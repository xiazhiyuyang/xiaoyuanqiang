"""数据概览：核心计数、趋势、分布、最近动态。"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post, Category
from app.models.comment import Comment
from app.models.report import Report
from app.models.interaction import Favorite
from app.schemas.common import Result
from app.api.deps import require_permission

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/stats", response_model=Result[dict])
async def stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("stats_view")),
):
    today = datetime.now(timezone.utc).date()

    user_count = (await db.execute(
        select(func.count()).select_from(User).where(User.is_deleted == False)  # noqa: E712
    )).scalar()
    post_count = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == "published")
    )).scalar()
    pending_count = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == "pending")
    )).scalar()
    deleted_count = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == "deleted")
    )).scalar()
    comment_count = (await db.execute(select(func.count()).select_from(Comment))).scalar()
    report_pending = (await db.execute(
        select(func.count()).select_from(Report).where(Report.status == "pending")
    )).scalar()
    banned_count = (await db.execute(
        select(func.count()).select_from(User).where(
            User.is_banned == True, User.is_deleted == False  # noqa: E712
        )
    )).scalar()
    today_post_count = (await db.execute(
        select(func.count()).select_from(Post).where(func.date(Post.created_at) == today)
    )).scalar()
    today_user_count = (await db.execute(
        select(func.count()).select_from(User).where(
            func.date(User.created_at) == today, User.is_deleted == False  # noqa: E712
        )
    )).scalar()

    agg = await db.execute(select(
        func.coalesce(func.sum(Post.view_count), 0),
        func.coalesce(func.sum(Post.like_count), 0),
    ).where(Post.status == "published"))
    total_views, total_likes = agg.one()
    total_favorites = (await db.execute(select(func.count()).select_from(Favorite))).scalar()

    since7 = datetime.now(timezone.utc) - timedelta(days=6)
    trend_rows = await db.execute(
        select(func.date(Post.created_at), func.count())
        .where(Post.created_at >= since7)
        .group_by(func.date(Post.created_at))
    )
    trend_map = {r[0]: int(r[1] or 0) for r in trend_rows.all()}
    trend = []
    for i in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        trend.append({"date": day.strftime("%m-%d"), "count": trend_map.get(day.isoformat(), 0)})

    cat_rows = await db.execute(
        select(Category.id, Category.name, Category.slug, func.count(Post.id))
        .outerjoin(Post, (Post.category_id == Category.id) & (Post.status == "published"))
        .group_by(Category.id, Category.name, Category.slug)
        .order_by(desc(func.count(Post.id)), Category.sort_order)
    )
    category_distribution = [
        {"id": r[0], "name": r[1], "slug": r[2], "count": int(r[3] or 0)}
        for r in cat_rows.all()
    ]

    recent_post_rows = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .order_by(desc(Post.created_at))
        .limit(8)
    )
    recent_posts = []
    for p in recent_post_rows.scalars().all():
        recent_posts.append({
            "id": p.id,
            "title": p.title,
            "author": (p.author.nickname if p.author else "匿名"),
            "author_id": p.user_id,
            "is_anonymous": bool(p.is_anonymous),
            "status": p.status,
            "visibility": getattr(p, "visibility", None) or "public",
            "like_count": int(p.like_count or 0),
            "comment_count": int(p.comment_count or 0),
            "view_count": int(p.view_count or 0),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    recent_user_rows = await db.execute(
        select(User).where(User.is_deleted == False).order_by(desc(User.created_at)).limit(6)  # noqa: E712
    )
    recent_users = [
        {
            "id": u.id, "nickname": u.nickname, "username": u.username,
            "role": u.role, "is_banned": bool(u.is_banned),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in recent_user_rows.scalars().all()
    ]

    return Result(data={
        "user_count": int(user_count or 0),
        "post_count": int(post_count or 0),
        "pending_count": int(pending_count or 0),
        "comment_count": int(comment_count or 0),
        "report_pending_count": int(report_pending or 0),
        "banned_count": int(banned_count or 0),
        "today_post_count": int(today_post_count or 0),
        "today_user_count": int(today_user_count or 0),
        "total_views": int(total_views or 0),
        "total_likes": int(total_likes or 0),
        "total_favorites": int(total_favorites or 0),
        "status_distribution": {
            "published": int(post_count or 0),
            "pending": int(pending_count or 0),
            "deleted": int(deleted_count or 0),
        },
        "category_distribution": category_distribution,
        "trend": trend,
        "recent_posts": recent_posts,
        "recent_users": recent_users,
    })
