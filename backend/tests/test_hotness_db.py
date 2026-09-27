"""热度分数据库集成测试。

单元测试只能验证 compute_score 的算术，验证不了「批量写回数据库」这条路径——
而正是这条路径踩过 SQLAlchemy 2.0 的坑：ORM 批量 UPDATE 带 WHERE 条件时
必须显式 `synchronize_session=None`，否则抛 InvalidRequestError，
表现为「服务能启动、但热度分永远是 0、热门流退化成时间序」。

所以这里用真实的 in-memory SQLite 跑一遍完整链路。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.hotness import RECOMPUTE_WINDOW_DAYS, compute_score, recompute_one, recompute_recent, reset_stale
from app.database import Base
from app.models.post import Category, Post
from app.models.user import User


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


async def _make_user(db, username: str = "u1") -> User:
    u = User(username=username, nickname=username, password_hash="x")
    db.add(u)
    await db.flush()
    return u


async def _make_post(db, user, *, title="t", like=0, comment=0, view=0, age_hours=1.0,
                     status="published") -> Post:
    p = Post(
        user_id=user.id, title=title, content="c", status=status,
        like_count=like, comment_count=comment, view_count=view,
        created_at=datetime.now(timezone.utc) - timedelta(hours=age_hours),
    )
    db.add(p)
    await db.flush()
    return p


@pytest.mark.asyncio
async def test_hot_score_column_exists_with_default(db):
    """新表必须自带 hot_score 且有默认值，否则 INSERT 会失败。"""
    u = await _make_user(db)
    p = await _make_post(db, u)
    await db.commit()
    assert p.hot_score == 0.0


@pytest.mark.asyncio
async def test_recompute_recent_persists_scores(db):
    """核心回归：批量写回必须真的落库（曾因 synchronize_session 缺失而静默失败）。"""
    u = await _make_user(db)
    p1 = await _make_post(db, u, title="新帖", like=10, comment=5, view=100, age_hours=1)
    p2 = await _make_post(db, u, title="老帖", like=10, comment=5, view=100, age_hours=240)
    await db.commit()

    affected = await recompute_recent(db)
    assert affected == 2

    rows = {r[0]: r[1] for r in (await db.execute(select(Post.id, Post.hot_score))).all()}
    assert rows[p1.id] > 0.0
    assert rows[p2.id] > 0.0
    assert rows[p1.id] > rows[p2.id]          # 同互动量，新帖分数更高
    assert rows[p1.id] == pytest.approx(
        compute_score(10, 5, 100, p1.created_at), rel=1e-3
    )


@pytest.mark.asyncio
async def test_recompute_recent_skips_old_posts(db):
    """窗口外的老帖不参与重算，避免每次全表扫描。"""
    u = await _make_user(db)
    old = await _make_post(db, u, title="远古帖", like=999,
                           age_hours=(RECOMPUTE_WINDOW_DAYS + 5) * 24)
    fresh = await _make_post(db, u, title="新帖", like=1, age_hours=1)
    await db.commit()

    affected = await recompute_recent(db)
    assert affected == 1
    scores = {r[0]: r[1] for r in (await db.execute(select(Post.id, Post.hot_score))).all()}
    assert scores[old.id] == 0.0
    assert scores[fresh.id] > 0.0


@pytest.mark.asyncio
async def test_recompute_recent_on_empty_table(db):
    """空表不能报错，返回 0。"""
    assert await recompute_recent(db) == 0


@pytest.mark.asyncio
async def test_reset_stale_zeroes_old_posts(db):
    u = await _make_user(db)
    old = await _make_post(db, u, title="远古帖", age_hours=(RECOMPUTE_WINDOW_DAYS + 5) * 24)
    old.hot_score = 123.456
    fresh = await _make_post(db, u, title="新帖", like=3, age_hours=1)
    fresh.hot_score = 9.99
    await db.commit()

    await reset_stale(db)
    scores = {r[0]: r[1] for r in (await db.execute(select(Post.id, Post.hot_score))).all()}
    assert scores[old.id] == 0.0
    assert scores[fresh.id] == 9.99          # 窗口内的不动


@pytest.mark.asyncio
async def test_recompute_one_updates_in_place(db):
    u = await _make_user(db)
    p = await _make_post(db, u, like=4, comment=2, view=10, age_hours=2)
    await db.commit()
    score = await recompute_one(db, p, commit=True)
    assert score > 0
    assert p.hot_score == score


@pytest.mark.asyncio
async def test_chunking_handles_more_than_chunk_size(db):
    """超过单批条数时必须分批写完，不能漏。"""
    from app.core import hotness
    original = hotness.CHUNK_SIZE
    hotness.CHUNK_SIZE = 3
    try:
        u = await _make_user(db)
        for i in range(10):
            await _make_post(db, u, title=f"p{i}", like=i + 1, age_hours=1)
        await db.commit()
        assert await recompute_recent(db) == 10
        rows = (await db.execute(select(Post.hot_score))).scalars().all()
        assert len(rows) == 10
        assert all(s > 0 for s in rows)
    finally:
        hotness.CHUNK_SIZE = original


@pytest.mark.asyncio
async def test_deleted_posts_are_still_scored(db):
    """软删帖（status='deleted'）也会被重算——分数本身无害，
    且列表查询已按 status 过滤，这里锁定行为避免将来误改。"""
    u = await _make_user(db)
    p = await _make_post(db, u, like=5, age_hours=1, status="deleted")
    await db.commit()
    await recompute_recent(db)
    score = (await db.execute(select(Post.hot_score).where(Post.id == p.id))).scalar()
    assert score > 0


@pytest.mark.asyncio
async def test_category_relation_still_works(db):
    """回归保护：新增字段不应影响既有关联查询。"""
    u = await _make_user(db)
    cat = Category(name="表白墙", slug="confession", icon="❤️", sort_order=1)
    db.add(cat)
    await db.flush()
    p = await _make_post(db, u, like=1)
    p.category_id = cat.id
    await db.commit()
    loaded = (await db.execute(select(Post).where(Post.id == p.id))).scalar_one()
    assert loaded.category.slug == "confession"
