"""热度分（时间衰减）计算与批量重算。

原实现的 `sort=hot` 是 `ORDER BY like_count DESC, created_at DESC`，
没有时间衰减——一条老帖只要赞够多就会永远压在首页顶部，新内容没有出头机会。

这里改成经典的「重力衰减」打分：

    base = like_count * 2 + comment_count * 3 + view_count * 0.1
    score = base / (age_hours + 2) ** GRAVITY

- `+2` 避免刚发布时 age≈0 导致除零/分数爆炸；
- `GRAVITY = 1.5` 是 Hacker News 常用值，越大衰减越快、首页更新越频繁；
- 评论权重高于点赞（互动成本更高），浏览权重最低（易被刷）。

分数落到 `posts.hot_score` 字段并建索引，列表查询直接 `ORDER BY hot_score DESC` 走索引，
不在查询时做函数计算（那样会导致全表扫 + 无法用索引）。

刷新时机：
1. 内容发生互动（点赞/评论/浏览/发帖）时，单条即时重算；
2. 后台周期任务每 10 分钟批量重算，保证即使没有新互动，排名也会随时间自然下沉。
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import bindparam, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post

logger = logging.getLogger("campus-wall")

GRAVITY = 1.5
W_LIKE = 2.0
W_COMMENT = 3.0
W_VIEW = 0.1
# 批量重算只看最近这么多天内的帖子：更早的帖子分数已趋近 0，重算无意义
RECOMPUTE_WINDOW_DAYS = 60
# 每批写入条数，避免单条 SQL 过大 / 长事务锁表
CHUNK_SIZE = 200


def compute_score(
    like_count: int = 0,
    comment_count: int = 0,
    view_count: int = 0,
    created_at: datetime | None = None,
    now: datetime | None = None,
) -> float:
    """纯函数：给定互动量与发布时间算出热度分。便于单测与复用。"""
    base = (like_count or 0) * W_LIKE + (comment_count or 0) * W_COMMENT + (view_count or 0) * W_VIEW
    if base <= 0:
        return 0.0
    ref = now or datetime.now(timezone.utc)
    created = created_at or ref
    # SQLite 取回的 datetime 可能是 naive（UTC），统一补齐时区再比较
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    age_hours = max((ref - created).total_seconds() / 3600.0, 0.0)
    score = base / math.pow(age_hours + 2.0, GRAVITY)
    # 保留 6 位小数：足够区分排序，又不会因浮点噪声频繁产生无意义写入
    return round(score, 6)


async def recompute_one(db: AsyncSession, post: Post, *, commit: bool = False) -> float:
    """单条重算。调用方通常已持有该 Post 对象，直接改属性即可随事务一起提交。"""
    score = compute_score(post.like_count, post.comment_count, post.view_count, post.created_at)
    post.hot_score = score
    if commit:
        await db.commit()
    return score


async def recompute_recent(db: AsyncSession, *, days: int = RECOMPUTE_WINDOW_DAYS) -> int:
    """批量重算最近 N 天的帖子热度分，返回受影响条数。

    用 executemany（一次 UPDATE 多组参数）而不是逐条 update，
    在 SQLite 上能把 N 次事务合并为若干批，显著降低写锁持有时间。
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(Post.id, Post.like_count, Post.comment_count, Post.view_count, Post.created_at)
        .where(Post.created_at >= cutoff)
    )).all()
    if not rows:
        return 0

    now = datetime.now(timezone.utc)
    payload = [
        {
            "p_id": r[0],
            "p_score": compute_score(r[1], r[2], r[3], r[4], now=now),
        }
        for r in rows
    ]
    # 用 Core 层的 Table.update() 而不是 ORM 的 update(Post)：
    # ORM 的「按主键批量更新」要求每个参数字典都以列名提供主键，
    # 用 bindparam 别名会报 "No primary key value supplied for column(s) posts.id"；
    # 这里本来就是纯后台打分、不需要会话同步，走 Core 更直接也更省开销。
    table = Post.__table__
    stmt = (
        table.update()
        .where(table.c.id == bindparam("p_id"))
        .values(hot_score=bindparam("p_score"))
    )
    affected = 0
    for i in range(0, len(payload), CHUNK_SIZE):
        chunk = payload[i:i + CHUNK_SIZE]
        await db.execute(stmt, chunk)
        affected += len(chunk)
    await db.commit()
    return affected


async def reset_stale(db: AsyncSession) -> int:
    """把窗口之外的老帖热度分归零，避免历史高分帖长期占据索引前部。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECOMPUTE_WINDOW_DAYS)
    result = await db.execute(
        update(Post)
        .where(Post.created_at < cutoff, Post.hot_score != 0)
        .values(hot_score=0.0)
        .execution_options(synchronize_session=None)
    )
    await db.commit()
    return int(result.rowcount or 0)
