"""admin 包公共工具：一次性确认 token、彻底清理用户数据。"""
import secrets as _secrets
import time as _time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.report import Report
from app.models.user import User

# ---------- 敏感操作二次确认 token（内存态、一次性、5 分钟有效）----------
_confirm_tokens: dict[str, dict] = {}
_CONFIRM_TTL = 300


def issue_confirm_token(admin_id: int, action: str, target_id: int) -> str:
    token = _secrets.token_urlsafe(24)
    _confirm_tokens[token] = {
        "admin_id": admin_id, "action": action, "target_id": target_id,
        "expires": _time.monotonic() + _CONFIRM_TTL,
    }
    return token


def consume_confirm_token(
    token: str | None, admin_id: int, action: str, target_id: int
) -> None:
    """校验并消费一次性确认 token；失败抛 403。"""
    if not token:
        raise HTTPException(status_code=403, detail="缺少确认令牌，请先调用 /api/admin/confirm-token 获取")
    item = _confirm_tokens.pop(token, None)
    if not item:
        raise HTTPException(status_code=403, detail="确认令牌无效或已被使用")
    if _time.monotonic() > item["expires"]:
        raise HTTPException(status_code=403, detail="确认令牌已过期，请重新获取")
    if item["admin_id"] != admin_id or item["action"] != action or item["target_id"] != target_id:
        raise HTTPException(status_code=403, detail="确认令牌与本次操作不匹配")


async def purge_user(db: AsyncSession, user: User):
    """彻底删除用户及其关联数据（FK 不级联的表手工清理）。

    保留供未来「彻底删除」使用；当前软删除接口不调用本函数。
    """
    from app.models.notification import Notification
    from app.models.interaction import LikeRecord, Favorite
    from app.models.message import Conversation, Message
    await db.execute(Notification.__table__.delete().where(Notification.user_id == user.id))
    await db.execute(
        Notification.__table__.update().where(Notification.sender_id == user.id).values(sender_id=None)
    )
    await db.execute(LikeRecord.__table__.delete().where(LikeRecord.user_id == user.id))
    await db.execute(Favorite.__table__.delete().where(Favorite.user_id == user.id))
    convs = (await db.execute(
        select(Conversation.id).where(
            (Conversation.user1_id == user.id) | (Conversation.user2_id == user.id)
        )
    )).scalars().all()
    if convs:
        await db.execute(Message.__table__.delete().where(Message.conversation_id.in_(convs)))
        await db.execute(Conversation.__table__.delete().where(Conversation.id.in_(convs)))
    await db.execute(
        Comment.__table__.update().where(Comment.reply_to_user_id == user.id)
        .values(reply_to_user_id=None)
    )
    await db.execute(Report.__table__.delete().where(Report.reporter_id == user.id))
    await db.execute(
        Report.__table__.update().where(
            (Report.target_user_id == user.id) | (Report.handler_id == user.id)
        ).values(target_user_id=None, handler_id=None)
    )
    try:
        from app.models.operation_log import OperationLog
        await db.execute(OperationLog.__table__.delete().where(OperationLog.user_id == user.id))
    except Exception:
        pass
    # 封存用户 UID（永久不再自动分配）
    try:
        from app.core.uid_allocator import reserve_uid
        await reserve_uid(db, user.id)
    except Exception:
        pass
    await db.delete(user)
