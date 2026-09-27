from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class OperationLog(Base):
    """后台/用户关键操作日志，只记录最基础的操作动态。"""

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="操作者ID，匿名为空")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="操作者用户名")
    action: Mapped[str] = mapped_column(String(48), index=True, comment="动作标识")
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="对象类型")
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="对象ID")
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="操作摘要")
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="success", comment="success/failed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
