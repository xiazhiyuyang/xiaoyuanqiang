from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.interaction import LikeRecord
from app.models.notification import Notification
from app.schemas.comment import CommentCreate, CommentResponse, CommentAuthor
from app.schemas.common import Result, PageResponse
from app.api.deps import get_current_user, get_current_user_optional
from app.core.moderation import (
    moderate_text, moderate_content, is_review_active, record_review, get_review_config,
)
from app.core.security import anonymous_alias
from app.core.ratelimit import rate_limit
from app.core.activity import user_notify_on

router = APIRouter(prefix="/api/posts/{post_id}/comments", tags=["评论"])


def _comment_to_dict(comment: Comment, current_user_id: int | None = None) -> dict:
    author = None
    author_name = None
    # 评论的匿名跟随帖子
    if comment.post and comment.post.is_anonymous and comment.post.user_id == comment.user_id:
        author_name = anonymous_alias(comment.user_id, comment.post_id)
    else:
        author = CommentAuthor(
            id=comment.author.id, nickname=comment.author.nickname, avatar=comment.author.avatar,
        )

    is_liked = False
    if current_user_id:
        # likes 在 service 层预加载或单独查，这里简化
        pass

    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "content": comment.content,
        "author": author,
        "author_name": author_name,
        "parent_id": comment.parent_id,
        "reply_to_user_id": comment.reply_to_user_id,
        "like_count": comment.like_count,
        "is_liked": is_liked,
        "created_at": comment.created_at,
        "replies": [],
    }


async def _load_visible_post(db: AsyncSession, post_id: int, viewer: User | None) -> Post:
    """评论读写前统一校验目标帖：必须已发布，且私密帖仅作者/管理员可见。

    防止通过枚举自增 post_id 读取或评论他人的私密/待审核/已删除帖子（IDOR/信息泄露）。
    对无权访问者统一返回 404，不泄露帖子是否存在。
    """
    post = (
        await db.execute(select(Post).where(Post.id == post_id, Post.status == "published"))
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    is_manager = bool(viewer) and (post.user_id == viewer.id or viewer.role == "admin")
    if getattr(post, "visibility", "public") == "private" and not is_manager:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


@router.get("", response_model=Result[PageResponse[CommentResponse]])
async def list_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # 先校验目标帖可见，避免私密/待审/已删帖的评论被枚举读取
    await _load_visible_post(db, post_id, current_user)
    # 只查顶层评论，回复嵌套
    query = (
        select(Comment)
        .where(Comment.post_id == post_id, Comment.parent_id.is_(None))
        .options(
            selectinload(Comment.author),
            selectinload(Comment.post),
            selectinload(Comment.replies).selectinload(Comment.author),
            selectinload(Comment.replies).selectinload(Comment.post),
        )
        .order_by(Comment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    comments = result.scalars().all()

    # 获取当前用户点赞的评论ID
    liked_ids = set()
    if current_user and comments:
        all_ids = []
        for c in comments:
            all_ids.append(c.id)
            for r in c.replies:
                all_ids.append(r.id)
        like_result = await db.execute(
            select(LikeRecord.target_id).where(
                LikeRecord.user_id == current_user.id,
                LikeRecord.target_type == "comment",
                LikeRecord.target_id.in_(all_ids),
            )
        )
        liked_ids = {row[0] for row in like_result.all()}

    items = []
    for c in comments:
        d = _comment_to_dict(c, current_user.id if current_user else None)
        d["is_liked"] = c.id in liked_ids
        d["replies"] = []
        for r in c.replies:
            rd = _comment_to_dict(r, current_user.id if current_user else None)
            rd["is_liked"] = r.id in liked_ids
            d["replies"].append(rd)
        items.append(d)

    return Result(data=PageResponse(
        items=items, total=len(items), page=page, page_size=page_size, total_pages=1,
    ))


@router.post("", response_model=Result[CommentResponse],
             dependencies=[Depends(rate_limit("comment-create", 20, 60))])
async def create_comment(
    post_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 已发布且当前用户可见（私密帖仅作者/管理员）才允许评论
    post = await _load_visible_post(db, post_id, current_user)

    if data.parent_id:
        parent_result = await db.execute(select(Comment).where(Comment.id == data.parent_id))
        if not parent_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="父评论不存在")

    mod_ctx = None
    if await is_review_active(db, "comment", current_user):
        cfg = await get_review_config(db)
        dry_run = bool(cfg.get("dry_run"))
        res = await moderate_content(db, data.content, target_type="comment",
                                     user_id=current_user.id, dry_run=dry_run)
        if res.requested_action == "block" and not dry_run:
            await record_review(db, target_type="comment", target_id=None, user_id=current_user.id,
                                title="", content=data.content, result=res, dry_run=False)
            await db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"内容包含违规词，发布被拦截：{'、'.join(res.blocked_words)}",
            )
        content = data.content if dry_run else (res.masked_text if res.requested_action in ("mask", "review") else data.content)
        mod_ctx = {"res": res, "dry_run": dry_run}
    else:
        moderation = await moderate_text(db, data.content)
        if moderation.blocked:
            raise HTTPException(
                status_code=400,
                detail=f"内容包含违规词，发布被拦截：{'、'.join(moderation.blocked_words)}",
            )
        content = moderation.cleaned

    comment = Comment(
        post_id=post_id,
        user_id=current_user.id,
        content=content,
        parent_id=data.parent_id,
        reply_to_user_id=data.reply_to_user_id,
    )
    db.add(comment)
    await db.flush()
    if mod_ctx is not None:
        await record_review(db, target_type="comment", target_id=comment.id, user_id=current_user.id,
                            title="", content=data.content, result=mod_ctx["res"], dry_run=mod_ctx["dry_run"])
    post.comment_count += 1
    # 评论经验奖励
    from app.core.levels import EXP_RULES, add_exp
    await add_exp(db, current_user, EXP_RULES["comment"], "comment")

    # 通知（接收方关闭了评论通知则不产生）
    if post.user_id != current_user.id and await user_notify_on(db, post.user_id, "comment"):
        db.add(Notification(
            user_id=post.user_id, sender_id=current_user.id, type="comment",
            title="有人评论了你的帖子", content=content[:50], target_id=post_id,
        ))
    if data.reply_to_user_id and data.reply_to_user_id != current_user.id and data.reply_to_user_id != post.user_id and await user_notify_on(db, data.reply_to_user_id, "comment"):
        db.add(Notification(
            user_id=data.reply_to_user_id, sender_id=current_user.id, type="comment",
            title="有人回复了你的评论", content=content[:50], target_id=post_id,
        ))

    await db.commit()
    await db.refresh(comment)

    result = await db.execute(
        select(Comment).where(Comment.id == comment.id).options(
            selectinload(Comment.author), selectinload(Comment.post),
        )
    )
    comment = result.scalar_one()
    return Result(data=_comment_to_dict(comment, current_user.id))


@router.delete("/{comment_id}", response_model=Result)
async def delete_comment(
    post_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.post_id == post_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除")

    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if post is not None:
        post.comment_count = max(0, post.comment_count - 1)

    await db.delete(comment)
    await db.commit()
    return Result(msg="删除成功")


@router.post("/{comment_id}/like", response_model=Result)
async def toggle_comment_like(
    post_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.post_id == post_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    existing = await db.execute(
        select(LikeRecord).where(
            LikeRecord.user_id == current_user.id,
            LikeRecord.target_id == comment_id,
            LikeRecord.target_type == "comment",
        )
    )
    record = existing.scalar_one_or_none()
    if record:
        await db.delete(record)
        comment.like_count = max(0, comment.like_count - 1)
        liked = False
    else:
        db.add(LikeRecord(user_id=current_user.id, target_id=comment_id, target_type="comment"))
        comment.like_count += 1
        liked = True

    await db.commit()
    return Result(data={"liked": liked, "like_count": comment.like_count})
