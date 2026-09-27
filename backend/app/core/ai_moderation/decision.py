"""裁决层：把词库命中、规则命中、特征分、大模型结论、图片结论
收敛成唯一一个处置动作（pass / mask / review / block）。

优先级：分类策略表（后台可配） 与 分数门槛 取更严厉者；
法定违法信息（categories 里 legal=True 且 severity 5）无条件拦截。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import categories as cats
from .config import AIConfig
from .image import ImageVerdict
from .llm import LLMVerdict
from .scoring import FeatureScore

_ORDER = {"pass": 0, "mask": 1, "review": 2, "block": 3}
_LEVEL_BY_ORDER = {0: "safe", 1: "low", 2: "medium", 3: "high"}
_LADDER = ("pass", "mask", "review", "block")

# 受保护分类：无论如何都不允许自动拦截，最高只能转人工复核。
# self_harm（轻生倾向）如果把内容直接删掉，等于把求助信号一起屏蔽掉，
# 既可能造成真实伤害，也丢掉了人工关怀介入的机会。
PROTECTED_CATEGORIES = frozenset({"self_harm"})

# 分数对分类策略的升级权限：最多升级一级，避免「分类说是打码、分数却直接删帖」的不可预期行为
_MAX_ESCALATION = 0

ACTION_LABELS = {
    "pass": "通过",
    "mask": "打码后发布",
    "review": "转人工复核",
    "block": "拦截",
}

RISK_LABELS = cats.RISK_LABELS


@dataclass
class Verdict:
    action: str = "pass"
    requested_action: str = "pass"      # 观察模式下记录的「本应执行」的动作
    risk_level: str = "safe"
    score: int = 0
    categories: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    cleaned_title: str = ""
    cleaned_content: str = ""
    masked: bool = False

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "requested_action": self.requested_action,
            "risk_level": self.risk_level,
            "score": self.score,
            "categories": self.categories,
            "reasons": self.reasons,
            "evidence": self.evidence,
            "masked": self.masked,
        }


def _strictest(actions: list[str]) -> str:
    best = "pass"
    for a in actions:
        if _ORDER.get(a, 0) > _ORDER.get(best, 0):
            best = a
    return best


def _escalate(action: str, levels: int = 1) -> str:
    """把动作沿 pass -> mask -> review -> block 升级，最多到 block。"""
    idx = _LADDER.index(action) if action in _LADDER else 0
    return _LADDER[min(len(_LADDER) - 1, idx + max(0, levels))]


def _score_action(score: int, cfg: AIConfig) -> str:
    if score >= cfg.block_score:
        return "block"
    if score >= cfg.review_score:
        return "review"
    if score >= cfg.mask_score:
        return "mask"
    return "pass"


def decide(
    *,
    cfg: AIConfig,
    target_type: str,
    title: str,
    content: str,
    lexicon_hits: list,
    rule_hits: list,
    feature: FeatureScore,
    llm_verdict: LLMVerdict | None,
    image_verdict: ImageVerdict | None,
    cleaned_title: str,
    cleaned_content: str,
) -> Verdict:
    v = Verdict(cleaned_title=cleaned_title, cleaned_content=cleaned_content)

    present: list[str] = []
    reasons: list[str] = []

    for h in lexicon_hits:
        c = getattr(h, "category", "other") or "other"
        if c not in present:
            present.append(c)
    for h in rule_hits:
        if h.category not in present:
            present.append(h.category)
    if feature.exemplar_hits:
        for ex in feature.exemplar_hits:
            if ex["category"] not in present:
                present.append(ex["category"])
    if llm_verdict:
        for c in llm_verdict.categories:
            if c not in present:
                present.append(c)
    if image_verdict and image_verdict.max_score:
        for c in image_verdict.categories:
            if c not in present:
                present.append(c)

    score = feature.score
    if llm_verdict and llm_verdict.score:
        # 大模型的自评分通常偏保守，按其置信度做一次融合
        conf = llm_verdict.confidence if llm_verdict.confidence > 0 else 0.7
        blended = int(llm_verdict.score * (0.6 + 0.4 * conf))
        score = max(score, blended)
    if image_verdict and image_verdict.max_score:
        score = max(score, image_verdict.max_score)
    score = max(0, min(100, score))
    v.score = score

    # 设计取向：后台「分类策略表」是运营意图的唯一权威来源，
    # 特征分不能随意把它抬高（否则把 abuse 设成打码也会被分数直接删帖，行为不可预期）。
    # 因此分类明确时：分数最多把动作升级一级；分类全部为「放行」时尊重运营的放行决定。
    if present:
        policy_actions = [cfg.action_for(c) for c in present]
        all_pass = all(a == "pass" for a in policy_actions)
        if all_pass:
            action = "pass"
        else:
            cat_action = _strictest([a for a in policy_actions if a != "pass"])
            score_action = _score_action(score, cfg)
            if _ORDER[score_action] > _ORDER[cat_action]:
                action = _escalate(cat_action, _MAX_ESCALATION)
                if _ORDER[action] > _ORDER[cat_action]:
                    reasons.append(
                        f"综合风险分 {score} 偏高，已在分类默认处置「{ACTION_LABELS.get(cat_action, cat_action)}」"
                        f"基础上升级为「{ACTION_LABELS.get(action, action)}」"
                    )
            else:
                action = cat_action
    else:
        all_pass = False
        action = _score_action(score, cfg)

    # 否则会被分类策略表（例如 ad 默认 review）架空，管理员改了词却不生效。
    for h in lexicon_hits:
        act = getattr(h, "action", "mask")
        if act in ("block", "review", "mask"):
            action = _strictest([action, act])

    legal_hits = [c for c in present if cats.is_legal(c)]
    if legal_hits:
        action = _strictest([action, "block"])
        for c in legal_hits:
            reasons.append(f"{cats.label(c)}：{cats.hint(c)}")

    protected_hits = [c for c in present if c in PROTECTED_CATEGORIES]
    if protected_hits and not legal_hits:
        if _ORDER[action] > _ORDER["review"]:
            action = "review"
        reasons.insert(0, "该类内容不会自动删除：已转人工并保留原文，请人工及时关怀跟进")

    if image_verdict and image_verdict.local_only and image_verdict.max_score:
        if _ORDER[action] > _ORDER["review"]:
            action = "review"
        reasons.append(
            f"图片肤色特征异常（得分 {image_verdict.max_score}），本地启发式仅供参考，已转人工确认"
        )
    elif image_verdict and image_verdict.max_score >= cfg.image_block_score and not image_verdict.local_only:
        action = _strictest([action, "block"])
        reasons.append(f"图片审查判定违规（得分 {image_verdict.max_score}）")
    elif image_verdict and image_verdict.max_score >= cfg.image_review_score and not image_verdict.local_only:
        action = _strictest([action, "review"])
        reasons.append(f"图片存在疑似违规内容（得分 {image_verdict.max_score}）")

    if lexicon_hits:
        words = "、".join(dict.fromkeys([getattr(h, "word", "") for h in lexicon_hits]))[:50]
        worst = max((getattr(h, "severity", 3) or 3) for h in lexicon_hits)
        reasons.append(f"命中违规词库 {len(lexicon_hits)} 处（最高等级 {worst}/5）：{words}")
    if rule_hits:
        names = "、".join(dict.fromkeys([h.name for h in rule_hits]))[:60]
        reasons.append(f"命中审查规则：{names}")
        for h in rule_hits:
            if h.note:
                reasons.append(h.note)
                break
    for sig in feature.signals:
        if sig.weight >= 15:
            reasons.append(f"{sig.name}：{sig.detail}")
    if llm_verdict and llm_verdict.reasons:
        reasons.extend([f"AI 语义判定：{r}" for r in llm_verdict.reasons])
    if llm_verdict and llm_verdict.risk_level in ("high", "critical") and not llm_verdict.reasons:
        reasons.append("AI 语义判定为高风险内容")
    if not reasons and action != "pass":
        reasons.append(f"综合风险分 {score}，超过处置门槛")

    # 去重并限长
    seen = set()
    uniq = []
    for r in reasons:
        r = (r or "").strip()
        if r and r not in seen:
            seen.add(r)
            uniq.append(r[:120])
    v.reasons = uniq[:6]

    order = _ORDER[action]
    level = _LEVEL_BY_ORDER[order]
    if score >= 90 or (llm_verdict and llm_verdict.risk_level == "critical"):
        level = "critical"
    elif score >= 75 or (llm_verdict and llm_verdict.risk_level == "high"):
        level = "high"
    elif score >= 40 or (llm_verdict and llm_verdict.risk_level == "medium"):
        level = "medium"
    elif score >= 20:
        level = "low"
    else:
        level = "safe"
    if action == "block":
        level = "critical" if (legal_hits or score >= 90) else "high"
    elif action == "review":
        level = level if level in ("medium", "high", "critical") else "medium"
    elif action == "mask":
        level = level if level in ("low", "medium") else "low"
    v.risk_level = level

    v.categories = present[:8]
    v.requested_action = action

    if cfg.dry_run:
        v.action = "pass"
        if action != "pass":
            v.reasons.insert(0, f"【观察模式】本应执行「{ACTION_LABELS.get(action, action)}」，未实际处置")
    else:
        v.action = action

    v.evidence = {
        "lexicon": [
            {"word": getattr(h, "word", ""), "action": getattr(h, "action", ""),
             "category": getattr(h, "category", "other"), "severity": getattr(h, "severity", 3)}
            for h in lexicon_hits[:20]
        ],
        "rules": [
            {"id": h.rule_id, "name": h.name, "category": h.category,
             "severity": h.severity, "matched": h.matched}
            for h in rule_hits[:20]
        ],
        "features": feature.as_dict(),
        "llm": llm_verdict.as_dict() if llm_verdict else None,
        "image": image_verdict.as_dict() if image_verdict and image_verdict.checked else None,
        "target_type": target_type,
    }
    return v
