"""AI 智能审查流水线（对外唯一入口）。

    L0 归一化
    L1 词库 DFA（app/core/moderation.py，支持 mask/review/block + 分类 + 等级）
    L2 规则正则（联系方式/诈骗/学术不端/隐私/轻生倾向…）
    L3 特征打分（统计特征 + 违规样例相似度）
    L4 大模型语义（可选，OpenAI 兼容，默认只对可疑内容调用）
    L5 图片审查（可选）
    -> 裁决（分类策略表 + 分数门槛 + 法定红线） -> pass/mask/review/block
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import moderation
from app.core.activity import get_setting, update_settings

from .config import AIConfig, SETTING_KEY, apply_provider_preset, merge_updates, parse_config
from .decision import ACTION_LABELS, Verdict, decide
from .image import ImageVerdict, review_images
from .llm import LLMVerdict, review_text
from .rules import RuleHit, scan_rules
from .scoring import score_text
from . import domains as domain_blacklist

logger = logging.getLogger("campus-wall")

_config_cache: tuple[float, AIConfig] | None = None
_CONFIG_TTL = 30.0  # 秒；后台保存时会立即失效，这里的 TTL 只是兜底

SCENE_LABELS = {
    "post": "帖子（标题与正文）",
    "comment": "评论",
    "message": "私信",
    "profile": "用户资料（昵称/简介）",
}


@dataclass
class ReviewOutcome:
    verdict: Verdict
    record_id: int | None = None
    latency_ms: int = 0
    skipped: bool = False
    skip_reason: str = ""

    @property
    def action(self) -> str:
        return self.verdict.action

    @property
    def action_label(self) -> str:
        return ACTION_LABELS.get(self.verdict.action, self.verdict.action)

    def message(self) -> str:
        """给用户看的一句话说明。"""
        from . import categories as cats
        if self.verdict.action == "block":
            for c in self.verdict.categories:
                if cats.is_legal(c):
                    return cats.hint(c)
            if self.verdict.categories:
                return cats.hint(self.verdict.categories[0])
            return "内容未通过安全审查，不予发布。"
        if self.verdict.action == "review":
            return "内容已提交人工复核，通过后将公开展示。"
        return ""

    def as_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "latency_ms": self.latency_ms,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            **self.verdict.as_dict(),
        }


async def get_config(force: bool = False) -> AIConfig:
    global _config_cache
    now = time.time()
    if not force and _config_cache and now - _config_cache[0] < _CONFIG_TTL:
        return _config_cache[1]
    raw = await get_setting(SETTING_KEY)
    cfg = apply_provider_preset(parse_config(raw))
    _config_cache = (now, cfg)
    return cfg


def invalidate_config() -> None:
    global _config_cache
    _config_cache = None


async def save_config(db: AsyncSession, payload: dict) -> AIConfig:
    """合并并保存配置；同步刷新词库白名单与 LLM 缓存。"""
    current = await get_config(force=True)
    updated = merge_updates(current, payload)
    import json
    await update_settings(db, {SETTING_KEY: json.dumps(updated.as_dict(), ensure_ascii=False)})
    invalidate_config()
    moderation.invalidate()
    from .llm import clear_cache
    clear_cache()
    return updated


def should_call_llm(cfg: AIConfig, feature_score: int, has_hit: bool) -> bool:
    if not cfg.llm_api_key or not cfg.llm_base_url or not cfg.llm_model:
        return False
    mode = cfg.llm_trigger
    if mode == "off":
        return False
    if mode == "always":
        return True
    if mode == "sampled":
        return random.randint(1, 100) <= max(0, cfg.llm_sample_rate)
    # suspect（默认）：本地已经嗅到可疑才送去花 token
    return has_hit or feature_score >= cfg.llm_min_score


async def evaluate(
    db: AsyncSession,
    *,
    target_type: str,
    title: str = "",
    content: str = "",
    images: list[str] | None = None,
    with_llm: bool | None = None,
) -> ReviewOutcome:
    """只做审查，不落库、不处置。供后台「审查测试」与主流程复用。"""
    started = time.monotonic()
    cfg = await get_config()

    title = title or ""
    content = content or ""
    full_text = f"{title}\n{content}".strip()

    if not cfg.enabled or not cfg.local_enabled:
        v = Verdict(cleaned_title=title, cleaned_content=content)
        return ReviewOutcome(verdict=v, latency_ms=int((time.monotonic() - started) * 1000),
                             skipped=True, skip_reason="AI 审查未启用")

    # L1 词库
    title_hits = await moderation.scan_hits(db, title)
    content_hits = await moderation.scan_hits(db, content)
    lexicon_hits = title_hits + content_hits

    # L2 规则
    rule_hits = scan_rules(full_text)

    # L2b 站外域名黑名单（涉黄/涉赌/诈骗域名）
    for dom in domain_blacklist.matched_blocked_domains(full_text)[:3]:
        rule_hits.append(RuleHit(
            rule_id="blocked_domain", name="违规域名黑名单", category="illegal",
            severity=5, action="block", weight=90, matched=dom,
            note=f"链接指向已知违规域名：{dom}",
        ))

    # L3 特征打分
    feature = score_text(full_text, lexicon_hits=lexicon_hits, rule_hits=rule_hits)

    # L5 图片（与文本并行没有意义，这里顺序执行且失败不阻塞）
    image_verdict: ImageVerdict | None = None
    if cfg.image_enabled and images:
        image_verdict = await review_images(images, cfg)

    # L4 大模型
    llm_verdict: LLMVerdict | None = None
    run_llm = should_call_llm(cfg, feature.score, bool(lexicon_hits or rule_hits)) \
        if with_llm is None else bool(with_llm)
    if run_llm:
        hint_bits = []
        if lexicon_hits:
            hint_bits.append("敏感词：" + "、".join(
                dict.fromkeys([h.word for h in lexicon_hits]))[:40])
        if rule_hits:
            hint_bits.append("规则：" + "、".join(
                dict.fromkeys([h.name for h in rule_hits]))[:40])
        llm_verdict = await review_text(
            title, content, cfg,
            scene=SCENE_LABELS.get(target_type, "内容"),
            local_hint="；".join(hint_bits),
        )

    cleaned_title = moderation.mask_text(title, title_hits)
    cleaned_content = moderation.mask_text(content, content_hits)

    verdict = decide(
        cfg=cfg, target_type=target_type, title=title, content=content,
        lexicon_hits=lexicon_hits, rule_hits=rule_hits, feature=feature,
        llm_verdict=llm_verdict, image_verdict=image_verdict,
        cleaned_title=cleaned_title, cleaned_content=cleaned_content,
    )
    verdict.masked = (cleaned_title != title) or (cleaned_content != content)
    # LLM 判定打码但词库未命中具体词时，无法精确屏蔽，转人工复核而非原样公开发布
    if verdict.action == "mask" and not verdict.masked:
        verdict.action = "review"
        verdict.reasons.append("LLM 建议打码但未命中具体敏感词，转人工确认")
    return ReviewOutcome(verdict=verdict, latency_ms=int((time.monotonic() - started) * 1000))


def _should_persist(cfg: AIConfig, outcome: ReviewOutcome) -> bool:
    v = outcome.verdict
    if v.action != "pass" or v.requested_action != "pass":
        return True
    if v.categories or v.evidence.get("lexicon") or v.evidence.get("rules"):
        return True
    return v.score >= 20


async def review(
    db: AsyncSession,
    *,
    target_type: str,
    target_id: int | None,
    user_id: int | None,
    title: str = "",
    content: str = "",
    images: list[str] | None = None,
    source: str = "auto",
) -> ReviewOutcome:
    """完整审查 + 落库。调用方根据 outcome.action 决定如何处置业务数据。"""
    cfg = await get_config()
    if not cfg.enabled or not cfg.scope_on(target_type):
        return ReviewOutcome(
            verdict=Verdict(cleaned_title=title, cleaned_content=content),
            skipped=True, skip_reason="该场景未开启 AI 审查",
        )

    outcome = await evaluate(
        db, target_type=target_type, title=title, content=content, images=images,
    )
    if not _should_persist(cfg, outcome):
        return outcome

    try:
        from app.models.moderation import ModerationRecord
        v = outcome.verdict
        status = "pending" if v.action == "review" else (
            "blocked" if v.action == "block" else "auto"
        )
        record = ModerationRecord(
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            title=(title or "")[:120],
            content=(f"{title}\n{content}".strip())[:2000],
            risk_level=v.risk_level,
            score=v.score,
            categories=v.categories,
            reasons=v.reasons,
            evidence=v.evidence,
            action=v.action,
            requested_action=v.requested_action,
            source=source,
            status=status,
            latency_ms=outcome.latency_ms,
            dry_run=bool(cfg.dry_run),
        )
        db.add(record)
        await db.flush()
        outcome.record_id = record.id
    except Exception:
        logger.warning("AI 审查记录写入失败（不影响主流程）", exc_info=True)
    return outcome


async def test_review(payload_title: str, payload_content: str, target_type: str = "post",
                      images: list[str] | None = None) -> dict:
    """后台「审查测试」：不落库、不受范围开关限制，强制走全链路。"""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        outcome = await evaluate(
            db, target_type=target_type, title=payload_title,
            content=payload_content, images=images, with_llm=None,
        )
    return outcome.as_dict()


async def attach_target(db: AsyncSession, record_id: int, target_id: int) -> None:
    """内容落库拿到主键后回填审查记录的 target_id。"""
    from app.models.moderation import ModerationRecord
    record = await db.get(ModerationRecord, record_id)
    if record is not None and record.target_id is None:
        record.target_id = target_id


async def user_violation_stats(db: AsyncSession, user_id: int, days: int = 7) -> dict:
    """近 N 天的违规统计，供自动封禁与后台展示。"""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func, select

    from app.models.moderation import ModerationRecord

    since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    rows = (await db.execute(
        select(ModerationRecord.action, func.count())
        .where(ModerationRecord.user_id == user_id,
               ModerationRecord.created_at >= since,
               ModerationRecord.dry_run == False)  # noqa: E712
        .group_by(ModerationRecord.action)
    )).all()
    stats = {str(a): int(c) for a, c in rows}
    blocked = stats.get("block", 0)
    review = stats.get("review", 0)
    return {
        "blocked": blocked, "review": review,
        "total": sum(stats.values()),
        "risk_score": min(100, blocked * 12 + review * 4),
    }
