"""大模型语义审查层（OpenAI 兼容协议）。

设计要点：
- **可选**：未配置 API Key 或调用失败时自动降级，绝不阻塞用户发布；
- **省钱**：默认只对本地判定「可疑」的内容调用（llm_trigger=suspect），
  带抽样比例、送审门槛、超长截断、结果缓存、每日调用上限；
- **容错**：超时/网络错误/返回非 JSON 都只记录并返回 None，
  连续失败触发熔断，避免每条内容都白等一次网络超时；
- **不阻塞事件循环**：全程 httpx.AsyncClient，纯异步 I/O。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field

import httpx

from .config import AIConfig
from .normalize import compact

logger = logging.getLogger("campus-wall")

_CATEGORY_KEYS = (
    "politics", "terror", "illegal", "porn", "minor", "fraud",
    "privacy", "academic", "violence", "self_harm", "ad", "abuse", "spam", "other",
)

SYSTEM_PROMPT = """你是中国高校「校园墙」社区的资深内容安全审查员，需要判断学生投稿是否违反社区规范。

【违规分类】categories 只能从下列 key 中选（可多选，正常内容留空数组）：
- politics 政治敏感（攻击党和国家、煽动对立、传播政治谣言）
- terror 暴恐极端（宣扬暴力恐怖、极端主义、民族仇恨）
- illegal 违法犯罪（枪支弹药、毒品、假证假章、管制物品交易）
- porn 色情低俗（性交易、色情资源、露骨描写）
- minor 涉未成年人（任何涉未成年人的不良内容）
- fraud 诈骗赌博（刷单返利、校园贷、网络赌博、跑分洗钱、虚假兼职）
- privacy 隐私侵害（曝光他人手机号/身份证/学号/宿舍、人肉开盒）
- academic 学术不端（代写论文、代考、出售答案、代课代签）
- violence 暴力威胁（人身威胁、约架、校园欺凌）
- self_harm 轻生倾向（表达自杀或自残意愿）
- ad 广告引流（商业推广、站外导流、留联系方式、拉群）
- abuse 辱骂攻击（人身攻击、恶毒诅咒、地域/性别歧视）
- spam 刷屏灌水（无意义重复、标题党）
- other 其他违规

【风险等级】risk_level 取 safe / low / medium / high / critical

【判定要求】
1. 必须结合语境判断。出现单个敏感词不等于违规，例如「打人」出现在球赛讨论里是正常的；
   但如果是对同学的攻击、威胁或约架，则属于 abuse / violence。
2. 要识别隐晦表达：嘲讽、阴阳怪气、反串、谐音字、拼音缩写、拆字（如「傻B」「加V信」「薇信」）。
3. 要识别软广告：看似分享实则引流，例如「有需要的同学私我」「评论区留联系方式」。
4. 校园场景重点：代写代考、出售答案、代课代签、校园贷、宿舍矛盾升级、校园欺凌。
5. 正常校园内容必须判 safe：表白、吐槽食堂、失物招领、二手交易、社团招新、考研自习、
   提问求助、情绪倾诉（无自伤倾向）。宁可放过，不要误杀。
6. 不确定时给 medium 并建议 review，由人工复核，不要轻易判 high。

【输出格式】只输出一个 JSON 对象，不要任何解释、不要 markdown 代码块：
{"risk_level":"safe","score":0,"categories":[],"reasons":["..."],"confidence":0.9,"suggested_action":"pass"}

score 为 0-100 的整数风险分；suggested_action 取 pass / mask / review / block；
reasons 用一句中文说明判定依据（不超过 40 字，最多 3 条）。"""


@dataclass
class LLMVerdict:
    risk_level: str = "safe"
    score: int = 0
    categories: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.0
    suggested_action: str = "pass"
    model: str = ""
    latency_ms: int = 0
    cached: bool = False
    raw: str = ""

    def as_dict(self) -> dict:
        return {
            "risk_level": self.risk_level, "score": self.score,
            "categories": self.categories, "reasons": self.reasons,
            "confidence": self.confidence, "suggested_action": self.suggested_action,
            "model": self.model, "latency_ms": self.latency_ms, "cached": self.cached,
        }


_cache: dict[str, tuple[float, LLMVerdict]] = {}
_cache_order: list[str] = []
_CACHE_MAX = 2000

_breaker = {"failures": 0, "open_until": 0.0, "last_error": ""}
_BREAKER_THRESHOLD = 3
_BREAKER_COOLDOWN = 300.0

_quota = {"day": "", "count": 0}


def _cache_key(text: str, model: str) -> str:
    return hashlib.sha256(f"{model}|{compact(text)}".encode("utf-8")).hexdigest()


def _cache_get(key: str, ttl: int) -> LLMVerdict | None:
    item = _cache.get(key)
    if not item:
        return None
    ts, verdict = item
    if ttl <= 0 or time.time() - ts > ttl:
        _cache.pop(key, None)
        return None
    cached = LLMVerdict(**{**verdict.__dict__, "cached": True})
    return cached


def _cache_put(key: str, verdict: LLMVerdict) -> None:
    if key not in _cache:
        _cache_order.append(key)
    _cache[key] = (time.time(), verdict)
    while len(_cache_order) > _CACHE_MAX:
        old = _cache_order.pop(0)
        _cache.pop(old, None)


def breaker_state() -> dict:
    return {
        "open": time.time() < _breaker["open_until"],
        "failures": _breaker["failures"],
        "last_error": _breaker["last_error"],
        "open_seconds_left": max(0, int(_breaker["open_until"] - time.time())),
    }


def reset_breaker() -> None:
    _breaker.update({"failures": 0, "open_until": 0.0, "last_error": ""})


def quota_state() -> dict:
    today = time.strftime("%Y-%m-%d")
    if _quota["day"] != today:
        _quota["day"] = today
        _quota["count"] = 0
    return dict(_quota)


def _quota_take(limit: int) -> bool:
    st = quota_state()
    if limit and st["count"] >= limit:
        return False
    _quota["count"] += 1
    return True


def cache_stats() -> dict:
    return {"cached": len(_cache), "breaker": breaker_state(), "quota": quota_state()}


def clear_cache() -> None:
    _cache.clear()
    _cache_order.clear()


def _extract_json(content: str) -> dict | None:
    if not content:
        return None
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _coerce(obj: dict, model: str, latency_ms: int, raw: str) -> LLMVerdict:
    v = LLMVerdict(model=model, latency_ms=latency_ms, raw=raw[:500])
    level = str(obj.get("risk_level") or "safe").lower()
    v.risk_level = level if level in ("safe", "low", "medium", "high", "critical") else "medium"
    try:
        v.score = max(0, min(100, int(float(obj.get("score", 0)))))
    except (TypeError, ValueError):
        v.score = 0
    cats = obj.get("categories")
    if isinstance(cats, list):
        v.categories = [str(c) for c in cats if str(c) in _CATEGORY_KEYS][:5]
    elif isinstance(cats, str) and cats in _CATEGORY_KEYS:
        v.categories = [cats]
    reasons = obj.get("reasons")
    if isinstance(reasons, list):
        v.reasons = [str(r)[:60] for r in reasons if str(r).strip()][:3]
    elif isinstance(reasons, str) and reasons.strip():
        v.reasons = [reasons.strip()[:60]]
    try:
        v.confidence = max(0.0, min(1.0, float(obj.get("confidence", 0.0))))
    except (TypeError, ValueError):
        v.confidence = 0.0
    act = str(obj.get("suggested_action") or "pass").lower()
    v.suggested_action = act if act in ("pass", "mask", "review", "block") else "pass"
    return v


def _build_user_prompt(title: str, content: str, scene: str, local_hint: str) -> str:
    parts = [f"【场景】{scene}"]
    if title:
        parts.append(f"【标题】{title}")
    parts.append(f"【正文】{content}")
    if local_hint:
        parts.append(f"【本地规则已发现的可疑点（供参考，不要盲从）】{local_hint}")
    parts.append("请按系统提示输出 JSON。")
    return "\n".join(parts)


async def review_text(title: str, content: str, cfg: AIConfig, *,
                      scene: str = "帖子", local_hint: str = "") -> LLMVerdict | None:
    """调用大模型做语义审查。失败/未配置/熔断/超配额一律返回 None（调用方降级）。"""
    if not cfg.llm_api_key or not cfg.llm_base_url or not cfg.llm_model:
        return None
    if cfg.llm_trigger == "off":
        return None
    if time.time() < _breaker["open_until"]:
        return None

    body_text = ((title or "") + "\n" + (content or ""))[: max(100, cfg.llm_max_len)]
    if not body_text.strip():
        return None

    key = _cache_key(body_text, cfg.llm_model)
    hit = _cache_get(key, cfg.llm_cache_ttl)
    if hit is not None:
        return hit
    if not _quota_take(cfg.llm_daily_limit):
        logger.warning("AI 审查：今日大模型调用已达上限 %s，本次跳过", cfg.llm_daily_limit)
        return None

    url = cfg.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(title, content, scene, local_hint)},
        ],
        "temperature": 0.1,
        "max_tokens": 400,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {cfg.llm_api_key}",
        "Content-Type": "application/json",
    }
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=cfg.llm_timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
        latency = int((time.monotonic() - started) * 1000)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        content_str = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        obj = _extract_json(content_str)
        if obj is None:
            raise RuntimeError(f"返回内容不是合法 JSON：{content_str[:160]}")
        verdict = _coerce(obj, cfg.llm_model, latency, content_str)
        _cache_put(key, verdict)
        _breaker["failures"] = 0
        logger.info("AI 审查 LLM 判定 level=%s score=%s cats=%s %dms",
                    verdict.risk_level, verdict.score, verdict.categories, latency)
        return verdict
    except Exception as exc:  # 网络/超时/解析异常统一降级
        _breaker["failures"] += 1
        _breaker["last_error"] = f"{type(exc).__name__}: {str(exc)[:150]}"
        if _breaker["failures"] >= _BREAKER_THRESHOLD:
            _breaker["open_until"] = time.time() + _BREAKER_COOLDOWN
            logger.warning("AI 审查大模型连续失败 %d 次，熔断 %d 秒",
                           _breaker["failures"], int(_BREAKER_COOLDOWN))
        logger.warning("AI 审查大模型调用失败，已降级为本地判定：%s", _breaker["last_error"])
        return None


async def ping(cfg: AIConfig) -> dict:
    """后台「测试连接」用：发一条最小请求验证 Key 与模型是否可用。"""
    if not cfg.llm_api_key:
        return {"ok": False, "msg": "未配置 API Key"}
    if not cfg.llm_base_url or not cfg.llm_model:
        return {"ok": False, "msg": "未配置接口地址或模型名"}
    url = cfg.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg.llm_model,
        "messages": [
            {"role": "system", "content": "你是内容安全审查员，只输出 JSON。"},
            {"role": "user", "content": '判断这句话是否违规：「加我微信vx123456日结兼职刷单」。只输出 {"risk_level":"high","score":90,"categories":["fraud"],"reasons":["刷单诈骗引流"],"confidence":0.95,"suggested_action":"block"}'},
        ],
        "temperature": 0,
        "max_tokens": 200,
        "stream": False,
    }
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=cfg.llm_timeout) as client:
            resp = await client.post(
                url, json=payload,
                headers={"Authorization": f"Bearer {cfg.llm_api_key}"},
            )
        latency = int((time.monotonic() - started) * 1000)
        if resp.status_code >= 400:
            return {"ok": False, "msg": f"HTTP {resp.status_code}：{resp.text[:200]}", "latency_ms": latency}
        content_str = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        obj = _extract_json(content_str)
        if obj is None:
            return {"ok": False, "msg": f"模型返回无法解析为 JSON：{content_str[:160]}", "latency_ms": latency}
        return {
            "ok": True, "msg": "连接成功，模型可用",
            "latency_ms": latency, "sample_verdict": _coerce(obj, cfg.llm_model, latency, content_str).as_dict(),
        }
    except Exception as exc:
        return {"ok": False, "msg": f"{type(exc).__name__}: {str(exc)[:200]}"}


async def warmup() -> None:
    """预留：必要时可在此做连接预热。"""
    await asyncio.sleep(0)
