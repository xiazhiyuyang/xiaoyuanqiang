"""AI 审查相关数据模型。

- ModerationRecord：每一次 AI 审查的完整流水（含证据链），
  既是「人工复核队列」的数据源，也是可解释性与复盘的基础；
- ModerationAppeal：作者对审查结果的申诉工单。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, Index, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


def _dumps(value) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(str(value), ensure_ascii=False)


def _loads(raw, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


class ModerationRecord(Base):
    """AI 审查记录 / 人工复核队列。"""

    __tablename__ = "moderation_records"
    __table_args__ = (
        Index("idx_modrec_status_created", "status", "created_at"),
        Index("idx_modrec_target", "target_type", "target_id"),
        Index("idx_modrec_user_created", "user_id", "created_at"),
        Index("idx_modrec_action_created", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    target_type: Mapped[str] = mapped_column(
        String(16), default="post", comment="post/comment/message/profile"
    )
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="内容作者")

    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审查原文（截断）")

    risk_level: Mapped[str] = mapped_column(String(16), default="safe", comment="safe/low/medium/high/critical")
    score: Mapped[int] = mapped_column(Integer, default=0, comment="综合风险分 0-100")
    categories_json: Mapped[str | None] = mapped_column("categories", Text, nullable=True, comment="违规分类 JSON")
    reasons_json: Mapped[str | None] = mapped_column("reasons", Text, nullable=True, comment="判定理由 JSON")
    evidence_json: Mapped[str | None] = mapped_column("evidence", Text, nullable=True, comment="证据链 JSON")

    action: Mapped[str] = mapped_column(String(16), default="pass", comment="实际处置 pass/mask/review/block")
    requested_action: Mapped[str] = mapped_column(
        String(16), default="pass", comment="观察模式下本应执行的动作"
    )
    source: Mapped[str] = mapped_column(String(16), default="auto", comment="auto/manual/test")
    status: Mapped[str] = mapped_column(
        String(16), default="auto", comment="auto/pending/blocked/approved/rejected"
    )
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为观察模式记录")

    handler_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    handle_remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, index=True
    )

    # ---- JSON 访问器 ----
    @property
    def categories(self) -> list[str]:
        return _loads(self.categories_json, [])

    @categories.setter
    def categories(self, value):
        self.categories_json = _dumps(value or [])

    @property
    def reasons(self) -> list[str]:
        return _loads(self.reasons_json, [])

    @reasons.setter
    def reasons(self, value):
        self.reasons_json = _dumps(value or [])

    @property
    def evidence(self) -> dict:
        return _loads(self.evidence_json, {})

    @evidence.setter
    def evidence(self, value):
        self.evidence_json = _dumps(value or {})


class ModerationAppeal(Base):
    """审查申诉：作者认为被误判时提交，进入后台申诉队列。"""

    __tablename__ = "moderation_appeals"
    __table_args__ = (
        Index("idx_appeal_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    target_type: Mapped[str] = mapped_column(String(16), default="post")
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reason: Mapped[str] = mapped_column(Text, comment="申诉理由")
    status: Mapped[str] = mapped_column(String(16), default="pending", comment="pending/accepted/rejected")
    handler_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    handle_remark: Mapped[str | None] = mapped_column(String(300), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, index=True
    )
