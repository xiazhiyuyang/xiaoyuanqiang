"""设备与IP封禁管理核心模块。
参考 FingerprintJS（浏览器指纹）和 fail2ban（滑动窗口自动封禁）的核心原理。
- 设备指纹：前端采集 Canvas/WebGL/屏幕/时区等信号计算哈希，清除缓存仍稳定
- IP封禁：支持单个IP和CIDR段，递增封禁时长，白名单豁免
- 自动封禁：连续登录失败达到阈值自动封禁IP（1h→24h→7d→永久）
"""
import hashlib
import ipaddress
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, IPBan, DeviceBan, IPWhitelist, LoginFailure

# ============ 自动封禁配置（参考 fail2ban） ============
AUTO_BAN_MAX_FAILURES = 10          # 滑动窗口内最大失败次数
AUTO_BAN_WINDOW_MINUTES = 10        # 滑动窗口时长（分钟）
AUTO_BAN_DURATIONS = [              # 递增封禁时长（小时），第N次封禁对应索引N-1
    timedelta(hours=1),
    timedelta(hours=24),
    timedelta(days=7),
]
AUTO_BAN_PERMANENT_AFTER = 4        # 第4次及以后永久封禁


def get_client_ip(request) -> str:
    """从请求中获取真实客户端IP（兼容 Nginx 反向代理）。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request) -> str:
    return request.headers.get("user-agent", "") or ""


def parse_platform(ua: str) -> str:
    ua = (ua or "").lower()
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "windows" in ua:
        return "windows"
    if "macintosh" in ua or "mac os" in ua:
        return "mac"
    if "linux" in ua:
        return "linux"
    return "h5"


def parse_device_name(ua: str) -> str:
    ua = ua or ""
    if "iPhone" in ua:
        return "iPhone"
    if "iPad" in ua:
        return "iPad"
    if "Android" in ua:
        if "Mobile" in ua:
            return "Android 手机"
        return "Android 平板"
    if "Windows" in ua:
        if "Edg" in ua:
            return "Windows / Edge"
        if "Chrome" in ua:
            return "Windows / Chrome"
        if "Firefox" in ua:
            return "Windows / Firefox"
        return "Windows 设备"
    if "Macintosh" in ua:
        return "Mac 设备"
    return "浏览器设备"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ============ IP 白名单 ============
async def is_ip_whitelisted(db: AsyncSession, ip: str) -> bool:
    """检查IP是否在白名单中（支持精确匹配和CIDR段匹配）。"""
    result = await db.execute(select(IPWhitelist))
    whitelist = result.scalars().all()
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for entry in whitelist:
        try:
            if "/" in entry.ip:
                network = ipaddress.ip_network(entry.ip, strict=False)
                if ip_obj in network:
                    return True
            elif entry.ip == ip:
                return True
        except ValueError:
            continue
    return False


# ============ IP 封禁检查 ============
def _ip_matches_ban(ip: str, ban_ip: str, is_cidr: bool) -> bool:
    """检查IP是否匹配封禁规则（支持CIDR段）。"""
    if not is_cidr:
        return ip == ban_ip
    try:
        ip_obj = ipaddress.ip_address(ip)
        network = ipaddress.ip_network(ban_ip, strict=False)
        return ip_obj in network
    except ValueError:
        return False


async def check_ip_banned(db: AsyncSession, ip: str) -> IPBan | None:
    """检查IP是否被封禁。返回生效中的封禁记录，未封禁返回None。
    白名单IP跳过自动封禁检查，但管理员手动封禁仍生效。"""
    result = await db.execute(
        select(IPBan).where(IPBan.is_active == True)
    )
    bans = result.scalars().all()
    now = datetime.now(timezone.utc)
    for ban in bans:
        # 到期自动解封
        if ban.expires_at:
            expires = _parse_iso(ban.expires_at)
            if expires and expires <= now:
                ban.is_active = False
                continue
        if _ip_matches_ban(ip, ban.ip, ban.is_cidr):
            # 白名单IP只豁免自动封禁，不豁免管理员手动封禁
            if ban.auto_banned and await is_ip_whitelisted(db, ip):
                continue
            return ban
    return None


# ============ 设备封禁检查 ============
async def check_device_banned(
    db: AsyncSession, device_code: str | None, fingerprint_hash: str | None
) -> DeviceBan | None:
    """检查设备是否被封禁。同时检查设备码和指纹哈希。
    指纹哈希封禁比设备码更可靠（清除localStorage后仍生效）。"""
    conditions = []
    if device_code:
        conditions.append(DeviceBan.device_code == device_code)
    if fingerprint_hash:
        conditions.append(DeviceBan.fingerprint_hash == fingerprint_hash)
    if not conditions:
        return None
    result = await db.execute(
        select(DeviceBan).where(and_(DeviceBan.is_active == True, or_(*conditions)))
    )
    bans = result.scalars().all()
    now = datetime.now(timezone.utc)
    for ban in bans:
        if ban.expires_at:
            expires = _parse_iso(ban.expires_at)
            if expires and expires <= now:
                ban.is_active = False
                continue
        return ban
    return None


# ============ 设备登录记录 ============
async def record_device_login(
    db: AsyncSession,
    user_id: int,
    device_code: str,
    request,
    fingerprint_hash: str | None = None,
) -> Device | None:
    """记录用户登录设备信息。如果设备已存在则更新，否则新建。
    设备码为空时，用 IP+UA 的哈希生成临时设备标识。"""
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    platform = parse_platform(ua)
    device_name = parse_device_name(ua)

    if not device_code:
        raw = f"{ip}|{ua}"
        device_code = "auto_" + hashlib.md5(raw.encode()).hexdigest()[:16]

    result = await db.execute(
        select(Device).where(Device.user_id == user_id, Device.device_code == device_code)
    )
    device = result.scalar_one_or_none()

    if device:
        device.last_login_at = datetime.now(timezone.utc)
        device.login_count += 1
        device.ip = ip
        device.user_agent = ua
        device.platform = platform
        device.device_name = device_name
        if fingerprint_hash and not device.fingerprint_hash:
            device.fingerprint_hash = fingerprint_hash
    else:
        device = Device(
            user_id=user_id,
            device_code=device_code,
            fingerprint_hash=fingerprint_hash,
            device_name=device_name,
            platform=platform,
            ip=ip,
            user_agent=ua,
        )
        db.add(device)
    await db.commit()
    return device


# ============ 登录失败记录与自动封禁（参考 fail2ban） ============
async def record_login_failure(
    db: AsyncSession,
    ip: str,
    username: str | None = None,
    device_code: str | None = None,
    fingerprint_hash: str | None = None,
    reason: str | None = None,
) -> None:
    """记录一次登录失败，并检查是否触发自动封禁。"""
    # 白名单IP不记录失败、不触发自动封禁
    if await is_ip_whitelisted(db, ip):
        return

    failure = LoginFailure(
        ip=ip, username=username, device_code=device_code,
        fingerprint_hash=fingerprint_hash, reason=reason,
    )
    db.add(failure)

    # 清理超过窗口的旧记录
    window_start = datetime.now(timezone.utc) - timedelta(minutes=AUTO_BAN_WINDOW_MINUTES)
    await db.execute(delete(LoginFailure).where(LoginFailure.created_at < window_start))

    # 统计滑动窗口内的失败次数
    count_result = await db.execute(
        select(func.count(LoginFailure.id)).where(
            LoginFailure.ip == ip,
            LoginFailure.created_at >= window_start,
        )
    )
    failure_count = count_result.scalar() or 0
    await db.commit()

    # 达到阈值触发自动封禁
    if failure_count >= AUTO_BAN_MAX_FAILURES:
        await _auto_ban_ip(db, ip, failure_count)


async def _auto_ban_ip(db: AsyncSession, ip: str, failure_count: int) -> None:
    """自动封禁IP（递增时长，参考 fail2ban 的递增封禁策略）。"""
    # 统计该IP历史封禁次数
    count_result = await db.execute(
        select(func.count(IPBan.id)).where(IPBan.ip == ip, IPBan.auto_banned == True)
    )
    prior_bans = count_result.scalar() or 0
    ban_number = prior_bans + 1  # 本次是第几次封禁

    # 计算封禁时长
    if ban_number >= AUTO_BAN_PERMANENT_AFTER:
        expires_at = None  # 永久封禁
        duration_text = "永久"
    else:
        duration = AUTO_BAN_DURATIONS[min(ban_number - 1, len(AUTO_BAN_DURATIONS) - 1)]
        expires_at = (datetime.now(timezone.utc) + duration).isoformat(timespec="seconds")
        duration_text = f"{duration.total_seconds() / 3600:.0f}小时" if duration.total_seconds() < 86400 else f"{duration.days}天"

    # 先解除该IP已有的自动封禁（用新的更长时长替换）
    existing = await db.execute(
        select(IPBan).where(IPBan.ip == ip, IPBan.auto_banned == True, IPBan.is_active == True)
    )
    for ban in existing.scalars().all():
        ban.is_active = False

    ban = IPBan(
        ip=ip,
        is_cidr=False,
        reason=f"系统自动封禁：{AUTO_BAN_WINDOW_MINUTES}分钟内连续登录失败{failure_count}次（第{ban_number}次封禁，{duration_text}）",
        banned_by=0,
        banned_by_name="系统",
        ban_count=ban_number,
        auto_banned=True,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(ban)

    # 清空该IP的失败记录
    await db.execute(delete(LoginFailure).where(LoginFailure.ip == ip))
    await db.commit()


async def clear_login_failures(db: AsyncSession, ip: str) -> None:
    """登录成功后清空该IP的失败记录。"""
    await db.execute(delete(LoginFailure).where(LoginFailure.ip == ip))
    await db.commit()


# ============ 封禁/解封操作 ============
async def ban_ip(
    db: AsyncSession, ip: str, reason: str,
    banned_by: int, banned_by_name: str,
    duration_hours: int | None = None, is_cidr: bool = False,
) -> IPBan:
    """封禁IP。duration_hours为None表示永久封禁。"""
    # 先解除已有封禁
    existing = await db.execute(
        select(IPBan).where(IPBan.ip == ip, IPBan.is_active == True)
    )
    for ban in existing.scalars().all():
        ban.is_active = False

    expires_at = None
    if duration_hours and duration_hours > 0:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat(timespec="seconds")

    ban = IPBan(
        ip=ip, is_cidr=is_cidr, reason=reason,
        banned_by=banned_by, banned_by_name=banned_by_name,
        ban_count=1, auto_banned=False, expires_at=expires_at, is_active=True,
    )
    db.add(ban)
    await db.commit()
    await db.refresh(ban)
    return ban


async def unban_ip(db: AsyncSession, ip: str) -> bool:
    """解封IP。"""
    result = await db.execute(
        select(IPBan).where(IPBan.ip == ip, IPBan.is_active == True)
    )
    bans = result.scalars().all()
    if not bans:
        return False
    for ban in bans:
        ban.is_active = False
    await db.commit()
    return True


async def ban_device(
    db: AsyncSession,
    device_code: str | None,
    fingerprint_hash: str | None,
    reason: str,
    banned_by: int,
    banned_by_name: str,
    duration_hours: int | None = None,
) -> DeviceBan:
    """封禁设备。可按设备码或指纹哈希封禁，指纹哈希封禁更可靠。"""
    conditions = []
    if device_code:
        conditions.append(DeviceBan.device_code == device_code)
    if fingerprint_hash:
        conditions.append(DeviceBan.fingerprint_hash == fingerprint_hash)
    if conditions:
        existing = await db.execute(
            select(DeviceBan).where(and_(DeviceBan.is_active == True, or_(*conditions)))
        )
        for ban in existing.scalars().all():
            ban.is_active = False

    expires_at = None
    if duration_hours and duration_hours > 0:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat(timespec="seconds")

    # 旧表 device_code 有 NOT NULL 约束，按指纹封禁时填唯一占位值
    actual_device_code = device_code
    if not actual_device_code and fingerprint_hash:
        actual_device_code = f"fp_ban_{fingerprint_hash}"

    ban = DeviceBan(
        device_code=actual_device_code, fingerprint_hash=fingerprint_hash,
        reason=reason, banned_by=banned_by, banned_by_name=banned_by_name,
        expires_at=expires_at, is_active=True,
    )
    db.add(ban)
    await db.commit()
    await db.refresh(ban)
    return ban


async def unban_device(db: AsyncSession, device_code: str | None, fingerprint_hash: str | None) -> bool:
    """解封设备。"""
    conditions = []
    if device_code:
        conditions.append(DeviceBan.device_code == device_code)
    if fingerprint_hash:
        conditions.append(DeviceBan.fingerprint_hash == fingerprint_hash)
    if not conditions:
        return False
    result = await db.execute(
        select(DeviceBan).where(and_(DeviceBan.is_active == True, or_(*conditions)))
    )
    bans = result.scalars().all()
    if not bans:
        return False
    for ban in bans:
        ban.is_active = False
    await db.commit()
    return True


# 需要导入 or_
from sqlalchemy import or_  # noqa: E402
