"""多阶段内容审核流水线引擎

阶段1 归一化：全角转半角、英文小写、忽略空白与干扰符号
阶段2 DFA 关键词匹配（从 sensitive_words 表加载，带 category 标签）
阶段3 规则引擎（正则匹配，内置 BUILTIN_RULES）
阶段4 风险打分（block 词 +40 / mask 词 +20 / 规则按 weight，同类命中衰减）
阶段5 决策（block / review / mask / pass，支持分类级动作覆盖）
阶段6 打码（仅替换命中片段为等长 *）
阶段7 LLM 深度审核（可选，OpenAI 兼容接口，失败降级本地结果）

- 词库变更调用 invalidate() 即时生效
- 配置变更调用 invalidate_config() 即时生效
- moderate_text() 保持向后兼容（posts/comments/messages/admin 依赖）
"""
import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensitive_word import SensitiveWord

# 分类体系（6 类）
CATEGORY_CATALOG = [
    {"key": "politics", "label": "政治敏感", "hint": "涉及政治人物、事件、敏感话题", "legal": True, "severity": 5},
    {"key": "porn", "label": "色情低俗", "hint": "色情、低俗、性暗示内容", "legal": True, "severity": 4},
    {"key": "abuse", "label": "辱骂攻击", "hint": "人身攻击、辱骂、歧视", "legal": False, "severity": 3},
    {"key": "ad", "label": "广告引流", "hint": "商业广告、引流、联系方式", "legal": False, "severity": 3},
    {"key": "violence", "label": "暴力恐怖", "hint": "暴力、恐怖、自残、武器", "legal": True, "severity": 5},
    {"key": "other", "label": "其他违规", "hint": "其他违反社区公约的内容", "legal": False, "severity": 2},
]

CATEGORY_LABELS = {c["key"]: c["label"] for c in CATEGORY_CATALOG}

DEFAULT_CATEGORY_ACTIONS = {
    "politics": "block", "porn": "block", "abuse": "mask",
    "ad": "review", "violence": "block", "other": "pass",
}

RISK_LABELS = {
    "safe": "正常", "low": "低", "medium": "中", "high": "高", "critical": "严重",
}

ACTION_LABELS = {
    "pass": "通过", "mask": "打码", "review": "待复核", "block": "拦截",
}

# 内置规则
BUILTIN_RULES = [
    {"name": "url_link", "category": "ad", "severity": 3, "weight": 15, "action": "review",
     "pattern": r"https?://[^\s]+|[\w-]+\.(com|cn|net|org|io|cc|top|xyz)[^\s]*",
     "note": "URL/域名引流"},
    {"name": "phone_number", "category": "ad", "severity": 3, "weight": 15, "action": "review",
     "pattern": r"1[3-9]\d{9}", "note": "手机号"},
    {"name": "wechat_id", "category": "ad", "severity": 3, "weight": 20, "action": "review",
     "pattern": r"(微信|vx|wx|wechat)[:：\s]*[a-zA-Z0-9_-]{5,}", "note": "微信号/加微信"},
    {"name": "qq_number", "category": "ad", "severity": 3, "weight": 15, "action": "review",
     "pattern": r"qq[:：\s]*\d{5,12}", "note": "QQ号"},
    {"name": "contact_info", "category": "ad", "severity": 2, "weight": 10, "action": "mask",
     "pattern": r"(联系|加我|私聊|滴滴)[:：]?\s*[a-zA-Z0-9_-]{4,}", "note": "联系方式组合"},
    {"name": "money_earn", "category": "ad", "severity": 4, "weight": 25, "action": "block",
     "pattern": r"(刷单|日结|躺赚|无门槛|兼职.{0,6}赚钱|代写|代考|包过)", "note": "赚钱/刷单/兼职诈骗"},
]

_COMPILED_RULES = [(r, re.compile(r["pattern"], re.IGNORECASE)) for r in BUILTIN_RULES]

# 归一化（保留原逻辑）
_IGNORE_CHARS = set(
    " \t\r\n.,!?;:~·-—_/\\|@#$%^&*()[]{}<>\"'`。，！？；：～…、“”‘’（）【】《》✦✨⭐♥♡"
)
_END = "\x00"


def _normalize(text: str) -> tuple[str, list[int]]:
    """归一化文本，返回 (归一化串, 每个归一化字符对应原文索引)"""
    out_chars: list[str] = []
    idx_map: list[int] = []
    for i, ch in enumerate(text):
        if ch in _IGNORE_CHARS:
            continue
        code = ord(ch)
        if code == 0x3000:
            ch = " "
        elif 0xFF01 <= code <= 0xFF5E:
            ch = chr(code - 0xFEE0)
        out_chars.append(ch.lower())
        idx_map.append(i)
    return "".join(out_chars), idx_map


class _DFAFilter:
    def __init__(self) -> None:
        self._root: dict = {}
        self._ready = False

    def build(self, words: list[tuple[str, str, str]]) -> None:
        """words: [(word, action, category)]"""
        root: dict = {}
        for word, action, category in words:
            norm, _ = _normalize(word)
            if not norm:
                continue
            node = root
            for ch in norm:
                node = node.setdefault(ch, {})
            prev = node.get(_END)
            # block 优先；记录 (action, category)
            final_action = "block" if action == "block" or (prev and prev[0] == "block") else action
            node[_END] = (final_action, category or "other")
        self._root = root
        self._ready = True

    @property
    def ready(self) -> bool:
        return self._ready

    def scan(self, text: str) -> list[tuple[int, int, str, str, str]]:
        """返回 [(原文起始, 原文结束exclusive, 命中词, 动作, 分类)]，长词优先"""
        norm, idx_map = _normalize(text)
        hits: list[tuple[int, int, str, str, str]] = []
        n = len(norm)
        i = 0
        while i < n:
            node = self._root
            j = i
            last_end = -1
            last_value = None
            while j < n and norm[j] in node:
                node = node[norm[j]]
                j += 1
                if _END in node:
                    last_end = j
                    last_value = node[_END]
            if last_end > 0:
                start = idx_map[i]
                end = idx_map[last_end - 1] + 1
                hits.append((start, end, text[start:end], last_value[0], last_value[1]))
                i = last_end
            else:
                i += 1
        return hits


_filter = _DFAFilter()
_filter_lock = asyncio.Lock()

_config_cache: dict | None = None
_config_lock = asyncio.Lock()

DEFAULT_CONFIG = {
    "enabled": False,
    "dry_run": False,
    "local_enabled": True,
    "scope_post": True,
    "scope_comment": True,
    "scope_message": True,
    "scope_profile": False,
    "llm_enabled": False,
    "llm_trigger": "off",
    "llm_provider": "",
    "llm_base_url": "",
    "llm_model": "",
    "llm_api_key": "",
    "llm_min_score": 60,
    "llm_sample_rate": 10,
    "llm_timeout": 15,
    "llm_max_len": 2000,
    "llm_daily_limit": 0,
    "image_enabled": False,
    "image_provider": "local",
    "image_api_user": "",
    "image_api_url": "",
    "image_api_key": "",
    "image_api_secret": "",
    "block_score": 80,
    "review_score": 50,
    "mask_score": 30,
    "auto_ban_threshold": 0,
    "notify_author": True,
    "exempt_staff": False,
    "category_actions": dict(DEFAULT_CATEGORY_ACTIONS),
}


async def _ensure_loaded(db: AsyncSession) -> None:
    if _filter.ready:
        return
    async with _filter_lock:
        if _filter.ready:
            return
        try:
            result = await db.execute(
                select(SensitiveWord.word, SensitiveWord.action, SensitiveWord.category).where(
                    SensitiveWord.is_enabled == True  # noqa: E712
                )
            )
            _filter.build([(row[0], row[1], row[2]) for row in result.all()])
        except Exception:
            _filter.build([])


def invalidate() -> None:
    """词库变更后清空缓存，下次调用自动重载"""
    global _filter
    _filter = _DFAFilter()


def invalidate_config() -> None:
    """配置变更后清空进程内配置缓存"""
    global _config_cache
    _config_cache = None


async def _get_config(db: AsyncSession) -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    async with _config_lock:
        if _config_cache is not None:
            return _config_cache
        cfg = dict(DEFAULT_CONFIG)
        try:
            from app.models.ai_review import AIReviewConfig
            row = (await db.execute(
                select(AIReviewConfig).where(AIReviewConfig.id == 1)
            )).scalar_one_or_none()
            if row:
                for k in DEFAULT_CONFIG:
                    v = getattr(row, k, None)
                    if v is not None:
                        cfg[k] = v
                if not cfg.get("category_actions"):
                    cfg["category_actions"] = dict(DEFAULT_CATEGORY_ACTIONS)
        except Exception:
            pass
        _config_cache = cfg
        return _config_cache


# 结果对象
@dataclass
class ReviewResult:
    requested_action: str = "pass"       # pass/mask/review/block
    risk_level: str = "safe"            # safe/low/medium/high/critical
    risk_score: int = 0                  # 0-100
    categories: list = field(default_factory=list)
    category_labels: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    masked_text: str = ""
    blocked: bool = False
    blocked_words: list = field(default_factory=list)
    hits: list = field(default_factory=list)
    latency_ms: int = 0


@dataclass
class ModerationResult:
    """向后兼容的旧结果对象"""
    cleaned: str
    hits: list = field(default_factory=list)
    blocked: bool = False
    blocked_words: list = field(default_factory=list)


# 阶段3：规则扫描
def _scan_rules(text: str) -> list[dict]:
    out = []
    for rule, rx in _COMPILED_RULES:
        for m in rx.finditer(text):
            out.append({
                "name": rule["name"], "category": rule["category"],
                "severity": rule["severity"], "weight": rule["weight"],
                "action": rule["action"], "note": rule["note"],
                "matched": m.group(0), "span": (m.start(), m.end()),
            })
    return out


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "safe"


def _mask(text: str, keyword_hits, rule_hits) -> str:
    if not text:
        return text
    chars = list(text)
    for start, end, _w, _a, _c in keyword_hits:
        for k in range(start, min(end, len(chars))):
            chars[k] = "*"
    for rule in rule_hits:
        s, e = rule["span"]
        for k in range(s, min(e, len(chars))):
            chars[k] = "*"
    return "".join(chars)


def _should_llm(cfg: dict, score: int, user_id) -> bool:
    if not cfg.get("llm_enabled") or not cfg.get("llm_api_key"):
        return False
    trigger = cfg.get("llm_trigger", "off")
    if trigger == "off":
        return False
    if trigger == "always":
        return True
    if trigger == "suspect":
        return score >= cfg.get("llm_min_score", 60)
    if trigger == "sampled":
        rate = cfg.get("llm_sample_rate", 10)
        if score < cfg.get("llm_min_score", 60):
            return False
        return (user_id or 0) % 100 < rate
    return False


async def _call_llm(cfg: dict, text: str, target_type: str) -> dict | None:
    base = (cfg.get("llm_base_url") or "").rstrip("/")
    if not base:
        return None
    api_key = cfg.get("llm_api_key") or ""
    model = cfg.get("llm_model") or ""
    if not api_key or not model:
        return None
    timeout = cfg.get("llm_timeout", 15)
    max_len = cfg.get("llm_max_len", 2000)
    snippet = (text or "")[:max_len]
    prompt = (
        "你是校园社区内容安全审核员。判断以下内容的违规风险，只返回一个JSON对象，不要多余文字："
        "{\"risk_level\":\"safe|low|medium|high|critical\","
        "\"category\":\"politics|porn|abuse|ad|violence|other\","
        "\"reason\":\"一句简短理由\","
        "\"suggested_action\":\"pass|mask|review|block\"}。\n内容：\n" + snippet
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{base}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            return json.loads(m.group(0))
    except Exception:
        return None
    return None


# 主入口
async def moderate_content(
    db: AsyncSession,
    text: str,
    target_type: str = "post",
    user_id: int | None = None,
    dry_run: bool = False,
) -> ReviewResult:
    t0 = time.monotonic()
    cfg = await _get_config(db)
    text = text or ""

    await _ensure_loaded(db)
    keyword_hits = _filter.scan(text)
    rule_hits = _scan_rules(text)

    category_actions = cfg.get("category_actions") or {}

    score = 0
    reasons: list[str] = []
    cats: list[str] = []
    cat_count: dict[str, int] = {}
    blocked_words: list[str] = []
    all_hits: list[str] = []

    def _add(cat: str, pts: int) -> int:
        n = cat_count.get(cat, 0)
        decay = 1.0 / (2 ** n)
        cat_count[cat] = n + 1
        return pts * decay

    for start, end, word, action, cat in keyword_hits:
        all_hits.append(word)
        if category_actions.get(cat) == "pass":
            continue
        score += _add(cat, 40 if action == "block" else 20)
        reasons.append(f"命中敏感词: {word}")
        if cat not in cats:
            cats.append(cat)
        if action == "block":
            blocked_words.append(word)

    for rule in rule_hits:
        cat = rule["category"]
        if category_actions.get(cat) == "pass":
            continue
        score += _add(cat, rule["weight"])
        reasons.append(f"规则命中: {rule['name']}({rule['note']})")
        if cat not in cats:
            cats.append(cat)

    score = max(0, min(100, int(round(score))))
    risk_level = _risk_level(score)

    has_block_kw = bool(blocked_words)
    requested = "pass"
    for cat in cats:
        if category_actions.get(cat) == "block":
            requested = "block"
            break
    if requested != "block":
        if has_block_kw:
            requested = "block"
        elif score >= cfg.get("block_score", 80):
            requested = "block"
        elif score >= cfg.get("review_score", 50):
            requested = "review"
        elif score >= cfg.get("mask_score", 30):
            requested = "mask"
        else:
            requested = "pass"

    masked_text = _mask(text, keyword_hits, rule_hits)

    llm_result = None
    if _should_llm(cfg, score, user_id):
        llm_result = await _call_llm(cfg, text, target_type)
        if llm_result and not llm_result.get("error"):
            sa = llm_result.get("suggested_action")
            rank = {"pass": 0, "mask": 1, "review": 2, "block": 3}
            if sa in rank and rank[sa] > rank.get(requested, 0):
                requested = sa

    latency = int((time.monotonic() - t0) * 1000)

    evidence = {
        "keyword_hits": [
            {"word": w, "category": c, "action": a, "start": s, "end": e}
            for (s, e, w, a, c) in keyword_hits
        ],
        "rule_hits": rule_hits,
        "score_breakdown": {
            "score": score,
            "by_category": cat_count,
            "block_score": cfg.get("block_score", 80),
            "review_score": cfg.get("review_score", 50),
            "mask_score": cfg.get("mask_score", 30),
        },
        "llm_result": llm_result,
    }

    return ReviewResult(
        requested_action=requested,
        risk_level=risk_level,
        risk_score=score,
        categories=cats,
        category_labels=[CATEGORY_LABELS.get(c, c) for c in cats],
        reasons=reasons,
        evidence=evidence,
        masked_text=masked_text,
        blocked=(requested == "block"),
        blocked_words=blocked_words,
        hits=all_hits,
        latency_ms=latency,
    )


async def moderate_text(db: AsyncSession, text: str) -> ModerationResult:
    """向后兼容：mask 词替换为等长 *，block 词标记拦截"""
    if not text:
        return ModerationResult(cleaned=text)
    result = await moderate_content(db, text)
    return ModerationResult(
        cleaned=result.masked_text,
        hits=result.hits,
        blocked=result.blocked,
        blocked_words=result.blocked_words,
    )


# 集成辅助：判断 AI 审核是否对该目标启用
async def get_review_config(db: AsyncSession) -> dict:
    """公开读取进程内缓存的审核配置字典。"""
    return await _get_config(db)


_ACTION_RANK = {"pass": 0, "mask": 1, "review": 2, "block": 3}


def worst_action(a: str, b: str) -> str:
    """取两个建议动作中更严重的一个。"""
    return a if _ACTION_RANK.get(a, 0) >= _ACTION_RANK.get(b, 0) else b


async def is_review_active(db: AsyncSession, target_type: str, user=None) -> bool:
    cfg = await _get_config(db)
    if not cfg.get("enabled"):
        return False
    scope_map = {"post": "scope_post", "comment": "scope_comment", "message": "scope_message"}
    key = scope_map.get(target_type)
    if key and not cfg.get(key, True):
        return False
    if cfg.get("exempt_staff") and user and user.role == "admin":
        return False
    return True


def _default_action_for(requested: str) -> str:
    return {
        "block": "blocked", "review": "auto_pass", "mask": "auto_pass", "pass": "auto_pass",
    }.get(requested, "auto_pass")


def _default_status_for(requested: str) -> str:
    return {
        "block": "blocked", "review": "pending", "mask": "auto", "pass": "auto",
    }.get(requested, "auto")


async def record_review(
    db: AsyncSession,
    *,
    target_type: str,
    target_id: int | None,
    user_id: int | None,
    title: str,
    content: str,
    result: ReviewResult,
    dry_run: bool = False,
    action: str | None = None,
    status: str | None = None,
) -> object:
    """根据 ReviewResult 创建一条 AIReviewRecord（已 flush，未 commit）"""
    from app.models.ai_review import AIReviewRecord

    stats: dict = {}
    if user_id:
        since = datetime.utcnow() - timedelta(days=30)
        total = (await db.execute(
            select(func.count(AIReviewRecord.id)).where(
                AIReviewRecord.user_id == user_id, AIReviewRecord.created_at >= since
            )
        )).scalar()
        blocked = (await db.execute(
            select(func.count(AIReviewRecord.id)).where(
                AIReviewRecord.user_id == user_id,
                AIReviewRecord.action == "blocked",
                AIReviewRecord.created_at >= since,
            )
        )).scalar()
        stats = {"total_reviews": int(total or 0), "blocked_count": int(blocked or 0), "last_30d": {}}

    ev = dict(result.evidence or {})
    ev["reasons"] = result.reasons
    ev["categories"] = result.categories
    ev["category_labels"] = result.category_labels

    rec = AIReviewRecord(
        target_type=target_type,
        target_id=target_id,
        user_id=user_id,
        title=(title or "")[:500],
        content=content or "",
        risk_level=result.risk_level,
        risk_score=float(result.risk_score),
        category=(result.categories[0] if result.categories else ""),
        reason=(result.reasons[0] if result.reasons else ""),
        action=action or _default_action_for(result.requested_action),
        status=status or _default_status_for(result.requested_action),
        review_source="llm" if (result.evidence or {}).get("llm_result") else "keyword",
        meta={},
        requested_action=result.requested_action,
        latency_ms=result.latency_ms,
        evidence=ev,
        dry_run=dry_run,
        masked_content=result.masked_text or "",
        author_stats=stats,
    )
    db.add(rec)
    await db.flush()
    return rec


# 内置词库（用于 /lexicon/import）
BUILTIN_LEXICON = {
    "politics": ["反动", "颠覆国家", "分裂国家"],
    "porn": ["约炮", "裸聊", "一夜情", "色情", "av女优", "黄色网站"],
    "abuse": ["傻逼", "傻b", "煞笔", "操你", "狗东西", "脑残", "废物", "去死",
              "滚蛋", "垃圾人", "贱货", "王八", "草泥马"],
    "ad": ["加微信", "加vx", "加我微信", "微信号", "兼职刷单", "刷单", "日结",
           "躺赚", "无门槛", "代写论文", "代写", "代考", "包过", "出售答案",
           "兼职赚钱", "vx：", "微信：", "招代理", "减肥药", "彩票", "赌博"],
    "violence": ["杀人", "砍人", "爆炸", "自杀", "自残", "炸药", "枪支"],
    "other": ["代写作业", "代签到", "代点名"],
}

LEXICON_SOURCES = [
    {"file": "敏感词库-政治.txt", "category": "politics", "action": "block", "severity": 5, "min_len": 2, "note": "政治敏感词"},
    {"file": "敏感词库-色情.txt", "category": "porn", "action": "block", "severity": 4, "min_len": 2, "note": "色情低俗词"},
    {"file": "敏感词库-辱骂.txt", "category": "abuse", "action": "mask", "severity": 3, "min_len": 2, "note": "辱骂攻击词"},
    {"file": "敏感词库-广告.txt", "category": "ad", "action": "review", "severity": 3, "min_len": 2, "note": "广告引流词"},
]
