from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Report(Base):
    """举报 - target_type: post/comment/user/message"""
    __tablename__ = "reports"
    # 后台按状态+时间分页拉举报：WHERE status=? ORDER BY created_at
    __table_args__ = (
        Index("idx_reports_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, comment="举报人")
    target_type: Mapped[str] = mapped_column(String(16), comment="post/comment/user/message")
    target_id: Mapped[int] = mapped_column(Integer, comment="被举报对象ID")
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="被举报内容的发布者"
    )
    reason: Mapped[str] = mapped_column(String(50), comment="举报理由")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="补充说明")
    target_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True, comment="被举报内容快照")
    status: Mapped[str] = mapped_column(
        String(16), default="pending", index=True, comment="pending/approved/rejected"
    )
    handler_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, comment="处理管理员")
    handle_remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
