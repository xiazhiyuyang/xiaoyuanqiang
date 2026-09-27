from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.common import Result, PageResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["通知"])

# 私信类通知走「消息-私信会话」，互动列表保留赞/评论/关注/系统
_INTERACTION_TYPES = ("like", "comment", "follow", "system")


@router.get("", response_model=Result[PageResponse[dict]])
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.type.in_(_INTERACTION_TYPES),
    )
    count_query = select(func.count()).select_from(Notification).where(
        Notification.user_id == current_user.id,
        Notification.type.in_(_INTERACTION_TYPES),
    )
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        base.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    notifications = result.scalars().all()
    items = [{
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "content": n.content,
        "target_id": n.target_id,
        "sender_id": n.sender_id,
        "is_read": n.is_read,
        "created_at": n.created_at,
    } for n in notifications]
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.get("/unread-count", response_model=Result[dict])
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
            Notification.type.in_(_INTERACTION_TYPES),
        )
    )
    return Result(data={"count": result.scalar()})


@router.post("/{notification_id}/read", response_model=Result)
async def read_one(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """单条通知标记已读（仅能操作自己的通知）。"""
    n = await db.get(Notification, notification_id)
    if n and n.user_id == current_user.id and not n.is_read:
        n.is_read = True
        await db.commit()
    return Result(msg="ok")


@router.post("/read-all", response_model=Result)
async def read_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        update(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
            Notification.type.in_(_INTERACTION_TYPES),
        ).values(is_read=True)
    )
    await db.commit()
    return Result(msg="已全部标记为已读")
