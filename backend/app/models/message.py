from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Conversation(Base):
    """私信会话 - user1_id 始终为两人中较小的用户ID，保证唯一"""
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("user1_id", "user2_id", name="uq_conversation_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user1_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user2_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    last_content: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="最后一条消息预览")
    last_sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Message(Base):
    """私信消息"""
    __tablename__ = "messages"
    # 按会话分页拉取消息：WHERE conversation_id=? ORDER BY created_at
    __table_args__ = (
        Index("idx_messages_conv_created", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, comment="接收方是否已读")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
