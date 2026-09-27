from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class SensitiveWord(Base):
    """敏感词 - action: mask(替换为*) / block(直接拦截)"""
    __tablename__ = "sensitive_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="敏感词")
    category: Mapped[str] = mapped_column(
        String(16), default="other",
        comment="politics政治/porn色情/abuse辱骂/ad广告/violence暴力/other其他"
    )
    action: Mapped[str] = mapped_column(String(8), default="mask", comment="mask/block")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
