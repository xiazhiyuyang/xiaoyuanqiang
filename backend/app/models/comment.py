from datetime import datetime, timezone

from sqlalchemy import Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Comment(Base):
    __tablename__ = "comments"
    # 按帖子分页拉取评论：WHERE post_id=? ORDER BY created_at
    __table_args__ = (
        Index("idx_comments_post_created", "post_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    reply_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    author: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="comments")
    reply_to_user: Mapped["User | None"] = relationship(foreign_keys=[reply_to_user_id])
    post: Mapped["Post"] = relationship(back_populates="comments_list")
    parent: Mapped["Comment | None"] = relationship(remote_side="Comment.id", back_populates="replies")
    replies: Mapped[list["Comment"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
