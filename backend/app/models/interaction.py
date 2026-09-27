from datetime import datetime, timezone

from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class LikeRecord(Base):
    """点赞记录 - target_type: post / comment"""
    __tablename__ = "like_records"
    __table_args__ = (UniqueConstraint("user_id", "target_id", "target_type", name="uq_like"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    target_type: Mapped[str] = mapped_column(String(16), comment="post/comment")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Favorite(Base):
    """收藏帖子"""
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_favorite"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Follow(Base):
    """用户关注关系：follower_id 关注 following_id"""
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follow"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, comment="粉丝（关注者）"
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, comment="被关注者"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
