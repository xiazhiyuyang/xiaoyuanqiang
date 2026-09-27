from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class UIDAllocation(Base):
    """UID 号段分配表。

    普通号段：01000 起依次递增，由 counter 控制；
    尊享号段：00001-00999 预生成，需管理员授予。
    用户注销后 UID 进入 reserved（永久封存），管理员可手动放回分配池。
    """
    __tablename__ = "uid_allocations"

    uid: Mapped[str] = mapped_column(String(8), primary_key=True, comment="5位数字UID，如 01000")
    status: Mapped[str] = mapped_column(String(16), default="available", index=True,
                                         comment="available/assigned/reserved")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, index=True, comment="是否尊享号(00001-00999)")
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="分配给的用户ID")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


Index("ix_uid_status_premium", UIDAllocation.status, UIDAllocation.is_premium)
