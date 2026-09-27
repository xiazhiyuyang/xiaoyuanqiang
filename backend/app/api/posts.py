import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post, PostImage, Category
from app.models.interaction import LikeRecord, Favorite, Follow
from app.models.user import staff_tags_of
from app.models.notification import Notification
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostDetail, PostImageResponse,
    CategoryResponse, PostAuthor,
)
from app.schemas.common import Result, PageResponse
from fastapi import Request

from app.api.deps import get_current_user, get_current_user_optional
from app.core.moderation import (
    moderate_text, moderate_content, is_review_active, record_review,
    get_review_config, worst_action,
)
from app.core.security import anonymous_alias
from app.core.ratelimit import rate_limit
from app.core.activity import log_action, get_review_policy, feature_on, user_notify_on
from app.core.levels import level_info, EXP_RULES, add_exp

router = APIRouter(prefix="/api/posts", tags=["帖子"])


def _assert_interact_allowed(post: Post, user: User) -> None:
    """点赞/收藏等互动前校验：私密帖仅作者/管理员可互动，对其他人按 404 处理（不泄露存在性）。"""
    is_manager = post.user_id == user.id or user.role == "admin"
    if getattr(post, "visibility", "public") == "private" and not is_manager:
        raise HTTPException(status_code=404, detail="帖子不存在")


async def _check_text(db: AsyncSession, title: str, content: str, user: User | None = None):
    """内容审核：AI 流水线启用时走多阶段审核，否则回退旧的敏感词过滤。

    返回 (处理后标题, 处理后内容, mod_ctx)。mod_ctx 用于发布成功后落库审核记录；
    AI 审核未启用时为 None。block 级内容直接拦截（落库记录后抛 400）。
    """
    user_id = user.id if user else None
    if not await is_review_active(db, "post", user):
        t = await moderate_text(db, title)
        c = await moderate_text(db, content)
        blocked = t.blocked_words + c.blocked_words
        if blocked:
            raise HTTPException(status_code=400, detail=f"内容包含违规词，发布被拦截：{'、'.join(blocked)}")
        return t.cleaned, c.cleaned, None

    cfg = await get_review_config(db)
    dry_run = bool(cfg.get("dry_run"))
    tr = await moderate_content(db, title, target_type="post", user_id=user_id, dry_run=dry_run)
    cr = await moderate_content(db, content, target_type="post", user_id=user_id, dry_run=dry_run)
    worst = worst_action(tr.requested_action, cr.requested_action)

    if worst == "block" and not dry_run:
        await record_review(db, target_type="post", target_id=None, user_id=user_id,
                            title=title, content=content, result=cr, dry_run=False)
        await db.commit()
        bw = tr.blocked_words + cr.blocked_words
        raise HTTPException(status_code=400, detail=f"内容包含违规词，发布被拦截：{'、'.join(bw)}")

    if dry_run:
        final_title, final_content = title, content
    else:
        final_title = tr.masked_text if worst in ("mask", "review") else title
        final_content = cr.masked_text if worst in ("mask", "review") else content
    ctx = {"tr": tr, "cr": cr, "dry_run": dry_run, "user_id": user_id,
           "title": title, "content": content}
    return final_title, final_content, ctx


def _post_to_response(post: Post, user_id: int | None = None, followed_ids: set[int] | None = None) -> dict:
    """将 Post 对象转为响应字典，处理匿名逻辑。
    followed_ids: 当前浏览者已关注的用户 id 集合，用于卡片上的「已关注/关注」状态。"""
    author = None
    author_name = None
    level_badge = None
    author_obj = post.author
    if author_obj is not None:
        _info = level_info(author_obj.level or 1)
        level_badge = {"level": _info["level"], "name": _info["name"], "color": _info["color"]}
    author_user_id = None
    if post.is_anonymous:
        author_name = anonymous_alias(post.user_id, post.id)
    else:
        author_user_id = post.user_id
        author = PostAuthor(
            id=post.author.id,
            nickname=post.author.nickname,
            avatar=post.author.avatar,
            level=author_obj.level or 1,
            level_name=level_badge["name"],
            level_color=level_badge["color"],
            role=author_obj.role or "user",
            staff_tags=staff_tags_of(author_obj),
            is_following=(post.author.id in (followed_ids or set())),
        )

    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "is_anonymous": post.is_anonymous,
        "visibility": getattr(post, "visibility", None) or "public",
        "user_id": author_user_id,
        "author": author,
        "author_name": author_name,
        "level_badge": level_badge,
        "category": CategoryResponse.model_validate(post.category) if post.category else None,
        "images": [PostImageResponse.model_validate(img) for img in post.images],
        "video_url": post.video_url,
        "view_count": post.view_count,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "is_top": post.is_top,
        "created_at": post.created_at,
    }


@router.get("", response_model=Result[PageResponse[PostResponse]])
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    category_id: int | None = None,
    keyword: str | None = None,
    sort: str = Query("new", pattern="^(new|hot)$"),
    feed: str = Query("all", pattern="^(all|following)$", description="all=全部 following=只看关注"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # 可见范围：公开帖所有人可见；登录用户还能看到自己的“仅自己”帖；管理员可见全部
    list_conds = [Post.status == "published"]
    if not (current_user and current_user.role == "admin"):
        if current_user:
            list_conds.append(or_(Post.visibility == "public", Post.visibility.is_(None), Post.user_id == current_user.id))
        else:
            list_conds.append(or_(Post.visibility == "public", Post.visibility.is_(None)))
    query = select(Post).where(*list_conds)
    count_query = select(func.count()).select_from(Post).where(*list_conds)
    # 关注流：仅展示当前用户关注对象发布的公开帖子；同时批量取出关注集合供卡片回显
    followed_ids: set[int] = set()
    if current_user:
        _follow_rows = await db.execute(
            select(Follow.following_id).where(Follow.follower_id == current_user.id)
        )
        followed_ids = {r for r in _follow_rows.scalars().all()}
    if feed == "following":
        if not current_user or not followed_ids:
            return Result(data=PageResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0))
        query = query.where(Post.user_id.in_(followed_ids))
        count_query = count_query.where(Post.user_id.in_(followed_ids))

    if category_id:
        query = query.where(Post.category_id == category_id)
        count_query = count_query.where(Post.category_id == category_id)
    if keyword:
        query = query.where(or_(Post.title.contains(keyword), Post.content.contains(keyword)))
        count_query = count_query.where(or_(Post.title.contains(keyword), Post.content.contains(keyword)))

    # 排序：置顶优先，然后按新/热
    if sort == "hot":
        query = query.order_by(desc(Post.is_top), desc(Post.like_count), desc(Post.created_at))
    else:
        query = query.order_by(desc(Post.is_top), desc(Post.created_at))

    query = query.options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.images))
    query = query.offset((page - 1) * page_size).limit(page_size)

    total_result = await db.execute(count_query)
    total = total_result.scalar()
    result = await db.execute(query)
    posts = result.scalars().all()

    items = [_post_to_response(p, followed_ids=followed_ids) for p in posts]
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    ))


@router.get("/categories/list", response_model=Result[list[CategoryResponse]])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return Result(data=[CategoryResponse.model_validate(c) for c in result.scalars().all()])


@router.get("/{post_id}", response_model=Result[PostDetail])
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id, Post.status == "published")
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.images))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    is_manager_detail = bool(current_user) and (post.user_id == current_user.id or current_user.role == "admin")
    if (getattr(post, "visibility", "public") == "private") and not is_manager_detail:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 浏览量原子 +1（避免并发读改写丢失计数）
    await db.execute(
        update(Post).where(Post.id == post_id).values(view_count=Post.view_count + 1)
    )
    post.view_count += 1
    await db.commit()

    data = _post_to_response(post)
    data["is_liked"] = False
    data["is_favorited"] = False
    # 作者/管理员可见编辑、删除入口
    is_owner = bool(current_user) and post.user_id == current_user.id
    is_manager = bool(current_user) and (is_owner or current_user.role == "admin")
    data["is_owner"] = is_owner
    data["can_edit"] = is_manager
    if current_user:
        liked = await db.execute(
            select(LikeRecord).where(
                LikeRecord.user_id == current_user.id,
                LikeRecord.target_id == post_id,
                LikeRecord.target_type == "post",
            )
        )
        favorited = await db.execute(
            select(Favorite).where(Favorite.user_id == current_user.id, Favorite.post_id == post_id)
        )
        data["is_liked"] = liked.scalar_one_or_none() is not None
        data["is_favorited"] = favorited.scalar_one_or_none() is not None

    return Result(data=data)


@router.post("", response_model=Result[PostResponse],
             dependencies=[Depends(rate_limit("post-create", 10, 60))])
async def create_post(
    data: PostCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not data.title.strip() or not data.content.strip():
        raise HTTPException(status_code=400, detail="标题和内容都不能为空")
    # 校验分类：传了 category_id 就必须是真实存在的分类，避免产生无分类脏数据
    if data.category_id is not None:
        cat = await db.get(Category, data.category_id)
        if not cat:
            raise HTTPException(status_code=400, detail="所选分类不存在，请重新选择")
    title, content, mod_ctx = await _check_text(db, data.title, data.content, user=current_user)
    # 功能开关：视频 / 匿名
    if data.video_url and not await feature_on("allow_video", True):
        raise HTTPException(status_code=403, detail="站点已关闭视频发布功能")
    is_anonymous = data.is_anonymous
    if is_anonymous and not await feature_on("allow_anonymous", True):
        is_anonymous = False
    # 审核策略：off 免审 / random 按比例随机抽查 / all 全部先审
    policy = await get_review_policy()
    sampled = False
    if policy["mode"] == "all":
        need_review = True
    elif policy["mode"] == "random" and policy["rate"] > 0:
        sampled = random.randint(1, 100) <= policy["rate"]
        need_review = sampled
    else:
        need_review = False
    post = Post(
        user_id=current_user.id,
        title=title,
        content=content,
        category_id=data.category_id,
        is_anonymous=is_anonymous,
        visibility=(data.visibility or "public"),
        video_url=data.video_url,
        status="pending" if need_review else "published",
    )
    db.add(post)
    await db.flush()

    # AI 审核记录落库（post 创建后才能拿到 target_id）
    if mod_ctx is not None:
        await record_review(
            db, target_type="post", target_id=post.id, user_id=mod_ctx["user_id"],
            title=mod_ctx["title"], content=mod_ctx["content"],
            result=mod_ctx["cr"], dry_run=mod_ctx["dry_run"],
        )

    for idx, url in enumerate(data.images):
        db.add(PostImage(post_id=post.id, url=url, sort_order=idx))

    # 发帖经验奖励
    from app.core.levels import EXP_RULES, add_exp
    await add_exp(db, current_user, EXP_RULES["post"], "post")
    if need_review:
        # 被抽中/强制审核：在「消息-互动消息」内告知作者
        db.add(Notification(
            user_id=current_user.id, type="system",
            title="你的帖子被随机抽中审核" if sampled else "帖子已进入审核",
            content=f"《{title[:30]}》正在等待人工审核，通过后将公开展示，审核结果会在这里通知你。",
            target_id=post.id,
        ))
    await db.commit()
    await db.refresh(post)
    await log_action(
        user_id=current_user.id, username=current_user.username, action="post_create",
        target_type="post", target_id=post.id,
        detail=("发帖（待审核）：" if need_review else "发帖：") + title[:30],
        request=request,
    )

    result = await db.execute(
        select(Post).where(Post.id == post.id)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.images))
    )
    post = result.scalar_one()
    if need_review:
        msg = "已被随机抽中，审核通过后将公开展示" if sampled else "发布成功，正在等待审核"
    else:
        msg = "发布成功"
    return Result(data=_post_to_response(post), msg=msg)


@router.put("/{post_id}", response_model=Result[PostResponse])
async def update_post(
    post_id: int,
    data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权修改")

    update_data = data.model_dump(exclude_unset=True)
    if "title" in update_data or "content" in update_data:
        new_title = update_data.get("title", post.title)
        new_content = update_data.get("content", post.content)
        update_data["title"], update_data["content"], _ = await _check_text(db, new_title, new_content, user=current_user)
    for field, value in update_data.items():
        setattr(post, field, value)
    post.updated_at = datetime.now(timezone.utc)
    await db.commit()

    result = await db.execute(
        select(Post).where(Post.id == post_id)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.images))
    )
    return Result(data=_post_to_response(result.scalar_one()))


@router.delete("/{post_id}", response_model=Result)
async def delete_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除")
    title = post.title
    post.status = "deleted"
    await db.commit()
    await log_action(
        user_id=current_user.id, username=current_user.username, action="post_delete",
        target_type="post", target_id=post_id, detail=f"删除帖子：{title[:30]}", request=request,
    )
    return Result(msg="删除成功")


@router.post("/{post_id}/like", response_model=Result)
async def toggle_like(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Post).where(Post.id == post_id, Post.status == "published"))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    _assert_interact_allowed(post, current_user)

    existing = await db.execute(
        select(LikeRecord).where(
            LikeRecord.user_id == current_user.id,
            LikeRecord.target_id == post_id,
            LikeRecord.target_type == "post",
        )
    )
    record = existing.scalar_one_or_none()
    if record:
        await db.delete(record)
        post.like_count = max(0, post.like_count - 1)
        liked = False
    else:
        db.add(LikeRecord(user_id=current_user.id, target_id=post_id, target_type="post"))
        post.like_count += 1
        liked = True
        # 通知作者（非自己、非匿名、接收方未关闭点赞通知）
        if post.user_id != current_user.id and await user_notify_on(db, post.user_id, "like"):
            from app.models.notification import Notification
            db.add(Notification(
                user_id=post.user_id, sender_id=current_user.id, type="like",
                title="有人赞了你的帖子", content=post.title[:50], target_id=post_id,
            ))
            # 作者收获点赞经验
            from app.core.levels import EXP_RULES, add_exp
            author = await db.get(User, post.user_id)
            if author:
                await add_exp(db, author, EXP_RULES["liked"], "liked")

    await db.commit()
    return Result(data={"liked": liked, "like_count": post.like_count})


@router.post("/{post_id}/favorite", response_model=Result)
async def toggle_favorite(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Post).where(Post.id == post_id, Post.status == "published"))
    fav_post = result.scalar_one_or_none()
    if not fav_post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    _assert_interact_allowed(fav_post, current_user)

    existing = await db.execute(
        select(Favorite).where(Favorite.user_id == current_user.id, Favorite.post_id == post_id)
    )
    record = existing.scalar_one_or_none()
    if record:
        await db.delete(record)
        favorited = False
    else:
        db.add(Favorite(user_id=current_user.id, post_id=post_id))
        favorited = True

    await db.commit()
    return Result(data={"favorited": favorited})
