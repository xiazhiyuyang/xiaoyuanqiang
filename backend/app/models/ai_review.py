"""AI 智能审查模型"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Float,
)
from sqlalchemy.orm import relationship
from app.database import Base


class AIReviewRecord(Base):
    """AI 审查记录"""
    __tablename__ = "ai_review_records"

    id = Column(Integer, primary_key=True)
    target_type = Column(String(20), default="post")  # post/comment/message
    target_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(500), default="")
    content = Column(Text, default="")
    risk_level = Column(String(20), default="low")  # safe/low/medium/high/critical
    risk_score = Column(Float, default=0.0)
    category = Column(String(50), default="")  # 主要违规分类 key
    reason = Column(Text, default="")  # 判定依据
    action = Column(String(20), default="pending")  # blocked/auto_pass/manual_pass/manual_reject
    status = Column(String(20), default="pending")  # pending/reviewed/blocked/auto/appealed
    review_source = Column(String(20), default="keyword")  # keyword/rule/llm/image
    meta = Column(JSON, default=dict)  # 额外信息

    # ---- 扩展字段 ----
    requested_action = Column(String(20), default="pass")  # AI 建议动作 pass/mask/review/block
    latency_ms = Column(Integer, default=0)  # 审核耗时
    evidence = Column(JSON, default=dict)  # 完整证据链
    dry_run = Column(Boolean, default=False)  # 是否观察模式
    masked_content = Column(Text, default="")  # 打码后内容
    author_stats = Column(JSON, default=dict)  # 作者近30天风险画像

    handled_by = Column(Integer, nullable=True)
    handled_remark = Column(String(500), default="")
    handled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")


class AIReviewConfig(Base):
    """AI 审查配置（单行存储）"""
    __tablename__ = "ai_review_config"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, default=False)
    llm_enabled = Column(Boolean, default=False)
    image_enabled = Column(Boolean, default=False)
    llm_provider = Column(String(50), default="")
    llm_base_url = Column(String(500), default="")
    llm_api_key = Column(String(500), default="")
    llm_model = Column(String(100), default="")
    image_provider = Column(String(50), default="")
    image_api_key = Column(String(500), default="")
    image_api_secret = Column(String(500), default="")
    auto_block_high_risk = Column(Boolean, default=True)
    manual_review_medium_risk = Column(Boolean, default=True)
    category_actions = Column(JSON, default=dict)
    llm_presets = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---- 扩展字段 ----
    dry_run = Column(Boolean, default=False)
    local_enabled = Column(Boolean, default=True)
    scope_post = Column(Boolean, default=True)
    scope_comment = Column(Boolean, default=True)
    scope_message = Column(Boolean, default=True)
    scope_profile = Column(Boolean, default=False)
    llm_trigger = Column(String(20), default="off")  # off/suspect/sampled/always
    llm_min_score = Column(Integer, default=60)
    llm_sample_rate = Column(Integer, default=10)
    llm_timeout = Column(Integer, default=15)
    llm_max_len = Column(Integer, default=2000)
    llm_daily_limit = Column(Integer, default=0)
    image_api_user = Column(String(200), default="")
    image_api_url = Column(String(500), default="")
    block_score = Column(Integer, default=80)
    review_score = Column(Integer, default=50)
    mask_score = Column(Integer, default=30)
    auto_ban_threshold = Column(Integer, default=0)
    notify_author = Column(Boolean, default=True)
    exempt_staff = Column(Boolean, default=False)


class AIReviewAppeal(Base):
    """AI 审查申诉"""
    __tablename__ = "ai_review_appeals"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("ai_review_records.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending/accepted/rejected
    handled_by = Column(Integer, nullable=True)
    handled_remark = Column(String(500), default="")
    handled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    record = relationship("AIReviewRecord", foreign_keys=[record_id], lazy="joined")
