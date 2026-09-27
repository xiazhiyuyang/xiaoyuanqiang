"""帖子管理：列表/置顶/审核/恢复/删除。"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.schemas.common import Result, PageResponse
from app.api.deps import require_permission
from app.core.activity import log_action, notify_user

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/posts", response_model=Result[PageResponse[dict]])
async def list_all_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("post_manage", "content_review")),
):
    query = select(Post).options(selectinload(Post.author), selectinload(Post.category))
    count_query = select(func.count()).select_from(Post)
    if status_filter:
        query = query.where(Post.status == status_filter)
        count_query = count_query.where(Post.status == status_filter)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(Post.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    posts = result.scalars().all()
    items = [{
        "id": p.id, "title": p.title, "content": p.content[:200],
        "author_name": p.author.nickname if p.author else None,
        "author_id": p.user_id,
        "category": p.category.name if p.category else None,
        "is_anonymous": p.is_anonymous, "is_top": p.is_top,
        "has_video": bool(p.video_url),
        "status": p.status, "view_count": p.view_count,
        "like_count": p.like_count, "comment_count": p.comment_count,
        "created_at": p.created_at,
    } for p in posts]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.post("/posts/{post_id}/top", response_model=Result)
async def toggle_top(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("post_manage", "content_review")),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.is_top = not post.is_top
    await db.commit()
    return Result(data={"is_top": post.is_top}, msg=("已置顶" if post.is_top else "已取消置顶"))


@router.post("/posts/{post_id}/review", response_model=Result)
async def review_post(
    post_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("post_manage", "content_review")),
):
    """审核帖子：action=approve 通过 / reject 驳回（删除）"""
    action = (body or {}).get("action")
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if action == "approve":
        post.status = "published"
        msg = "已通过审核"
    elif action == "reject":
        post.status = "deleted"
        msg = "已驳回并删除"
    else:
        raise HTTPException(status_code=400, detail="审核动作不合法")
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
        user_id=admin.id, username=admin.username, action="admin_post_review",
        target_type="post", target_id=post.id, detail=f"{msg}：{post.title[:30]}", request=request,
    )
    return Result(msg=msg)


@router.post("/posts/{post_id}/restore", response_model=Result)
async def restore_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("post_manage", "content_review")),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.status = "published"
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_post_restore",
        target_type="post", target_id=post.id, detail=f"恢复帖子：{post.title[:30]}", request=request,
    )
    return Result(msg="已恢复")


@router.delete("/posts/{post_id}", response_model=Result)
async def admin_delete_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("post_manage", "content_review")),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    title = post.title
    post.status = "deleted"
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_post_delete",
        target_type="post", target_id=post_id, detail=f"后台删除帖子：{title[:30]}", request=request,
    )
    return Result(msg="已删除")
