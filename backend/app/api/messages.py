from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.message import Conversation, Message
from app.models.notification import Notification
from app.schemas.message import (
    ConversationCreate, MessageCreate, MessageResponse, ConversationResponse,
)
from app.schemas.common import Result, PageResponse
from app.api.deps import get_current_user
from app.core.moderation import (
    moderate_text, moderate_content, is_review_active, record_review, get_review_config,
)
from app.core.ratelimit import rate_limit
from app.core.activity import log_action, feature_on

router = APIRouter(prefix="/api/messages", tags=["私信"])


async def _get_owned_conversation(db, conversation_id: int, user: User) -> Conversation:
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if conv.user1_id != user.id and conv.user2_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    return conv


@router.get("/conversations", response_model=Result[list[ConversationResponse]])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(or_(Conversation.user1_id == current_user.id, Conversation.user2_id == current_user.id))
        .order_by(Conversation.last_message_at.desc())
    )
    convs = result.scalars().all()
    if not convs:
        return Result(data=[])

    peer_ids = [(c.user2_id if c.user1_id == current_user.id else c.user1_id) for c in convs]
    peers = {
        u.id: u
        for u in (await db.execute(select(User).where(User.id.in_(peer_ids)))).scalars().all()
    }
    # 各会话未读数
    unread_result = await db.execute(
        select(Message.conversation_id, func.count())
        .where(Message.conversation_id.in_([c.id for c in convs]),
               Message.sender_id != current_user.id,
               Message.is_read == False)  # noqa: E712
        .group_by(Message.conversation_id)
    )
    unread_map = {row[0]: row[1] for row in unread_result.all()}

    items = []
    for c in convs:
        peer_id = c.user2_id if c.user1_id == current_user.id else c.user1_id
        peer = peers.get(peer_id)
        items.append(ConversationResponse(
            id=c.id,
            peer_id=peer_id,
            peer_nickname=peer.nickname if peer else "用户已注销",
            peer_avatar=peer.avatar if peer else None,
            last_content=c.last_content,
            last_sender_id=c.last_sender_id,
            unread_count=unread_map.get(c.id, 0),
            last_message_at=c.last_message_at,
        ))
    return Result(data=items)


@router.post("/conversations", response_model=Result[ConversationResponse])
async def create_or_get_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not await feature_on("message_open", True):
        raise HTTPException(status_code=403, detail="站点已关闭私信功能")
    if data.target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能和自己私信")
    target = await db.execute(select(User).where(User.id == data.target_user_id))
    target = target.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.is_banned:
        raise HTTPException(status_code=400, detail="该用户已被封禁")

    u1, u2 = sorted([current_user.id, data.target_user_id])
    result = await db.execute(
        select(Conversation).where(Conversation.user1_id == u1, Conversation.user2_id == u2)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(user1_id=u1, user2_id=u2)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    return Result(data=ConversationResponse(
        id=conv.id,
        peer_id=target.id,
        peer_nickname=target.nickname,
        peer_avatar=target.avatar,
        last_content=conv.last_content,
        last_sender_id=conv.last_sender_id,
        unread_count=0,
        last_message_at=conv.last_message_at,
    ))


@router.get("/conversations/{conversation_id}/messages", response_model=Result[PageResponse[MessageResponse]])
async def list_messages(
    conversation_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_conversation(db, conversation_id, current_user)
    count = (await db.execute(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )).scalar()
    # 倒序取最新一页后正序展示
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    messages = list(reversed(result.scalars().all()))
    # 进入会话把对方发来的未读消息标记已读
    await db.execute(
        update(Message)
        .where(Message.conversation_id == conversation_id,
               Message.sender_id != current_user.id,
               Message.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return Result(data=PageResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=count, page=page, page_size=page_size,
        total_pages=(count + page_size - 1) // page_size if count else 0,
    ))


@router.post("/conversations/{conversation_id}/messages", response_model=Result[MessageResponse],
             dependencies=[Depends(rate_limit("message-send", 30, 60))])
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = await _get_owned_conversation(db, conversation_id, current_user)
    raw_content = data.content.strip()
    mod_ctx = None
    if await is_review_active(db, "message", current_user):
        cfg = await get_review_config(db)
        dry_run = bool(cfg.get("dry_run"))
        res = await moderate_content(db, raw_content, target_type="message",
                                     user_id=current_user.id, dry_run=dry_run)
        if res.requested_action == "block" and not dry_run:
            await record_review(db, target_type="message", target_id=None, user_id=current_user.id,
                                title="", content=raw_content, result=res, dry_run=False)
            await db.commit()
            raise HTTPException(status_code=400, detail=f"内容包含违规词，发送被拦截：{'、'.join(res.blocked_words)}")
        content = raw_content if dry_run else (res.masked_text if res.requested_action in ("mask", "review") else raw_content)
        mod_ctx = {"res": res, "dry_run": dry_run}
    else:
        result = await moderate_text(db, raw_content)
        if result.blocked:
            raise HTTPException(status_code=400, detail=f"内容包含违规词，发送被拦截：{'、'.join(result.blocked_words)}")
        content = result.cleaned

    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content,
    )
    db.add(message)
    await db.flush()
    if mod_ctx is not None:
        await record_review(db, target_type="message", target_id=message.id, user_id=current_user.id,
                            title="", content=raw_content, result=mod_ctx["res"], dry_run=mod_ctx["dry_run"])
    conv.last_content = content[:200]
    conv.last_sender_id = current_user.id
    from datetime import datetime, timezone
    conv.last_message_at = datetime.now(timezone.utc)

    peer_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
    db.add(Notification(
        user_id=peer_id, sender_id=current_user.id, type="message",
        title="你收到一条新私信", content=content[:50], target_id=conversation_id,
    ))
    await db.commit()
    await db.refresh(message)
    await log_action(
        user_id=current_user.id, username=current_user.username, action="message_send",
        target_type="conversation", target_id=conversation_id,
        detail=f"私信用户#{peer_id}：{content[:30]}", request=request,
    )
    return Result(data=MessageResponse.model_validate(message))


@router.post("/conversations/{conversation_id}/read", response_model=Result)
async def mark_read(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_conversation(db, conversation_id, current_user)
    await db.execute(
        update(Message)
        .where(Message.conversation_id == conversation_id,
               Message.sender_id != current_user.id,
               Message.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return Result(msg="已读")


@router.get("/unread-count", response_model=Result[dict])
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 我参与的会话中，对方发给我的未读消息数
    conv_result = await db.execute(
        select(Conversation.id).where(
            or_(Conversation.user1_id == current_user.id, Conversation.user2_id == current_user.id)
        )
    )
    conv_ids = [row[0] for row in conv_result.all()]
    count = 0
    if conv_ids:
        count = (await db.execute(
            select(func.count()).select_from(Message).where(
                Message.conversation_id.in_(conv_ids),
                Message.sender_id != current_user.id,
                Message.is_read == False,  # noqa: E712
            )
        )).scalar()
    return Result(data={"count": count})
