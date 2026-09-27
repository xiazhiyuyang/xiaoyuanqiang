"""用户管理：列表/回收站/恢复/封禁/角色/创建/修改/删除/重置密码/权限/UID 号段。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.common import Result, PageResponse
from app.schemas.admin import UserRoleUpdate
from app.schemas.user import (
    AdminUserCreate, AdminUserUpdate, AdminResetPassword, PermissionUpdate,
    ChangePassword,
)
from app.core.security import hash_password, verify_password
from app.core.levels import level_of_exp
from app.api.deps import get_admin_user, require_permission
from app.core.activity import log_action
from app.services import user_service
from app.api.admin import _utils

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


# ---------- 敏感操作二次确认 token ----------
@router.post("/confirm-token", response_model=Result[dict])
async def issue_confirm_token(
    body: dict,
    admin: User = Depends(get_admin_user),
):
    """生成敏感操作一次性确认 token（5 分钟有效、一次性）。
    body: {action: delete_user | reset_password, target_id: int}"""
    action = body.get("action")
    target_id = body.get("target_id")
    if action not in ("delete_user", "reset_password"):
        raise HTTPException(status_code=400, detail="不支持的确认操作")
    if not isinstance(target_id, int):
        raise HTTPException(status_code=400, detail="target_id 必须为整数")
    token = _utils.issue_confirm_token(admin.id, action, target_id)
    return Result(data={"confirm_token": token, "expires_in": _utils._CONFIRM_TTL},
                  msg="确认令牌已生成，请在 5 分钟内通过请求头 X-Confirm-Token 完成操作")


# ---------- 用户列表 / 回收站 ----------
@router.get("/users", response_model=Result[PageResponse[dict]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("user_manage")),
):
    query = select(User).where(User.is_deleted == False)  # noqa: E712
    count_query = select(func.count()).select_from(User).where(User.is_deleted == False)  # noqa: E712
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


@router.get("/users/recycle", response_model=Result[PageResponse[dict]])
async def list_recycle_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("user_manage")),
):
    """回收站：列出已软删除（注销）的用户。"""
    query = select(User).where(User.is_deleted == True)  # noqa: E712
    count_query = select(func.count()).select_from(User).where(User.is_deleted == True)  # noqa: E712
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(User.deleted_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    items = [{
        "id": u.id, "uid": getattr(u, "uid", None), "username": u.username,
        "nickname": u.nickname, "avatar": u.avatar, "role": u.role,
        "deleted_at": u.deleted_at, "created_at": u.created_at,
    } for u in users]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.post("/users/{user_id}/restore", response_model=Result)
async def admin_restore_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """从回收站恢复已注销用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.is_deleted:
        raise HTTPException(status_code=400, detail="该用户未在回收站中")
    await user_service.restore_user(db, user)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_restore",
        target_type="user", target_id=user_id,
        detail=f"恢复用户：{user.nickname}", request=request,
    )
    return Result(msg=f"用户 {user.nickname} 已恢复")


@router.post("/users/{user_id}/ban", response_model=Result)
async def toggle_ban(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("user_manage")),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))  # noqa: E712
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能操作自己的账号")
    if user.role == "admin" and not user.is_banned:
        raise HTTPException(status_code=400, detail="管理员账号不能被封禁")
    is_banned = await user_service.toggle_ban(user)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_ban",
        target_type="user", target_id=user.id,
        detail=("封禁" if is_banned else "解封") + f"用户 {user.nickname}",
        request=request,
    )
    return Result(data={"is_banned": is_banned},
                  msg=("已封禁" if is_banned else "已解封"))


@router.put("/users/{user_id}/role", response_model=Result)
async def set_user_role(
    user_id: int,
    data: UserRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))  # noqa: E712
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
    existing = await user_service.get_user_by_username(db, data.username)
    if existing:
        if existing.is_deleted:
            raise HTTPException(status_code=400, detail="该用户名已被注销，无法创建")
        raise HTTPException(status_code=400, detail="该用户名已存在")
    user = await user_service.create_user(
        db, username=data.username, nickname=data.nickname,
        password=data.password, role=data.role,
    )
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
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))  # noqa: E712
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
    """软删除用户账号：移入回收站，禁止登录与展示，保留数据。"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
    _utils.consume_confirm_token(request.headers.get("x-confirm-token"), admin.id, "delete_user", user_id)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.is_deleted:
        raise HTTPException(status_code=400, detail="该用户已在回收站中")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员账号不能被删除")
    name = user.nickname
    await user_service.soft_delete_user(db, user)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_user_delete",
        target_type="user", target_id=user_id,
        detail=f"注销用户：{name}（软删除，移入回收站）", request=request,
    )
    return Result(msg=f"用户 {name} 已注销并移入回收站")


@router.post("/users/{user_id}/password", response_model=Result)
async def admin_reset_password(
    user_id: int,
    data: AdminResetPassword,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """管理员重置任意用户密码。不填 new_password 则自动生成强随机密码并返回。"""
    _utils.consume_confirm_token(request.headers.get("x-confirm-token"), admin.id, "reset_password", user_id)
    import secrets, string
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))  # noqa: E712
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.new_password:
        from app.schemas.user import validate_password_strength
        new_pwd = validate_password_strength(data.new_password)
    else:
        alphabet = string.ascii_letters + string.digits
        new_pwd = ''.join(secrets.choice(alphabet) for _ in range(8))
    user.password_hash = await run_in_threadpool(hash_password, new_pwd)
    user_service.reset_lockout(user)
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
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))  # noqa: E712
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


# ---------- UID 号段管理 ----------
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
    user = (await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))).scalar_one_or_none()  # noqa: E712
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
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
    user = (await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))).scalar_one_or_none()  # noqa: E712
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
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
    from app.schemas.user import validate_password_strength
    new_pwd = validate_password_strength(data.new_password)
    admin.password_hash = await run_in_threadpool(hash_password, new_pwd)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="change_password",
        detail="管理员修改自己的密码", request=request,
    )
    return Result(msg="密码修改成功")
