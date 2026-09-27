from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.post import Post, Category
from app.models.comment import Comment
from app.models.report import Report
from app.models.interaction import LikeRecord, Favorite
from app.models.sensitive_word import SensitiveWord
from app.models.promotion import Banner, Announcement
from app.models.operation_log import OperationLog
from app.schemas.common import Result, PageResponse
from app.schemas.post import CategoryResponse
from app.schemas.report import ReportHandle, REPORT_REASONS
from app.schemas.admin import (
    CategoryCreate, SensitiveWordCreate, SensitiveWordUpdate, SensitiveWordBatch,
    BannerCreate, BannerUpdate, AnnouncementCreate, AnnouncementUpdate,
    UserRoleUpdate, SettingsUpdate, AppUpdateConfig,
)
from app.schemas.user import (
    AdminUserCreate, AdminUserUpdate, AdminResetPassword, PermissionUpdate,
    ChangePassword,
)
from app.core.security import hash_password, verify_password
from app.core.levels import level_of_exp
from app.api.deps import get_admin_user, require_permission
from app.core.moderation import invalidate as invalidate_words
from app.core.activity import (
    log_action, ACTION_LABELS, get_settings, update_settings, SETTING_DEFAULTS,
    notify_user,
)

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


async def _purge_user(db: AsyncSession, user: User):
    """彻底删除用户及其关联数据（FK 不级联的表手工清理）。"""
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


@router.get("/stats", response_model=Result[dict])
async def stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("stats_view")),
):
    today = datetime.now(timezone.utc).date()

    user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    post_count = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == "published")
    )).scalar()
    pending_count = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == "pending")
    )).scalar()
    deleted_count = (await db.execute(
        select(func.count()).select_from(Post).where(Post.status == "deleted")
    )).scalar()
    comment_count = (await db.execute(select(func.count()).select_from(Comment))).scalar()
    report_pending = (await db.execute(
        select(func.count()).select_from(Report).where(Report.status == "pending")
    )).scalar()
    banned_count = (await db.execute(
        select(func.count()).select_from(User).where(User.is_banned == True)  # noqa: E712
    )).scalar()
    today_post_count = (await db.execute(
        select(func.count()).select_from(Post).where(func.date(Post.created_at) == today)
    )).scalar()
    today_user_count = (await db.execute(
        select(func.count()).select_from(User).where(func.date(User.created_at) == today)
    )).scalar()

    agg = await db.execute(select(
        func.coalesce(func.sum(Post.view_count), 0),
        func.coalesce(func.sum(Post.like_count), 0),
    ).where(Post.status == "published"))
    total_views, total_likes = agg.one()
    total_favorites = (await db.execute(select(func.count()).select_from(Favorite))).scalar()

    since7 = datetime.now(timezone.utc) - timedelta(days=6)
    trend_rows = await db.execute(
        select(func.date(Post.created_at), func.count())
        .where(Post.created_at >= since7)
        .group_by(func.date(Post.created_at))
    )
    trend_map = {r[0]: int(r[1] or 0) for r in trend_rows.all()}
    trend = []
    for i in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        trend.append({"date": day.strftime("%m-%d"), "count": trend_map.get(day.isoformat(), 0)})

    cat_rows = await db.execute(
        select(Category.id, Category.name, Category.slug, func.count(Post.id))
        .outerjoin(Post, (Post.category_id == Category.id) & (Post.status == "published"))
        .group_by(Category.id, Category.name, Category.slug)
        .order_by(desc(func.count(Post.id)), Category.sort_order)
    )
    category_distribution = [
        {"id": r[0], "name": r[1], "slug": r[2], "count": int(r[3] or 0)}
        for r in cat_rows.all()
    ]

    recent_post_rows = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .order_by(desc(Post.created_at))
        .limit(8)
    )
    recent_posts = []
    for p in recent_post_rows.scalars().all():
        recent_posts.append({
            "id": p.id,
            "title": p.title,
            "author": (p.author.nickname if p.author else "匿名"),
            "author_id": p.user_id,
            "is_anonymous": bool(p.is_anonymous),
            "status": p.status,
            "visibility": getattr(p, "visibility", None) or "public",
            "like_count": int(p.like_count or 0),
            "comment_count": int(p.comment_count or 0),
            "view_count": int(p.view_count or 0),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    recent_user_rows = await db.execute(
        select(User).order_by(desc(User.created_at)).limit(6)
    )
    recent_users = [
        {
            "id": u.id, "nickname": u.nickname, "username": u.username,
            "role": u.role, "is_banned": bool(u.is_banned),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in recent_user_rows.scalars().all()
    ]

    return Result(data={
        # 核心计数
        "user_count": int(user_count or 0),
        "post_count": int(post_count or 0),
        "pending_count": int(pending_count or 0),
        "comment_count": int(comment_count or 0),
        "report_pending_count": int(report_pending or 0),
        "banned_count": int(banned_count or 0),
        "today_post_count": int(today_post_count or 0),
        "today_user_count": int(today_user_count or 0),
        # 互动总量
        "total_views": int(total_views or 0),
        "total_likes": int(total_likes or 0),
        "total_favorites": int(total_favorites or 0),
        # 分布与趋势
        "status_distribution": {
            "published": int(post_count or 0),
            "pending": int(pending_count or 0),
            "deleted": int(deleted_count or 0),
        },
        "category_distribution": category_distribution,
        "trend": trend,
        # 最近动态
        "recent_posts": recent_posts,
        "recent_users": recent_users,
    })


@router.get("/users", response_model=Result[PageResponse[dict]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("user_manage")),
):
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if keyword:
        cond = User.username.contains(keyword) | User.nickname.contains(keyword)
        query = query.where(cond)
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    items = [{
        "id": u.id, "uid": getattr(u, "uid", None), "username": u.username, "nickname": u.nickname,
        "avatar": u.avatar, "cover_image": getattr(u, "cover_image", None),
        "role": u.role, "is_banned": u.is_banned,
        "gender": u.gender, "college": u.college, "grade": u.grade,
        "major": getattr(u, "major", None), "location": getattr(u, "location", None),
        "bio": u.bio, "phone": u.phone,
        "exp": u.exp or 0, "level": u.level or 1,
        "perms": u.permission_list,
        "has_security": bool(u.security_question),
        "created_at": u.created_at,
    } for u in users]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.post("/users/{user_id}/ban", response_model=Result)
async def toggle_ban(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("user_manage")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能操作自己的账号")
    if user.role == "admin" and not user.is_banned:
        raise HTTPException(status_code=400, detail="管理员账号不能被封禁")
    user.is_banned = not user.is_banned
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_ban",
        target_type="user", target_id=user.id,
        detail=("封禁" if user.is_banned else "解封") + f"用户 {user.nickname}",
        request=request,
    )
    return Result(data={"is_banned": user.is_banned},
                  msg=("已封禁" if user.is_banned else "已解封"))


@router.put("/users/{user_id}/role", response_model=Result)
async def set_user_role(
    user_id: int,
    data: UserRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id and data.role != "admin":
        raise HTTPException(status_code=400, detail="不能取消自己的管理员角色")
    old_role = user.role
    user.role = data.role
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_role",
        target_type="user", target_id=user.id,
        detail=f"用户 {user.nickname} 角色 {old_role} → {data.role}", request=request,
    )
    return Result(msg="角色已更新")


@router.get("/permissions/catalog", response_model=Result[dict])
async def permission_catalog(admin: User = Depends(get_admin_user)):
    """可授予普通用户的单项权限目录（授权不等于管理员）。"""
    return Result(data={
        "permissions": [{"key": k, "label": v} for k, v in User.PERMISSION_CATALOG.items()]
    })


@router.post("/users", response_model=Result[dict])
async def admin_create_user(
    data: AdminUserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """管理员直接创建用户账号。"""
    exists = await db.execute(select(User).where(func.lower(User.username) == data.username))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该用户名已存在")
    user = User(
        username=data.username, nickname=data.nickname,
        password_hash=await run_in_threadpool(hash_password, data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_create",
        target_type="user", target_id=user.id,
        detail=f"创建用户 {user.nickname}（{user.username}，角色 {user.role}）", request=request,
    )
    return Result(data={"id": user.id}, msg="用户已创建")


@router.put("/users/{user_id}", response_model=Result)
async def admin_update_user(
    user_id: int,
    data: AdminUserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("user_manage")),
):
    """修改用户昵称/资料/角色/经验。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    updates = data.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] is not None:
        if user.id == admin.id and updates["role"] != "admin":
            raise HTTPException(status_code=400, detail="不能取消自己的管理员角色")
        user.role = updates.pop("role")
    if "exp" in updates and updates["exp"] is not None:
        user.exp = updates.pop("exp")
        user.level = level_of_exp(user.exp)
    updates.pop("exp", None)
    for field in ("nickname", "gender", "college", "grade", "major", "location", "bio", "phone", "avatar", "cover_image"):
        if field in updates and updates[field] is not None:
            setattr(user, field, updates[field])
    if user.nickname:
        user.nickname = user.nickname.strip()[:32]
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_update",
        target_type="user", target_id=user.id,
        detail=f"修改用户资料：{user.nickname}", request=request,
    )
    return Result(msg="用户资料已更新")


@router.delete("/users/{user_id}", response_model=Result)
async def admin_delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """彻底删除用户账号及其内容。"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员账号不能被删除")
    name = user.nickname
    await _purge_user(db, user)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_delete",
        target_type="user", target_id=user_id,
        detail=f"删除用户：{name}", request=request,
    )
    return Result(msg=f"用户 {name} 已删除")


@router.post("/users/{user_id}/password", response_model=Result)
async def admin_reset_password(
    user_id: int,
    data: AdminResetPassword,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """管理员重置任意用户密码。不填 new_password 则自动生成 8 位随机密码并返回。"""
    import secrets, string
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.new_password:
        new_pwd = data.new_password
    else:
        alphabet = string.ascii_letters + string.digits
        while True:
            new_pwd = ''.join(secrets.choice(alphabet) for _ in range(8))
            if any(c.isalpha() for c in new_pwd) and any(c.isdigit() for c in new_pwd):
                break
    user.password_hash = await run_in_threadpool(hash_password, new_pwd)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_reset_password",
        target_type="user", target_id=user.id,
        detail=f"重置用户 {user.nickname} 的密码", request=request,
    )
    return Result(data={"new_password": new_pwd}, msg="密码已重置")


@router.put("/users/{user_id}/permissions", response_model=Result)
async def admin_set_permissions(
    user_id: int,
    data: PermissionUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """授予/收回普通用户的单项权限（内容审查、举报审查等），不改变其角色。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员默认拥有全部权限，无需单独授权")
    perms = sorted(set(data.permissions))
    user.permissions = ",".join(perms)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_set_perms",
        target_type="user", target_id=user.id,
        detail=f"设置 {user.nickname} 的权限：{('、'.join(perms)) or '无'}", request=request,
    )
    return Result(data={"perms": perms}, msg="授权已更新")


@router.get("/uids/stats", response_model=Result[dict])
async def admin_uid_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """UID 号段统计：尊享总数/可用/已分配、封存数、普通已分配。"""
    from app.core.uid_allocator import get_uid_stats
    return Result(data=await get_uid_stats(db))


@router.get("/uids", response_model=Result[dict])
async def admin_list_uids(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="available/assigned/reserved"),
    is_premium: bool | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """UID 池列表，支持按状态/类型/关键词筛选。"""
    from app.models.uid import UIDAllocation
    from app.models.user import User as UserModel
    q = select(UIDAllocation)
    cq = select(func.count()).select_from(UIDAllocation)
    if status:
        q = q.where(UIDAllocation.status == status)
        cq = cq.where(UIDAllocation.status == status)
    if is_premium is not None:
        q = q.where(UIDAllocation.is_premium == is_premium)
        cq = cq.where(UIDAllocation.is_premium == is_premium)
    if keyword:
        cond = UIDAllocation.uid.contains(keyword)
        if keyword.isdigit():
            uid_match = (await db.execute(select(UIDAllocation.uid).where(UIDAllocation.user_id == int(keyword)))).scalars().all()
            if uid_match:
                cond = cond | UIDAllocation.uid.in_(uid_match)
        q = q.where(cond)
        cq = cq.where(cond)
    total = (await db.execute(cq)).scalar()
    rows = (await db.execute(
        q.order_by(UIDAllocation.uid.asc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    # 批量查用户名
    user_ids = [r.user_id for r in rows if r.user_id]
    user_map = {}
    if user_ids:
        us = (await db.execute(select(UserModel.id, UserModel.nickname, UserModel.username).where(UserModel.id.in_(user_ids)))).all()
        user_map = {u.id: {"nickname": u.nickname, "username": u.username} for u in us}
    items = [{
        "uid": r.uid, "status": r.status, "is_premium": r.is_premium,
        "user_id": r.user_id,
        "user_nickname": user_map.get(r.user_id, {}).get("nickname") if r.user_id else None,
        "user_username": user_map.get(r.user_id, {}).get("username") if r.user_id else None,
        "assigned_at": r.assigned_at,
    } for r in rows]
    return Result(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.post("/uids/{uid}/unreserve", response_model=Result)
async def admin_unreserve_uid(
    uid: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """把封存的 UID 重新放回分配池。"""
    from app.core.uid_allocator import unreserve_uid
    ok = await unreserve_uid(db, uid)
    if not ok:
        raise HTTPException(status_code=400, detail="该 UID 不存在或未处于封存状态")
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_uid_unreserve",
        detail=f"解封 UID {uid}，重新进入分配池", request=request,
    )
    return Result(msg=f"UID {uid} 已解封，重新进入分配池")


@router.post("/uids/grant-premium", response_model=Result[dict])
async def admin_grant_premium_uid(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """授予用户尊享号（自动取最小可用尊享号）。body: {user_id}"""
    from app.core.uid_allocator import allocate_premium_uid
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 如果用户已有普通 UID，先封存
    if user.uid:
        from app.core.uid_allocator import reserve_uid as _reserve
        await _reserve(db, user.id)
    uid = await allocate_premium_uid(db, user.id)
    if not uid:
        raise HTTPException(status_code=400, detail="尊享号已全部授予完毕，无可用号段")
    user.uid = uid
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_uid_grant_premium",
        target_type="user", target_id=user.id,
        detail=f"授予用户 {user.nickname} 尊享号 {uid}", request=request,
    )
    return Result(data={"uid": uid}, msg=f"已授予 {user.nickname} 尊享号 {uid}")


@router.post("/uids/assign", response_model=Result)
async def admin_assign_uid(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """手动把指定 UID 分配给用户。body: {uid, user_id}"""
    from app.core.uid_allocator import assign_specific_uid
    uid = (data.get("uid") or "").strip()
    user_id = data.get("user_id")
    if not uid or not user_id:
        raise HTTPException(status_code=400, detail="缺少 uid 或 user_id")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 封存用户原有 UID
    if user.uid and user.uid != uid:
        from app.core.uid_allocator import reserve_uid as _reserve
        await _reserve(db, user.id)
    ok = await assign_specific_uid(db, uid, user.id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"UID {uid} 不可用（不存在或已被分配/未封存）")
    user.uid = uid
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_uid_assign",
        target_type="user", target_id=user.id,
        detail=f"手动分配 UID {uid} 给用户 {user.nickname}", request=request,
    )
    return Result(msg=f"UID {uid} 已分配给 {user.nickname}")


@router.put("/account/password", response_model=Result)
async def admin_change_own_password(
    data: ChangePassword,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """管理员修改自己的密码。"""
    if not await run_in_threadpool(verify_password, data.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if await run_in_threadpool(verify_password, data.new_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    admin.password_hash = await run_in_threadpool(hash_password, data.new_password)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="change_password",
        detail="管理员修改自己的密码", request=request,
    )
    return Result(msg="密码修改成功")


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


@router.post("/categories", response_model=Result[CategoryResponse])
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("category_manage")),
):
    exists = await db.execute(select(Category).where(Category.slug == data.slug))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分类标识已存在")
    category = Category(
        name=data.name, slug=data.slug,
        icon=data.icon, sort_order=data.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return Result(data=CategoryResponse.model_validate(category))


@router.delete("/categories/{category_id}", response_model=Result)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("category_manage")),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    await db.delete(category)
    await db.commit()
    return Result(msg="已删除")


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
                select(User).where(User.id == report.target_user_id)
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


@router.get("/sensitive-words", response_model=Result[PageResponse[dict]])
async def list_sensitive_words(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    keyword: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    query = select(SensitiveWord)
    count_query = select(func.count()).select_from(SensitiveWord)
    if keyword:
        query = query.where(SensitiveWord.word.contains(keyword))
        count_query = count_query.where(SensitiveWord.word.contains(keyword))
    if category:
        query = query.where(SensitiveWord.category == category)
        count_query = count_query.where(SensitiveWord.category == category)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(SensitiveWord.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    words = result.scalars().all()
    items = [{
        "id": w.id, "word": w.word, "category": w.category,
        "action": w.action, "is_enabled": w.is_enabled, "created_at": w.created_at,
    } for w in words]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.post("/sensitive-words", response_model=Result)
async def create_sensitive_word(
    data: SensitiveWordCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    word = data.word.strip()
    exists = await db.execute(select(SensitiveWord).where(SensitiveWord.word == word))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该敏感词已存在")
    db.add(SensitiveWord(word=word, category=data.category, action=data.action, is_enabled=data.is_enabled))
    await db.commit()
    invalidate_words()
    return Result(msg="已添加")


@router.put("/sensitive-words/{word_id}", response_model=Result)
async def update_sensitive_word(
    word_id: int,
    data: SensitiveWordUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    result = await db.execute(select(SensitiveWord).where(SensitiveWord.id == word_id))
    sw = result.scalar_one_or_none()
    if not sw:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    if data.category is not None:
        sw.category = data.category
    if data.action is not None:
        sw.action = data.action
    if data.is_enabled is not None:
        sw.is_enabled = data.is_enabled
    if data.word:
        sw.word = data.word.strip()
    await db.commit()
    invalidate_words()
    return Result(msg="已更新")


@router.delete("/sensitive-words/{word_id}", response_model=Result)
async def delete_sensitive_word(
    word_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    result = await db.execute(select(SensitiveWord).where(SensitiveWord.id == word_id))
    sw = result.scalar_one_or_none()
    if not sw:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    await db.delete(sw)
    await db.commit()
    invalidate_words()
    return Result(msg="已删除")


@router.post("/sensitive-words/batch", response_model=Result)
async def batch_import_sensitive_words(
    data: SensitiveWordBatch,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    category = data.category
    action = data.action
    raw_words = [w.strip() for w in data.text.replace("，", "\n").replace(",", "\n").splitlines()]
    words = [w for w in raw_words if w]
    if not words:
        raise HTTPException(status_code=400, detail="没有可导入的词")
    existing = (await db.execute(select(SensitiveWord.word).where(SensitiveWord.word.in_(words)))).all()
    existing_set = {row[0] for row in existing}
    added = 0
    for w in words:
        if w in existing_set:
            continue
        db.add(SensitiveWord(word=w, category=category, action=action))
        existing_set.add(w)
        added += 1
    await db.commit()
    invalidate_words()
    return Result(msg=f"导入完成：新增 {added} 个，跳过已存在 {len(words) - added} 个",
                  data={"added": added, "skipped": len(words) - added})


def _banner_dict(b: Banner) -> dict:
    return {
        "id": b.id, "title": b.title, "image_url": b.image_url,
        "link_url": b.link_url, "theme": b.theme,
        "sort_order": b.sort_order, "is_active": b.is_active,
        "created_at": b.created_at,
    }


@router.get("/banners", response_model=Result[list[dict]])
async def admin_list_banners(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banners = (await db.execute(
        select(Banner).order_by(desc(Banner.sort_order), Banner.id.desc())
    )).scalars().all()
    return Result(data=[_banner_dict(b) for b in banners])


@router.post("/banners", response_model=Result[dict])
async def admin_create_banner(
    data: BannerCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banner = Banner(**data.model_dump())
    db.add(banner)
    await db.commit()
    await db.refresh(banner)
    return Result(data=_banner_dict(banner), msg="已添加")


@router.put("/banners/{banner_id}", response_model=Result[dict])
async def admin_update_banner(
    banner_id: int,
    data: BannerUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banner = (await db.execute(select(Banner).where(Banner.id == banner_id))).scalar_one_or_none()
    if not banner:
        raise HTTPException(status_code=404, detail="广告不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(banner, field, value)
    await db.commit()
    await db.refresh(banner)
    return Result(data=_banner_dict(banner), msg="已更新")


@router.delete("/banners/{banner_id}", response_model=Result)
async def admin_delete_banner(
    banner_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banner = (await db.execute(select(Banner).where(Banner.id == banner_id))).scalar_one_or_none()
    if not banner:
        raise HTTPException(status_code=404, detail="广告不存在")
    await db.delete(banner)
    await db.commit()
    return Result(msg="已删除")


def _announcement_dict(a: Announcement) -> dict:
    return {
        "id": a.id, "content": a.content, "link_url": a.link_url,
        "sort_order": a.sort_order, "is_active": a.is_active,
        "created_at": a.created_at,
    }


@router.get("/announcements", response_model=Result[list[dict]])
async def admin_list_announcements(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    items = (await db.execute(
        select(Announcement).order_by(desc(Announcement.sort_order), Announcement.id.desc())
    )).scalars().all()
    return Result(data=[_announcement_dict(a) for a in items])


@router.post("/announcements", response_model=Result[dict])
async def admin_create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    ann = Announcement(**data.model_dump())
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return Result(data=_announcement_dict(ann), msg="已添加")


@router.put("/announcements/{ann_id}", response_model=Result[dict])
async def admin_update_announcement(
    ann_id: int,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    ann = (await db.execute(select(Announcement).where(Announcement.id == ann_id))).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ann, field, value)
    await db.commit()
    await db.refresh(ann)
    return Result(data=_announcement_dict(ann), msg="已更新")


@router.delete("/announcements/{ann_id}", response_model=Result)
async def admin_delete_announcement(
    ann_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    ann = (await db.execute(select(Announcement).where(Announcement.id == ann_id))).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    await db.delete(ann)
    await db.commit()
    return Result(msg="已删除")


@router.get("/logs", response_model=Result[PageResponse[dict]])
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    action: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("operation_log")),
):
    query = select(OperationLog)
    count_query = select(func.count()).select_from(OperationLog)
    if action:
        query = query.where(OperationLog.action == action)
        count_query = count_query.where(OperationLog.action == action)
    if keyword:
        cond = OperationLog.username.contains(keyword) | OperationLog.detail.contains(keyword)
        query = query.where(cond)
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()
    items = [{
        "id": lg.id, "user_id": lg.user_id, "username": lg.username,
        "action": lg.action, "action_text": ACTION_LABELS.get(lg.action, lg.action),
        "target_type": lg.target_type, "target_id": lg.target_id,
        "detail": lg.detail, "ip": lg.ip, "status": lg.status,
        "created_at": lg.created_at,
    } for lg in logs]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.get("/logs/actions", response_model=Result[list[dict]])
async def log_actions(
    admin: User = Depends(require_permission("operation_log")),
):
    return Result(data=[{"action": k, "label": v} for k, v in ACTION_LABELS.items()])


_BOOL_SETTING_KEYS = (
    "allow_register", "maintenance", "post_need_review", "allow_anonymous",
    "allow_video", "message_open", "show_level",
)
_INT_SETTING_KEYS = ("review_random_rate",)


_ENUM_FALLBACK = {
    "notice_mode": ("marquee", {"marquee", "vertical", "static"}),
    "review_mode": ("off", {"off", "random", "all"}),
    "default_theme": ("galaxy", {"galaxy", "ocean", "forest", "sunset", "rose", "midnight"}),
}


def _settings_form(data: dict) -> dict:
    """把存储的字符串配置转成后台表单需要的 bool/int/str。"""
    form = {}
    for key in SETTING_DEFAULTS:
        val = data.get(key, SETTING_DEFAULTS.get(key, ""))
        if key in _BOOL_SETTING_KEYS:
            form[key] = str(val) == "1"
        elif key in _INT_SETTING_KEYS:
            try:
                form[key] = int(float(val))
            except (TypeError, ValueError):
                form[key] = 20
        elif key in _ENUM_FALLBACK:
            default, allowed = _ENUM_FALLBACK[key]
            form[key] = val if val in allowed else default
        else:
            form[key] = val or ""
    return form


@router.get("/settings", response_model=Result[dict])
async def get_site_settings(
    admin: User = Depends(get_admin_user),
):
    data = await get_settings()
    return Result(data=_settings_form(data))


@router.put("/settings", response_model=Result[dict])
async def set_site_settings(
    data: SettingsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    changes = {}
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if key not in SETTING_DEFAULTS:
            continue
        if value is None:
            continue
        if isinstance(value, bool):
            changes[key] = "1" if value else "0"
        elif isinstance(value, int):
            changes[key] = str(value)
        else:
            changes[key] = (value or "").strip()
    if changes.get("post_need_review") == "1":
        changes["review_mode"] = "all"
    if not changes:
        raise HTTPException(status_code=400, detail="没有需要更新的设置")
    result = await update_settings(db, changes)
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_setting_update",
        detail=f"修改站点设置：{'、'.join(changes.keys())}", request=request,
    )
    return Result(data=_settings_form(result), msg="设置已保存")


@router.get("/app-update", response_model=Result[dict])
async def admin_get_app_update(
    admin: User = Depends(get_admin_user),
):
    from app.api.app_update import _load_config
    return Result(data=_load_config())


@router.put("/app-update", response_model=Result[dict])
async def admin_save_app_update(
    data: AppUpdateConfig,
    request: Request,
    admin: User = Depends(get_admin_user),
):
    import json
    from app.api.app_update import CONFIG_PATH
    cfg = data.model_dump()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_app_update",
        detail=f"保存App更新配置：{cfg.get('latest_version')}（code {cfg.get('version_code')}）",
        request=request,
    )
    return Result(data=cfg, msg="更新配置已保存")
