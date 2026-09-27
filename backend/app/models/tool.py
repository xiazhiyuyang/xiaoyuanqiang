from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class ToolCategory(Base):
    """工具分类。"""
    __tablename__ = "tool_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), comment="分类名称")
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="URL标识")
    icon: Mapped[str] = mapped_column(String(10), default="📦", comment="图标emoji")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Tool(Base):
    """工具箱工具。收录 GitHub 上的实用工具，转化为站内可用。

    type:
      - iframe:  通过 iframe 嵌入工具页面（需工具支持跨域嵌入）
      - builtin: 站内内置实现（content 存 HTML/CSS/JS）
      - link:    外链跳转
    """
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), comment="工具名称")
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="URL标识")
    description: Mapped[str] = mapped_column(String(500), default="", comment="工具描述")
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="分类ID")
    github_url: Mapped[str] = mapped_column(String(500), default="", comment="GitHub仓库地址")
    icon: Mapped[str] = mapped_column(String(10), default="🔧", comment="图标emoji")
    tool_type: Mapped[str] = mapped_column(String(20), default="builtin", comment="iframe/builtin/link")
    embed_url: Mapped[str] = mapped_column(String(500), default="", comment="iframe嵌入地址（type=iframe时）")
    content: Mapped[str] = mapped_column(Text, default="", comment="内置工具HTML内容（type=builtin时）")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True, comment="draft/published")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="使用次数")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否推荐")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
