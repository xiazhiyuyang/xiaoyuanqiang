from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.message import Message
from app.models.report import Report
from app.schemas.report import ReportCreate, REPORT_REASONS
from app.schemas.common import Result
from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit

router = APIRouter(prefix="/api/reports", tags=["举报"])


@router.post("", response_model=Result,
             dependencies=[Depends(rate_limit("report-create", 10, 60))])
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.reason not in REPORT_REASONS:
        raise HTTPException(status_code=400, detail="举报理由不合法")

    # 同一对象存在待处理举报时不重复提交
    dup = await db.execute(
        select(Report).where(
            Report.reporter_id == current_user.id,
            Report.target_type == data.target_type,
            Report.target_id == data.target_id,
            Report.status == "pending",
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已举报过该内容，正在处理中")

    snapshot = None
    target_user_id = None

    if data.target_type == "post":
        post = (await db.execute(select(Post).where(Post.id == data.target_id))).scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        snapshot = f"{post.title}\n{post.content}"[:1000]
        target_user_id = post.user_id
    elif data.target_type == "comment":
        comment = (await db.execute(select(Comment).where(Comment.id == data.target_id))).scalar_one_or_none()
        if not comment:
            raise HTTPException(status_code=404, detail="评论不存在")
        snapshot = comment.content[:1000]
        target_user_id = comment.user_id
    elif data.target_type == "user":
        user = (await db.execute(select(User).where(User.id == data.target_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        snapshot = f"昵称：{user.nickname}；简介：{user.bio or ''}"[:1000]
        target_user_id = user.id
    elif data.target_type == "message":
        message = (await db.execute(select(Message).where(Message.id == data.target_id))).scalar_one_or_none()
        if not message:
            raise HTTPException(status_code=404, detail="私信不存在")
        # 只有会话参与者能举报
        from app.models.message import Conversation
        conversation = (await db.execute(
            select(Conversation).where(Conversation.id == message.conversation_id)
        )).scalar_one_or_none()
        if not conversation or (
            conversation.user1_id != current_user.id and conversation.user2_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="无权举报该私信")
        snapshot = message.content[:1000]
        target_user_id = message.sender_id

    report = Report(
        reporter_id=current_user.id,
        target_type=data.target_type,
        target_id=data.target_id,
        target_user_id=target_user_id,
        reason=data.reason,
        detail=data.detail,
        target_snapshot=snapshot,
    )
    db.add(report)
    await db.commit()
    return Result(msg="举报已提交，我们会尽快处理")
