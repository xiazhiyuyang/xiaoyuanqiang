from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Device(Base):
    """用户登录设备记录，用于设备识别与封禁。"""
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, comment="关联用户ID")
    device_code: Mapped[str] = mapped_column(String(128), index=True, comment="设备唯一标识码（指纹哈希+本地盐）")
    fingerprint_hash: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="浏览器设备指纹哈希（Canvas/WebGL/屏幕等，清除缓存仍稳定）")
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="设备名称（如 iPhone 15 / Chrome on Windows）")
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="平台：ios/android/h5/windows/mac")
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="登录IP地址")
    ip_location: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="IP归属地（省/市）")
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True, comment="完整User-Agent")
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, comment="最后登录时间")
    login_count: Mapped[int] = mapped_column(Integer, default=1, comment="该设备登录次数")
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为受信任设备")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class IPBan(Base):
    """IP封禁记录。支持单个IP和CIDR段，支持递增封禁时长。"""
    __tablename__ = "ip_bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(64), index=True, comment="被封禁的IP地址或CIDR段（如 192.168.1.0/24）")
    is_cidr: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为CIDR网段封禁")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="封禁原因")
    banned_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="封禁管理员ID，0表示系统自动封禁")
    banned_by_name: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="封禁管理员名称")
    ban_count: Mapped[int] = mapped_column(Integer, default=1, comment="该IP累计被封禁次数（用于递增封禁时长）")
    auto_banned: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为系统自动封禁（连续登录失败触发）")
    expires_at: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="到期时间 ISO，为空表示永久封禁")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="是否生效中")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class DeviceBan(Base):
    """设备封禁记录。支持按设备码和指纹哈希封禁。"""
    __tablename__ = "device_bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="被封禁的设备码（可为空，按指纹封禁时为空）")
    fingerprint_hash: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="被封禁的设备指纹哈希（清除缓存仍生效）")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="封禁原因")
    banned_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="封禁管理员ID")
    banned_by_name: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="封禁管理员名称")
    expires_at: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="到期时间 ISO，为空表示永久封禁")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="是否生效中")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class IPWhitelist(Base):
    """IP白名单。白名单内IP永不被自动封禁，管理员手动封禁仍生效。"""
    __tablename__ = "ip_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="白名单IP或CIDR段")
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="备注")
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="添加管理员ID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class LoginFailure(Base):
    """登录失败记录。用于连续失败自动封禁IP（参考 fail2ban 滑动窗口计数）。"""
    __tablename__ = "login_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(64), index=True, comment="失败IP")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="尝试登录的用户名")
    device_code: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="尝试登录的设备码")
    fingerprint_hash: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="设备指纹哈希")
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="失败原因（密码错误/用户不存在/已封禁）")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
