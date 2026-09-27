"""IP与设备封禁管理：封禁列表/封禁/解封/用户设备查看。"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.device import Device, IPBan, DeviceBan, IPWhitelist, LoginFailure
from app.core.device_mgr import AUTO_BAN_MAX_FAILURES, AUTO_BAN_WINDOW_MINUTES, AUTO_BAN_DURATIONS
from app.schemas.common import Result, PageResponse
from app.api.deps import get_admin_user
from app.core.activity import log_action

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def _parse_expires_days(days: float | None) -> str | None:
    """将封禁天数转换为到期时间ISO字符串。None或0表示永久。支持小数天（如0.0417=1小时）。"""
    if not days or days <= 0:
        return None
    return (datetime.now(timezone.utc) + timedelta(days=float(days))).isoformat(timespec="seconds")


# ==================== IP 封禁 ====================

@router.get("/bans/ips", response_model=Result[PageResponse[dict]])
async def list_ip_bans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="按IP搜索"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """IP封禁列表。"""
    conds = []
    if keyword:
        conds.append(IPBan.ip.like(f"%{keyword}%"))
    total = (await db.execute(select(func.count(IPBan.id)).where(*conds))).scalar() or 0
    result = await db.execute(
        select(IPBan).where(*conds).order_by(desc(IPBan.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for ban in result.scalars().all():
        items.append({
            "id": ban.id, "ip": ban.ip, "reason": ban.reason,
            "banned_by": ban.banned_by, "banned_by_name": ban.banned_by_name,
            "expires_at": ban.expires_at, "is_active": ban.is_active,
            "created_at": ban.created_at.isoformat() if ban.created_at else None,
        })
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.post("/bans/ips", response_model=Result[dict])
async def ban_ip(
    body: dict,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """封禁IP。body: {ip, reason, days(0=永久)}"""
    ip = (body.get("ip") or "").strip()
    reason = (body.get("reason") or "").strip()[:500]
    days = body.get("days", 0)
    if not ip:
        raise HTTPException(status_code=400, detail="IP地址不能为空")

    # 检查是否已存在
    existing = (await db.execute(select(IPBan).where(IPBan.ip == ip))).scalar_one_or_none()
    expires_at = _parse_expires_days(days if isinstance(days, int) else 0)
    if existing:
        existing.reason = reason
        existing.expires_at = expires_at
        existing.is_active = True
        existing.banned_by = admin.id
        existing.banned_by_name = admin.username
        await db.commit()
        ban = existing
    else:
        ban = IPBan(
            ip=ip, reason=reason, expires_at=expires_at,
            banned_by=admin.id, banned_by_name=admin.username, is_active=True,
        )
        db.add(ban)
        await db.commit()
        await db.refresh(ban)

    await log_action(
        user_id=admin.id, username=admin.username, action="ip_ban",
        detail=f"封禁IP：{ip}，原因：{reason or '未填写'}，{'永久' if not expires_at else f'{days}天'}",
        request=request,
    )
    return Result(data={"id": ban.id, "ip": ban.ip, "message": "IP已封禁"})


@router.delete("/bans/ips/{ip}", response_model=Result[dict])
async def unban_ip(
    ip: str,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """解封IP。"""
    ban = (await db.execute(select(IPBan).where(IPBan.ip == ip))).scalar_one_or_none()
    if not ban:
        raise HTTPException(status_code=404, detail="该IP未被封禁")
    ban.is_active = False
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="ip_unban",
        detail=f"解封IP：{ip}", request=request,
    )
    return Result(data={"message": "IP已解封"})


# ==================== 设备封禁 ====================

@router.get("/bans/devices", response_model=Result[PageResponse[dict]])
async def list_device_bans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="按设备码搜索"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """设备封禁列表。"""
    conds = []
    if keyword:
        conds.append(DeviceBan.device_code.like(f"%{keyword}%"))
    total = (await db.execute(select(func.count(DeviceBan.id)).where(*conds))).scalar() or 0
    result = await db.execute(
        select(DeviceBan).where(*conds).order_by(desc(DeviceBan.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for ban in result.scalars().all():
        items.append({
            "id": ban.id, "device_code": ban.device_code, "reason": ban.reason,
            "banned_by": ban.banned_by, "banned_by_name": ban.banned_by_name,
            "expires_at": ban.expires_at, "is_active": ban.is_active,
            "created_at": ban.created_at.isoformat() if ban.created_at else None,
        })
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


@router.post("/bans/devices", response_model=Result[dict])
async def ban_device(
    body: dict,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """封禁设备。body: {device_code, reason, days(0=永久)}"""
    device_code = (body.get("device_code") or "").strip()
    reason = (body.get("reason") or "").strip()[:500]
    days = body.get("days", 0)
    if not device_code:
        raise HTTPException(status_code=400, detail="设备码不能为空")

    existing = (await db.execute(select(DeviceBan).where(DeviceBan.device_code == device_code))).scalar_one_or_none()
    expires_at = _parse_expires_days(days if isinstance(days, int) else 0)
    if existing:
        existing.reason = reason
        existing.expires_at = expires_at
        existing.is_active = True
        existing.banned_by = admin.id
        existing.banned_by_name = admin.username
        await db.commit()
        ban = existing
    else:
        ban = DeviceBan(
            device_code=device_code, reason=reason, expires_at=expires_at,
            banned_by=admin.id, banned_by_name=admin.username, is_active=True,
        )
        db.add(ban)
        await db.commit()
        await db.refresh(ban)

    await log_action(
        user_id=admin.id, username=admin.username, action="device_ban",
        detail=f"封禁设备：{device_code}，原因：{reason or '未填写'}，{'永久' if not expires_at else f'{days}天'}",
        request=request,
    )
    return Result(data={"id": ban.id, "device_code": ban.device_code, "message": "设备已封禁"})


@router.delete("/bans/devices/{device_code}", response_model=Result[dict])
async def unban_device(
    device_code: str,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """解封设备。参数可能是设备码或指纹哈希，同时匹配两种。"""
    from sqlalchemy import or_
    ban = (await db.execute(
        select(DeviceBan).where(
            or_(DeviceBan.device_code == device_code, DeviceBan.fingerprint_hash == device_code),
            DeviceBan.is_active == True,
        )
    )).scalar_one_or_none()
    if not ban:
        raise HTTPException(status_code=404, detail="该设备未被封禁")
    ban.is_active = False
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="device_unban",
        detail=f"解封设备：{device_code}", request=request,
    )
    return Result(data={"message": "设备已解封"})


# ==================== 用户设备查看 ====================

@router.get("/users/{user_id}/devices", response_model=Result[list[dict]])
async def list_user_devices(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """查看指定用户的登录设备列表。"""
    result = await db.execute(
        select(Device).where(Device.user_id == user_id).order_by(desc(Device.last_login_at))
    )
    items = []
    for d in result.scalars().all():
        items.append({
            "id": d.id, "device_code": d.device_code, "fingerprint_hash": d.fingerprint_hash,
            "device_name": d.device_name, "platform": d.platform, "ip": d.ip,
            "ip_location": d.ip_location,
            "last_login_at": d.last_login_at.isoformat() if d.last_login_at else None,
            "login_count": d.login_count, "is_trusted": d.is_trusted,
        })
    return Result(data=items)


# ==================== IP 白名单 ====================

@router.get("/bans/whitelist", response_model=Result[list[dict]])
async def list_whitelist(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """IP白名单列表。"""
    result = await db.execute(select(IPWhitelist).order_by(desc(IPWhitelist.created_at)))
    items = []
    for w in result.scalars().all():
        items.append({
            "id": w.id, "ip": w.ip, "remark": w.remark,
            "created_by": w.created_by,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        })
    return Result(data=items)


@router.post("/bans/whitelist", response_model=Result[dict])
async def add_whitelist(
    body: dict,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """添加IP白名单。body: {ip, remark}"""
    ip = (body.get("ip") or "").strip()
    remark = (body.get("remark") or "").strip()[:200]
    if not ip:
        raise HTTPException(status_code=400, detail="IP地址不能为空")
    existing = (await db.execute(select(IPWhitelist).where(IPWhitelist.ip == ip))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="该IP已在白名单中")
    w = IPWhitelist(ip=ip, remark=remark, created_by=admin.id)
    db.add(w)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="whitelist_add",
        detail=f"添加IP白名单：{ip}，备注：{remark or '无'}", request=request,
    )
    return Result(data={"id": w.id, "ip": w.ip, "message": "已添加白名单"})


@router.delete("/bans/whitelist/{ip}", response_model=Result[dict])
async def remove_whitelist(
    ip: str,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """移除IP白名单。"""
    w = (await db.execute(select(IPWhitelist).where(IPWhitelist.ip == ip))).scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="该IP不在白名单中")
    await db.delete(w)
    await db.commit()
    await log_action(
        user_id=admin.id, username=admin.username, action="whitelist_remove",
        detail=f"移除IP白名单：{ip}", request=request,
    )
    return Result(data={"message": "已移除白名单"})


# ==================== 自动封禁统计与规则 ====================

@router.get("/bans/auto-stats", response_model=Result[dict])
async def auto_ban_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """自动封禁统计：当前各IP失败次数、自动封禁规则配置。"""
    from datetime import timedelta as td
    window_start = datetime.now(timezone.utc) - td(minutes=AUTO_BAN_WINDOW_MINUTES)
    # 统计滑动窗口内各IP失败次数（Top 20）
    result = await db.execute(
        select(LoginFailure.ip, func.count(LoginFailure.id).label("cnt"))
        .where(LoginFailure.created_at >= window_start)
        .group_by(LoginFailure.ip).order_by(desc("cnt")).limit(20)
    )
    failures = [{"ip": row[0], "count": row[1]} for row in result.all()]
    # 自动封禁数量
    auto_count = (await db.execute(
        select(func.count(IPBan.id)).where(IPBan.auto_banned == True, IPBan.is_active == True)
    )).scalar() or 0
    return Result(data={
        "rule": {
            "max_failures": AUTO_BAN_MAX_FAILURES,
            "window_minutes": AUTO_BAN_WINDOW_MINUTES,
            "durations_hours": [int(d.total_seconds() / 3600) for d in AUTO_BAN_DURATIONS],
            "permanent_after": 4,
        },
        "active_auto_bans": auto_count,
        "current_failures": failures,
    })


# ==================== 按指纹哈希封禁设备 ====================

@router.post("/bans/fingerprint", response_model=Result[dict])
async def ban_fingerprint(
    body: dict,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """按设备指纹哈希封禁（比设备码更可靠，清除缓存仍生效）。
    body: {fingerprint_hash, reason, days(0=永久)}"""
    fingerprint_hash = (body.get("fingerprint_hash") or "").strip()
    reason = (body.get("reason") or "").strip()[:500]
    days = body.get("days", 0)
    if not fingerprint_hash:
        raise HTTPException(status_code=400, detail="指纹哈希不能为空")
    existing = (await db.execute(
        select(DeviceBan).where(DeviceBan.fingerprint_hash == fingerprint_hash, DeviceBan.is_active == True)
    )).scalar_one_or_none()
    expires_at = _parse_expires_days(days if isinstance(days, int) else 0)
    if existing:
        existing.reason = reason
        existing.expires_at = expires_at
        existing.banned_by = admin.id
        existing.banned_by_name = admin.username
        await db.commit()
        ban = existing
    else:
        # 旧表 device_code 有 NOT NULL 约束，按指纹封禁时填唯一占位值
        placeholder_code = f"fp_ban_{fingerprint_hash}"
        ban = DeviceBan(
            device_code=placeholder_code, fingerprint_hash=fingerprint_hash,
            reason=reason, expires_at=expires_at,
            banned_by=admin.id, banned_by_name=admin.username, is_active=True,
        )
        db.add(ban)
        await db.commit()
        await db.refresh(ban)
    await log_action(
        user_id=admin.id, username=admin.username, action="fingerprint_ban",
        detail=f"按指纹封禁设备：{fingerprint_hash}，原因：{reason or '未填写'}，{'永久' if not expires_at else f'{days}天'}",
        request=request,
    )
    return Result(data={"id": ban.id, "fingerprint_hash": fingerprint_hash, "message": "已按指纹封禁"})
