"""评论管理：列表/删除。"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.schemas.common import Result, PageResponse
from app.api.deps import require_permission
from app.core.activity import log_action

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/comments", response_model=Result[PageResponse[dict]])
async def list_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("comment_manage", "content_review")),
):
    query = select(Comment).options(selectinload(Comment.author))
    count_query = select(func.count()).select_from(Comment)
    if keyword:
        query = query.where(Comment.content.contains(keyword))
        count_query = count_query.where(Comment.content.contains(keyword))
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(Comment.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    comments = result.scalars().all()
    items = [{
        "id": c.id, "post_id": c.post_id, "content": c.content[:200],
        "author_name": c.author.nickname if c.author else None,
        "author_id": c.user_id, "like_count": c.like_count,
        "created_at": c.created_at,
    } for c in comments]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.delete("/comments/{comment_id}", response_model=Result)
async def admin_delete_comment(
    comment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("comment_manage", "content_review")),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    post = (await db.execute(select(Post).where(Post.id == comment.post_id))).scalar_one_or_none()
    if post:
        post.comment_count = max(0, post.comment_count - 1)
    content = comment.content[:30]
    await db.delete(comment)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_comment_delete",
        target_type="comment", target_id=comment_id, detail=f"删除评论：{content}", request=request,
    )
    return Result(msg="已删除")
