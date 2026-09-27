"""举报管理：列表/处理。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.report import Report
from app.schemas.common import Result, PageResponse
from app.schemas.report import ReportHandle, REPORT_REASONS
from app.api.deps import require_permission
from app.core.activity import log_action

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/reports", response_model=Result[PageResponse[dict]])
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("report_review")),
):
    query = select(Report)
    count_query = select(func.count()).select_from(Report)
    if status_filter:
        query = query.where(Report.status == status_filter)
        count_query = count_query.where(Report.status == status_filter)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(Report.status.asc(), Report.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    reports = result.scalars().all()
    user_ids = set()
    for r in reports:
        user_ids.add(r.reporter_id)
        if r.target_user_id:
            user_ids.add(r.target_user_id)
        if r.handler_id:
            user_ids.add(r.handler_id)
    name_map = {}
    if user_ids:
        users = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        name_map = {u.id: u.nickname for u in users}
    items = [{
        "id": r.id,
        "target_type": r.target_type,
        "target_id": r.target_id,
        "target_user_id": r.target_user_id,
        "target_user_name": name_map.get(r.target_user_id),
        "reporter_id": r.reporter_id,
        "reporter_name": name_map.get(r.reporter_id),
        "reason": r.reason,
        "reason_text": REPORT_REASONS.get(r.reason, r.reason),
        "detail": r.detail,
        "snapshot": r.target_snapshot,
        "status": r.status,
        "handler_id": r.handler_id,
        "handler_name": name_map.get(r.handler_id),
        "handle_remark": r.handle_remark,
        "handled_at": r.handled_at,
        "created_at": r.created_at,
    } for r in reports]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.post("/reports/{report_id}/handle", response_model=Result)
async def handle_report(
    report_id: int,
    data: ReportHandle,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("report_review")),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")
    if report.status != "pending":
        raise HTTPException(status_code=400, detail="该举报已处理")
    action_taken = []
    if data.status == "approved":
        if report.target_type == "post":
            post = (await db.execute(select(Post).where(Post.id == report.target_id))).scalar_one_or_none()
            if post and post.status != "deleted":
                post.status = "deleted"
                action_taken.append("已删除帖子")
        elif report.target_type == "comment":
            comment = (await db.execute(
                select(Comment).where(Comment.id == report.target_id)
            )).scalar_one_or_none()
            if comment:
                post = (await db.execute(select(Post).where(Post.id == comment.post_id))).scalar_one_or_none()
                if post:
                    post.comment_count = max(0, post.comment_count - 1)
                await db.delete(comment)
                action_taken.append("已删除评论")
        elif report.target_type == "user":
            data.ban_user = True
        if data.ban_user and report.target_user_id:
            target = (await db.execute(
                select(User).where(User.id == report.target_user_id, User.is_deleted == False)  # noqa: E712
            )).scalar_one_or_none()
            if target and target.role != "admin":
                target.is_banned = True
                action_taken.append("已封禁用户")
            elif target and target.role == "admin":
                action_taken.append("管理员账号不予封禁")
    report.status = data.status
    report.handler_id = admin.id
    report.handle_remark = data.remark
    report.handled_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_report_handle",
        target_type="report", target_id=report.id,
        detail=f"举报#{report.id}处理：{data.status}；{'、'.join(action_taken)}", request=request,
    )
    return Result(msg="；".join(action_taken) if action_taken else "处理完成",
                  data={"actions": action_taken})
