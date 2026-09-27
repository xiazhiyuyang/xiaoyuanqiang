from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, comment="分类名")
    slug: Mapped[str] = mapped_column(String(32), unique=True, comment="标识")
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="图标")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Post(Base):
    __tablename__ = "posts"
    # 信息流主查询：WHERE status='published' [AND category_id=?] ORDER BY is_top, created_at DESC
    # 个人主页：WHERE user_id=? ORDER BY created_at DESC
    __table_args__ = (
        Index("idx_posts_status_created", "status", "created_at"),
        Index("idx_posts_category_status", "category_id", "status"),
        Index("idx_posts_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(100), comment="标题")
    content: Mapped[str] = mapped_column(Text, comment="正文")
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否匿名")
    visibility: Mapped[str] = mapped_column(String(10), default="public", server_default="public", comment="public=公开 private=仅自己")
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="视频URL")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    is_top: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否置顶")
    status: Mapped[str] = mapped_column(String(16), default="published", comment="published/pending/deleted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    author: Mapped["User"] = relationship(back_populates="posts")
    category: Mapped["Category | None"] = relationship()
    images: Mapped[list["PostImage"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="PostImage.sort_order"
    )
    comments_list: Mapped[list["Comment"]] = relationship(back_populates="post", cascade="all, delete-orphan")


class PostImage(Base):
    __tablename__ = "post_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    post: Mapped["Post"] = relationship(back_populates="images")
