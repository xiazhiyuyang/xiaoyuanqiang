import json
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import or_, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.interaction import Favorite, Follow
from app.models.user import staff_tags_of
from app.models.notification import Notification
from app.schemas.user import (
    UserResponse, UserUpdate, UserProfileResponse, UserStats,
    ChangePassword, SecurityQuestionSet, FollowUser,
)
from app.core.security import hash_password, verify_password
from app.core.levels import progress as level_progress, ladder as level_ladder, unlocked_features
from app.schemas.common import Result, PageResponse
from app.api.deps import get_current_user, get_current_user_optional
from app.core.activity import parse_privacy, can_view, user_notify_on, log_action

router = APIRouter(prefix="/api/users", tags=["用户"])


async def _build_stats(db: AsyncSession, user_id: int) -> dict:
    post_row = await db.execute(
        select(
            func.count(Post.id),
            func.coalesce(func.sum(Post.like_count), 0),
            func.coalesce(func.sum(Post.view_count), 0),
        ).where(Post.user_id == user_id, Post.status == "published")
    )
    post_count, like_count, view_count = post_row.one()
    comment_count = await db.execute(
        select(func.count(Comment.id)).where(Comment.user_id == user_id)
    )
    favorite_count = await db.execute(
        select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
    )
    return {
        "post_count": int(post_count or 0),
        "like_count": int(like_count or 0),
        "comment_count": int(comment_count.scalar() or 0),
        "favorite_count": int(favorite_count.scalar() or 0),
        "view_count": int(view_count or 0),
    }


async def _follow_counts(db: AsyncSession, user_id: int) -> dict:
    """粉丝数 / 关注数"""
    followers = await db.execute(
        select(func.count(Follow.id)).where(Follow.following_id == user_id)
    )
    following = await db.execute(
        select(func.count(Follow.id)).where(Follow.follower_id == user_id)
    )
    return {
        "followers_count": int(followers.scalar() or 0),
        "following_count": int(following.scalar() or 0),
    }


def _completion(user: User) -> int:
    fields = [
        bool(user.avatar),
        bool(user.bio),
        user.gender not in (None, "", "unknown"),
        bool(user.grade),
        bool(user.college),
        bool(user.major),
        bool(user.location),
    ]
    return round(sum(fields) / len(fields) * 100)


@router.get("/me", response_model=Result[UserResponse])
async def get_me(user: User = Depends(get_current_user)):
    return Result(data=UserResponse.from_user(user))


@router.get("/me/overview", response_model=Result[dict])
async def get_my_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await _build_stats(db, user.id)
    stats["completion"] = _completion(user)
    stats.update(await _follow_counts(db, user.id))
    validated_stats = UserStats.model_validate(stats)
    return Result(data={
        "user": UserResponse.from_user(user).model_dump(mode="json"),
        "stats": validated_stats.model_dump(),
    })


@router.put("/me", response_model=Result[UserResponse])
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = data.model_dump(exclude_unset=True)
    if "privacy" in updates:
        privacy = updates.pop("privacy")
        user.privacy = json.dumps(privacy, ensure_ascii=False) if privacy is not None else None
    if "preferences" in updates:
        prefs = updates.pop("preferences")
        if prefs is not None:
            # 与已有偏好合并，允许前端只提交改动项
            from app.core.activity import parse_preferences
            merged = parse_preferences(user.preferences)
            merged.update(prefs)
            user.preferences = json.dumps(merged, ensure_ascii=False)
        else:
            user.preferences = None
    for field, value in updates.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return Result(data=UserResponse.from_user(user))


@router.put("/me/password", response_model=Result)
async def change_my_password(
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户修改自己的密码：必须验证原密码。"""
    # bcrypt 是同步 CPU 密集调用，放线程池避免阻塞事件循环
    if not await run_in_threadpool(verify_password, data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if await run_in_threadpool(verify_password, data.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = await run_in_threadpool(hash_password, data.new_password)
    await db.commit()
    return Result(msg="密码修改成功，下次登录请使用新密码")


@router.put("/me/security-question", response_model=Result)
async def set_my_security_question(
    data: SecurityQuestionSet,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """设置/修改密保问题（用于找回密码）。"""
    user.security_question = data.question.strip()[:100]
    user.security_answer_hash = await run_in_threadpool(
        hash_password, data.answer.strip().lower()
    )
    await db.commit()
    return Result(msg="密保问题已设置")


@router.get("/levels", response_model=Result[dict])
async def get_levels(
    user: User | None = Depends(get_current_user_optional),
):
    """等级表 + 当前用户等级进度与功能解锁情况（未登录也可看等级表）。"""
    data = {"ladder": level_ladder()}
    if user:
        data["mine"] = level_progress(user.exp or 0)
        data["features"] = unlocked_features(user.level or 1)
    return Result(data=data)


@router.get("/me/review-access", response_model=Result[dict])
async def my_review_access(user: User = Depends(get_current_user)):
    """我的审查权限：前端据此决定「我的」页是否显示内容/举报审查入口。"""
    return Result(data={
        "content_review": user.has_permission("content_review"),
        "report_review": user.has_permission("report_review"),
        "is_admin": user.role == "admin",
        "perms": user.permission_list,
    })


async def _public_profile(db: AsyncSession, user: User, viewer: User | None) -> dict:
    """按可见范围过滤后的公开主页资料。"""
    is_self = viewer is not None and viewer.id == user.id
    privacy = parse_privacy(user.privacy)
    profile = UserProfileResponse(
        id=user.id,
        uid=getattr(user, "uid", None),
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        cover_image=getattr(user, "cover_image", None),
        bio=user.bio,
        gender=user.gender if can_view(privacy["gender"], viewer, is_self) else "unknown",
        grade=user.grade if can_view(privacy["school"], viewer, is_self) else None,
        college=user.college if can_view(privacy["school"], viewer, is_self) else None,
        major=user.major if can_view(privacy["school"], viewer, is_self) else None,
        location=user.location if can_view(privacy["location"], viewer, is_self) else None,
        birthday=user.birthday if can_view(privacy["birthday"], viewer, is_self) else None,
        role=user.role,
        perm_tags=staff_tags_of(user),
        like_count=0,
        favorite_count=0,
        created_at=user.created_at,
    )
    data = profile.model_dump(mode="json")
    data["is_self"] = is_self
    # 可见范围回传给前端，用于在自己主页显示当前设置
    data["privacy"] = privacy if is_self else None
    stats = await _build_stats(db, user.id)
    data["post_count"] = stats["post_count"]
    data["like_count"] = stats["like_count"]
    data["favorite_count"] = stats["favorite_count"]
    # 关注数据：粉丝数、关注数、当前浏览者是否已关注
    data.update(await _follow_counts(db, user.id))
    data["is_following"] = False
    if viewer and not is_self:
        follow_row = await db.execute(
            select(Follow.id).where(
                Follow.follower_id == viewer.id, Follow.following_id == user.id
            )
        )
        data["is_following"] = follow_row.scalar_one_or_none() is not None
    return data


@router.get("/me/follows", response_model=Result[dict])
async def my_follows(
    type: str = Query("following", pattern="^(following|followers)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """我的关注 / 我的粉丝列表"""
    if type == "following":
        rows = await db.execute(
            select(User, Follow.created_at)
            .join(Follow, Follow.following_id == User.id)
            .where(Follow.follower_id == user.id, User.is_banned == False, User.is_deleted == False)  # noqa: E712
            .order_by(desc(Follow.created_at))
        )
        pairs = rows.all()
        items = [
            FollowUser(
                id=u.id, nickname=u.nickname, avatar=u.avatar, bio=u.bio,
                role=u.role or "user", perm_tags=staff_tags_of(u), level=u.level or 1,
                is_following=True, follow_each_other=True, created_at=at,
            ).model_dump(mode="json")
            for u, at in pairs
        ]
        return Result(data={"type": type, "items": items})
    # 粉丝：同时标出我是否回关
    rows = await db.execute(
        select(User, Follow.created_at).join(Follow, Follow.follower_id == User.id)
        .where(Follow.following_id == user.id, User.is_banned == False, User.is_deleted == False)  # noqa: E712
        .order_by(desc(Follow.created_at))
    )
    pairs = rows.all()
    my_following_ids = {
        r for r in (await db.execute(
            select(Follow.following_id).where(Follow.follower_id == user.id)
        )).scalars().all()
    }
    items = [
        FollowUser(
            id=u.id, nickname=u.nickname, avatar=u.avatar, bio=u.bio,
            role=u.role or "user", perm_tags=staff_tags_of(u), level=u.level or 1,
            is_following=(u.id in my_following_ids),
            follow_each_other=(u.id in my_following_ids),
            created_at=at,
        ).model_dump(mode="json")
        for u, at in pairs
    ]
    return Result(data={"type": type, "items": items})


@router.get("/me/posts", response_model=Result[PageResponse[dict]])
async def my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: str = Query("all", pattern="^(all|published|pending)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """我的发布：本人可见已发布 + 待审核（含匿名帖），已删除不返回。"""
    from app.api.posts import _post_to_response
    conds = [Post.user_id == user.id, Post.status != "deleted"]
    if status in ("published", "pending"):
        conds.append(Post.status == status)
    total = (await db.execute(
        select(func.count()).select_from(Post).where(*conds)
    )).scalar()
    rows = await db.execute(
        select(Post).where(*conds)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.images))
        .order_by(desc(Post.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for p in rows.scalars().all():
        d = _post_to_response(p)
        d["status"] = p.status
        items.append(d)
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.get("/me/favorites", response_model=Result[PageResponse[dict]])
async def my_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """我的收藏：按收藏时间倒序返回帖子卡片。"""
    from app.api.posts import _post_to_response
    fav_conds = [Favorite.user_id == user.id, Post.status != "deleted"]
    total = (await db.execute(
        select(func.count()).select_from(Post)
        .join(Favorite, Favorite.post_id == Post.id).where(*fav_conds)
    )).scalar()
    rows = await db.execute(
        select(Post).join(Favorite, Favorite.post_id == Post.id)
        .where(*fav_conds)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.images))
        .order_by(desc(Favorite.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )
    followed_ids = {r for r in (await db.execute(
        select(Follow.following_id).where(Follow.follower_id == user.id)
    )).scalars().all()}
    items = []
    for p in rows.scalars().all():
        d = _post_to_response(p, user.id, followed_ids=followed_ids)
        d["is_favorited"] = True
        items.append(d)
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.get("/search", response_model=Result[PageResponse[dict]])
async def search_users(
    keyword: str = Query(..., min_length=1, max_length=32),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
):
    """搜索用户：按昵称 / 登录名模糊匹配，排除封禁用户与自己。"""
    kw = keyword.strip()
    if not kw:
        return Result(data=PageResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0))
    conds = [
        User.is_banned == False,  # noqa: E712
        User.is_deleted == False,
        or_(User.nickname.contains(kw), User.username.contains(kw)),
    ]
    following_ids: set[int] = set()
    if viewer:
        following_ids = {r for r in (await db.execute(
            select(Follow.following_id).where(Follow.follower_id == viewer.id)
        )).scalars().all()}
    total = (await db.execute(select(func.count()).select_from(User).where(*conds))).scalar()
    # 自己置顶，其余按等级、注册时间
    rows = await db.execute(
        select(User).where(*conds)
        .order_by(desc(User.id == viewer.id) if viewer else User.created_at,
                  desc(User.level), User.created_at)
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for u in rows.scalars().all():
        post_cnt = (await db.execute(
            select(func.count()).select_from(Post).where(
                Post.user_id == u.id, Post.status == "published"
            )
        )).scalar()
        items.append({
            "id": u.id, "nickname": u.nickname, "username": u.username,
            "avatar": u.avatar, "bio": u.bio, "level": u.level or 1,
            "role": u.role or "user", "perm_tags": staff_tags_of(u),
            "is_following": u.id in following_ids, "post_count": int(post_cnt or 0),
            "is_self": bool(viewer and u.id == viewer.id),
        })
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.get("/suggestions", response_model=Result[list[dict]])
async def follow_suggestions(
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
):
    """推荐关注：按发帖活跃度排序，排除自己、已关注、被封禁用户。"""
    exclude = {viewer.id} if viewer else set()
    if viewer:
        rows = await db.execute(select(Follow.following_id).where(Follow.follower_id == viewer.id))
        exclude |= {r for r in rows.scalars().all()}
    stmt = (
        select(User, func.count(Post.id).label("pc"))
        .outerjoin(Post, (Post.user_id == User.id) & (Post.status == "published"))
        .where(User.is_banned == False, User.is_deleted == False)  # noqa: E712
        .group_by(User.id)
        .order_by(desc("pc"), desc(User.created_at))
        .limit(20)
    )
    result = await db.execute(stmt)
    items = []
    for u, _pc in result.all():
        if u.id in exclude:
            continue
        items.append(FollowUser(
            id=u.id, nickname=u.nickname, avatar=u.avatar, bio=u.bio,
            role=u.role or "user", perm_tags=staff_tags_of(u), level=u.level or 1,
            is_following=False,
        ).model_dump(mode="json"))
        if len(items) >= limit:
            break
    return Result(data=items)


@router.get("/{user_id}/follows", response_model=Result[dict])
async def user_follows(
    user_id: int,
    type: str = Query("following", pattern="^(following|followers)$"),
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
):
    """查看指定用户的关注 / 粉丝列表（公开）"""
    target = await db.get(User, user_id)
    if not target or target.is_banned or target.is_deleted:
        raise HTTPException(status_code=404, detail="用户不存在")
    viewer_following: set[int] = set()
    if viewer:
        rows = await db.execute(select(Follow.following_id).where(Follow.follower_id == viewer.id))
        viewer_following = {r for r in rows.scalars().all()}
    if type == "following":
        result = await db.execute(
            select(User, Follow.created_at)
            .join(Follow, Follow.following_id == User.id)
            .where(Follow.follower_id == user_id, User.is_banned == False, User.is_deleted == False)  # noqa: E712
            .order_by(desc(Follow.created_at))
        )
    else:
        result = await db.execute(
            select(User, Follow.created_at).join(Follow, Follow.follower_id == User.id)
            .where(Follow.following_id == user_id, User.is_banned == False, User.is_deleted == False)  # noqa: E712
            .order_by(desc(Follow.created_at))
        )
    items = []
    for u, at in result.all():
        is_following = u.id in viewer_following
        items.append(FollowUser(
            id=u.id, nickname=u.nickname, avatar=u.avatar, bio=u.bio,
            role=u.role or "user", perm_tags=staff_tags_of(u), level=u.level or 1,
            is_following=is_following, follow_each_other=is_following, created_at=at,
        ).model_dump(mode="json"))
    return Result(data={"type": type, "items": items})


@router.post("/{user_id}/follow", response_model=Result[dict])
async def toggle_follow(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关注 / 取消关注（toggle），返回最新状态与计数。"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    target = await db.get(User, user_id)
    if not target or target.is_banned or target.is_deleted:
        raise HTTPException(status_code=404, detail="用户不存在")
    existing = await db.execute(select(Follow).where(
        Follow.follower_id == current_user.id, Follow.following_id == user_id
    ))
    record = existing.scalar_one_or_none()
    if record:
        await db.delete(record)
        following = False
    else:
        db.add(Follow(follower_id=current_user.id, following_id=user_id))
        following = True
        if await user_notify_on(db, user_id, "follow"):
            db.add(Notification(
                user_id=user_id, sender_id=current_user.id, type="follow",
                title="有人关注了你", content=f"{current_user.nickname} 开始关注你", target_id=current_user.id,
            ))
    await db.commit()
    counts = await _follow_counts(db, user_id)
    return Result(data={"following": following, **counts}, msg="已关注" if following else "已取消关注")


@router.get("/{user_id}/follow", response_model=Result[dict])
async def follow_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
):
    """某用户的关注状态与计数"""
    target = await db.get(User, user_id)
    if not target or target.is_banned or target.is_deleted:
        raise HTTPException(status_code=404, detail="用户不存在")
    counts = await _follow_counts(db, user_id)
    is_following = False
    if viewer and viewer.id != user_id:
        row = await db.execute(select(Follow.id).where(
            Follow.follower_id == viewer.id, Follow.following_id == user_id
        ))
        is_following = row.scalar_one_or_none() is not None
    return Result(data={"is_following": is_following, **counts})


@router.get("/{user_id}", response_model=Result[dict])
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.is_banned or user.is_deleted:
        raise HTTPException(status_code=404, detail="用户不存在")
    return Result(data=await _public_profile(db, user, viewer))


@router.get("/{user_id}/posts", response_model=Result[PageResponse[dict]])
async def list_user_posts(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
):
    """TA 的主页帖子：他人看不到该用户的匿名帖。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.is_banned or user.is_deleted:
        raise HTTPException(status_code=404, detail="用户不存在")
    is_self = viewer is not None and viewer.id == user_id
    is_admin_here = viewer is not None and viewer.role == "admin"
    conditions = [Post.user_id == user_id, Post.status == "published"]
    if not (is_self or is_admin_here):
        conditions.append(Post.is_anonymous == False)  # noqa: E712
        conditions.append(or_(Post.visibility == "public", Post.visibility.is_(None)))
    query = select(Post).where(*conditions)
    count_query = select(func.count()).select_from(Post).where(*conditions)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.options(
            selectinload(Post.author), selectinload(Post.category), selectinload(Post.images)
        )
        .order_by(desc(Post.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )
    posts = result.scalars().all()
    # 浏览者的关注集合，用于帖子卡片正确回显「已关注/关注」状态
    followed_ids: set[int] = set()
    if viewer:
        _rows = await db.execute(
            select(Follow.following_id).where(Follow.follower_id == viewer.id)
        )
        followed_ids = {r for r in _rows.scalars().all()}

    def _to_dict(p: Post) -> dict:
        from app.api.posts import _post_to_response
        return _post_to_response(p, viewer.id if viewer else None, followed_ids=followed_ids)

    return Result(data=PageResponse(
        items=[_to_dict(p) for p in posts], total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))



DELETION_COOLDOWN_DAYS = 7  # 注销冷静期 7 天


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def execute_account_deletion(db: AsyncSession, user: User):
    """执行账号软删除：标记已删除、清空敏感字段、保留UID封存。"""
    user.is_deleted = True
    user.deleted_at = _now_iso()
    user.deletion_requested_at = None
    user.deletion_scheduled_at = None
    # 清空敏感个人信息（保留UID永久封存）
    user.phone = None
    user.student_id = None
    user.security_question = None
    user.security_answer_hash = None
    user.wechat_openid = None
    user.avatar = None
    user.cover_image = None
    user.bio = None
    user.privacy = None
    user.preferences = None
    # 昵称改为已注销标记
    user.nickname = f"已注销用户{user.uid or user.id}"
    await db.commit()


async def check_and_execute_deletion(db: AsyncSession, user: User) -> bool:
    """检查用户是否已到注销时间，到期则执行软删除。返回是否已执行删除。"""
    if user.is_deleted:
        return True
    if user.deletion_scheduled_at:
        try:
            scheduled = datetime.fromisoformat(user.deletion_scheduled_at)
            if datetime.now(timezone.utc) >= scheduled:
                await execute_account_deletion(db, user)
                return True
        except (ValueError, TypeError):
            pass
    return False


@router.get("/me/deletion-status", response_model=Result[dict])
async def get_deletion_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """查询账号注销状态。"""
    deleted = await check_and_execute_deletion(db, user)
    if deleted:
        raise HTTPException(status_code=401, detail="账号已注销")
    return Result(data={
        "has_request": bool(user.deletion_requested_at),
        "requested_at": user.deletion_requested_at,
        "scheduled_at": user.deletion_scheduled_at,
        "cooldown_days": DELETION_COOLDOWN_DAYS,
    })


@router.post("/me/deletion-request", response_model=Result[dict])
async def request_deletion(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交账号注销申请。需在请求体中提供密码进行身份验证。
    提交后进入7天冷静期，期间可撤销；到期自动执行注销。
    管理员账号不允许自助注销，需联系超级管理员处理。
    """
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员账号不允许自助注销，请联系超级管理员处理")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="账号已被封禁，无法申请注销")

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    password = body.get("password", "")
    if not password:
        raise HTTPException(status_code=400, detail="请输入登录密码进行身份验证")

    password_ok = await run_in_threadpool(verify_password, password, user.password_hash)
    if not password_ok:
        raise HTTPException(status_code=401, detail="密码错误，无法确认注销申请")

    now = _now_iso()
    scheduled = (datetime.now(timezone.utc) + timedelta(days=DELETION_COOLDOWN_DAYS)).isoformat(timespec="seconds")
    user.deletion_requested_at = now
    user.deletion_scheduled_at = scheduled
    await db.commit()

    await log_action(user_id=user.id, username=user.username, action="deletion_request",
                     detail=f"用户提交账号注销申请，计划注销时间：{scheduled}", request=request)

    return Result(data={
        "requested_at": now,
        "scheduled_at": scheduled,
        "cooldown_days": DELETION_COOLDOWN_DAYS,
        "message": f"注销申请已提交，{DELETION_COOLDOWN_DAYS}天冷静期后自动注销，期间可随时撤销",
    })


@router.post("/me/deletion-cancel", response_model=Result[dict])
async def cancel_deletion(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """撤销账号注销申请。仅在冷静期内可撤销。"""
    if not user.deletion_requested_at:
        raise HTTPException(status_code=400, detail="当前没有待处理的注销申请")

    deleted = await check_and_execute_deletion(db, user)
    if deleted:
        raise HTTPException(status_code=401, detail="账号已注销，无法撤销")

    user.deletion_requested_at = None
    user.deletion_scheduled_at = None
    await db.commit()

    await log_action(user_id=user.id, username=user.username, action="deletion_cancel",
                     detail="用户撤销账号注销申请", request=request)

    return Result(data={"message": "注销申请已撤销，账号恢复正常"})
