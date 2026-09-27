from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Notification(Base):
    """通知 - type: like/comment/system"""
    __tablename__ = "notifications"
    # 未读红点 / 按用户分页拉通知：WHERE user_id=? [AND is_read=?] ORDER BY created_at
    __table_args__ = (
        Index("idx_notifications_user_read", "user_id", "is_read"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, comment="接收者")
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="触发者")
    type: Mapped[str] = mapped_column(String(16), comment="like/comment/system")
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="相关帖子/评论ID")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
