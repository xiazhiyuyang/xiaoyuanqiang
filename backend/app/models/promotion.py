from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Banner(Base):
    """首页轮播广告位"""
    __tablename__ = "banners"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(60), comment="广告标题")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="广告图，为空时用主题色卡片")
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="点击跳转链接")
    theme: Mapped[str] = mapped_column(String(20), default="blue", comment="无图时的渐变主题")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序，越大越靠前")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否上架")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Announcement(Base):
    """首页滚动公告位"""
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(String(200), comment="公告内容")
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="点击跳转链接")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否展示")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
