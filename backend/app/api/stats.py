"""统计模块：站点概览、趋势、活跃与内容洞察（管理员）。

设计要点：
- 全部使用按日期分组的单条聚合查询，避免逐日 N+1。
- 日期桶在 Python 侧补零，保证趋势连续无空洞。
- 只读，不写库；不改变既有 /api/admin/stats 的返回结构。
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.schemas.common import Result
from app.core.levels import LEVEL_LADDER
from app.api.deps import get_admin_user

router = APIRouter(prefix="/api/admin", tags=["统计"])


def _day_buckets(days: int):
    """返回最近 days 天（含今天）的 [date(YYYY-MM-DD), ...]，按时间正序。"""
    today = datetime.now(timezone.utc).date()
    return [today - timedelta(days=i) for i in range(days - 1, -1, -1)]


async def _count_by_date(db, model, days):
    """对 model.created_at 按日分组计数，返回 {date_str: count}。"""
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    rows = await db.execute(
        select(func.date(model.created_at), func.count())
        .where(model.created_at >= since)
        .group_by(func.date(model.created_at))
    )
    return {r[0]: int(r[1] or 0) for r in rows.all()}


@router.get("/stats/insights", response_model=Result[dict])
async def insights(
    days: int = Query(30, ge=1, le=180, description="统计区间天数"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    buckets = _day_buckets(days)
    date_keys = [d.isoformat() for d in buckets]

    posts_by_day = await _count_by_date(db, Post, days)
    users_by_day = await _count_by_date(db, User, days)
    comments_by_day = await _count_by_date(db, Comment, days)

    series = [
        {
            "date": k,
            "posts": posts_by_day.get(k, 0),
            "users": users_by_day.get(k, 0),
            "comments": comments_by_day.get(k, 0),
        }
        for k in date_keys
    ]

    # ---- 等级分布（含未覆盖等级补零，名称/色值来自等级表）----
    lv_rows = await db.execute(
        select(User.level, func.count()).group_by(User.level)
    )
    lv_map = {int(r[0] or 1): int(r[1] or 0) for r in lv_rows.all()}
    level_distribution = [
        {
            "level": lv,
            "name": name,
            "color": color,
            "count": lv_map.get(lv, 0),
        }
        for lv, name, _need, color in LEVEL_LADDER
    ]

    # ---- 活跃用户：今日 / 近 7 日（按最近登录日期字符串）----
    today_str = datetime.now(timezone.utc).date().isoformat()
    week_start = (datetime.now(timezone.utc).date() - timedelta(days=6)).isoformat()
    active_today = (await db.execute(
        select(func.count()).select_from(User).where(User.last_login_date == today_str)
    )).scalar() or 0
    active_week = (await db.execute(
        select(func.count()).select_from(User).where(User.last_login_date >= week_start)
    )).scalar() or 0

    # ---- 头部创作者（近 30 天发布量 + 累计获赞）----
    top_rows = await db.execute(
        select(
            Post.user_id,
            func.count(Post.id).label("posts"),
            func.coalesce(func.sum(Post.like_count), 0).label("likes"),
        )
        .where(Post.status == "published")
        .group_by(Post.user_id)
        .order_by(func.count(Post.id).desc(), func.coalesce(func.sum(Post.like_count), 0).desc())
        .limit(10)
    )
    top_authors = []
    for r in top_rows.all():
        uid = r[0]
        u = (await db.execute(select(User).where(User.id == uid))).scalar() if uid else None
        top_authors.append({
            "id": uid,
            "nickname": u.nickname if u else "已注销",
            "level": int(u.level or 1) if u else 1,
            "posts": int(r[1] or 0),
            "likes": int(r[2] or 0),
        })

    # ---- 互动效率（已发布帖均值）----
    agg = await db.execute(
        select(
            func.count(Post.id),
            func.coalesce(func.avg(Post.view_count), 0),
            func.coalesce(func.avg(Post.like_count), 0),
            func.coalesce(func.avg(Post.comment_count), 0),
        ).where(Post.status == "published")
    )
    total_posts, avg_views, avg_likes, avg_comments = agg.one()
    total_posts = int(total_posts or 0)
    engagement = {
        "avg_views": round(float(avg_views or 0), 1),
        "avg_likes": round(float(avg_likes or 0), 2),
        "avg_comments": round(float(avg_comments or 0), 2),
        "posts": total_posts,
    }

    return Result(data={
        "range_days": days,
        "series": series,
        "level_distribution": level_distribution,
        "active": {
            "today_users": int(active_today),
            "week_users": int(active_week),
        },
        "top_authors": top_authors,
        "engagement": engagement,
    })
