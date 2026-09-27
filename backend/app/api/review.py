"""内容/举报审查接口

面向被管理员授予单项权限的普通用户：
- content_review：可查看待审/已发布帖子并执行通过、删除
- report_review：可查看并处理举报队列
被授权用户不是管理员，无法访问 /api/admin/* 的任何其他能力。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.report import Report
from app.schemas.common import Result, PageResponse
from app.schemas.report import ReportHandle, REPORT_REASONS
from app.api.deps import require_permission
from app.core.activity import log_action, notify_user

router = APIRouter(prefix="/api/review", tags=["审查中心"])


@router.get("/overview", response_model=Result[dict])
async def review_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("content_review", "report_review")),
):
    pending_posts = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == "pending")
    )).scalar()
    pending_reports = (await db.execute(
        select(func.count()).select_from(Report).where(Report.status == "pending")
    )).scalar()
    return Result(data={
        "pending_posts": int(pending_posts or 0),
        "pending_reports": int(pending_reports or 0),
        "content_review": user.has_permission("content_review"),
        "report_review": user.has_permission("report_review"),
        "is_admin": user.role == "admin",
    })


# ---------- 内容审查 ----------
@router.get("/posts", response_model=Result[PageResponse[dict]])
async def review_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status_filter: str = Query("pending", alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("content_review")),
):
    if status_filter not in ("pending", "published", "deleted"):
        status_filter = "pending"
    query = select(Post).where(Post.status == status_filter)
    total = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == status_filter)
    )).scalar()
    result = await db.execute(
        query.options(
            selectinload(Post.author),
            selectinload(Post.category),
            selectinload(Post.images),  # 修复：异步下访问 p.images 需预加载，否则已发布/已删除列表 500
        )
        .order_by(Post.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    posts = result.scalars().all()
    items = []
    for p in posts:
        items.append({
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "images": [img.url for img in p.images] if p.images else [],
            "video_url": p.video_url,
            "status": p.status,
            "is_anonymous": p.is_anonymous,
            "author_name": "匿名用户" if p.is_anonymous else (p.author.nickname if p.author else "未知"),
            "category_name": p.category.name if p.category else None,
            "like_count": p.like_count,
            "comment_count": p.comment_count,
            "view_count": p.view_count,
            "created_at": p.created_at,
        })
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.post("/posts/{post_id}/action", response_model=Result)
async def review_post_action(
    post_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("content_review")),
):
    """审查动作：approve 通过 / remove 删除（软删除）。"""
    action = (body or {}).get("action")
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if action == "approve":
        post.status = "published"
        msg = "已通过"
    elif action == "remove":
        post.status = "deleted"
        msg = "已删除"
    else:
        raise HTTPException(status_code=400, detail="动作不合法")
    # 审核结果在「消息-互动消息」内告知作者
    reason = str((body or {}).get("reason") or "").strip()
    if post.user_id:
        if action == "approve":
            await notify_user(
                db, post.user_id, "帖子审核通过",
                f"你发布的《{post.title[:30]}》已通过审核，现已公开展示。",
                target_id=post.id,
            )
        else:
            tail = f"驳回原因：{reason[:100]}" if reason else "内容可能违反社区公约，如有疑问可联系管理员。"
            await notify_user(
                db, post.user_id, "帖子未通过审核",
                f"你发布的《{post.title[:30]}》未通过审核。{tail}",
                target_id=post.id,
            )
    await db.commit()
    await log_action(
        user_id=user.id, username=user.username, action="review_post",
        target_type="post", target_id=post.id,
        detail=f"审查员{msg}帖子：{post.title[:30]}", request=request,
    )
    return Result(msg=msg)


# ---------- 举报审查 ----------
@router.get("/reports", response_model=Result[PageResponse[dict]])
async def review_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("report_review")),
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
        "reporter_name": name_map.get(r.reporter_id),
        "reason": r.reason,
        "reason_text": REPORT_REASONS.get(r.reason, r.reason),
        "detail": r.detail,
        "snapshot": r.target_snapshot,
        "status": r.status,
        "handle_remark": r.handle_remark,
        "handled_at": r.handled_at,
        "created_at": r.created_at,
    } for r in reports]
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.post("/reports/{report_id}/handle", response_model=Result)
async def review_handle_report(
    report_id: int,
    data: ReportHandle,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("report_review")),
):
    report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")
    if report.status != "pending":
        raise HTTPException(status_code=400, detail="该举报已处理")
    actions_taken = []
    if data.status == "approved":
        if report.target_type == "post":
            post = (await db.execute(select(Post).where(Post.id == report.target_id))).scalar_one_or_none()
            if post and post.status != "deleted":
                post.status = "deleted"
                actions_taken.append("已删除帖子")
        elif report.target_type == "comment":
            comment = (await db.execute(
                select(Comment).where(Comment.id == report.target_id)
            )).scalar_one_or_none()
            if comment:
                post = (await db.execute(select(Post).where(Post.id == comment.post_id))).scalar_one_or_none()
                if post:
                    post.comment_count = max(0, post.comment_count - 1)
                await db.delete(comment)
                actions_taken.append("已删除评论")
        elif report.target_type == "user":
            data.ban_user = True
        if data.ban_user and report.target_user_id:
            target = (await db.execute(
                select(User).where(User.id == report.target_user_id)
            )).scalar_one_or_none()
            if target and target.role != "admin":
                target.is_banned = True
                actions_taken.append("已封禁用户")
    report.status = data.status
    report.handler_id = user.id
    report.handle_remark = data.remark
    report.handled_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(
        user_id=user.id, username=user.username, action="review_report",
        target_type="report", target_id=report.id,
        detail=f"审查员处理举报#{report.id}：{data.status}；{'、'.join(actions_taken)}",
        request=request,
    )
    return Result(msg="；".join(actions_taken) if actions_taken else "处理完成",
                  data={"actions": actions_taken})
