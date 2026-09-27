"""邮箱验证与密码重置token模型。"""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class EmailVerification(Base):
    """邮箱验证记录（注册验证 / 密码重置）。"""
    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(128), index=True, comment="邮箱地址")
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, comment="验证token")
    scene: Mapped[str] = mapped_column(String(20), default="register", comment="register/reset")
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="关联用户ID（重置时）")
    used: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已使用")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
