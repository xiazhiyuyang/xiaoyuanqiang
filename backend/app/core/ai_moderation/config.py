"""AI 审查配置：默认值、读写、校验。

配置整体以单键 `ai_review_config`（JSON 字符串）持久化在 site_settings 表，
避免为几十个开关各加一行；API Key 属于机密，只存库、绝不出现在公开配置接口。
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from .categories import CATEGORIES, DEFAULT_CATEGORY_ACTIONS

logger = logging.getLogger("campus-wall")

SETTING_KEY = "ai_review_config"

# 大模型服务商预设（OpenAI 兼容协议）
LLM_PRESETS: dict[str, dict] = {
    "zhipu": {
        "label": "智谱 GLM-4-Flash（官方免费）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    "deepseek": {
        "label": "DeepSeek（按量付费，便宜）",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "qwen": {
        "label": "阿里通义千问（DashScope 兼容模式）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo",
    },
    "siliconflow": {
        "label": "硅基流动 SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
    },
    "moonshot": {
        "label": "月之暗面 Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "custom": {
        "label": "自定义 OpenAI 兼容接口",
        "base_url": "",
        "model": "",
    },
}

IMAGE_PRESETS = {
    "none": "关闭图片审查",
    "sightengine": "Sightengine（nudity-2.1，有免费额度）",
    "generic": "自定义图片审核 HTTP 接口",
    "local": "本地轻量启发式（肤色占比，仅提示不拦截）",
}

# LLM 触发时机
LLM_TRIGGER_MODES = {
    "off": "不调用",
    "suspect": "仅对本地判定可疑的内容调用（省钱，推荐）",
    "sampled": "按比例抽样调用",
    "always": "全部内容都调用（最准，最贵）",
}


@dataclass
class AIConfig:
    """AI 审查配置。"""
    enabled: bool = True
    dry_run: bool = False                 # 观察模式：只记录不处置，用于上线前试跑
    local_enabled: bool = True            # 词库 + 规则 + 特征打分

    llm_trigger: str = "suspect"          # off / suspect / sampled / always
    llm_provider: str = "zhipu"
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    llm_api_key: str = ""
    llm_model: str = "glm-4-flash"
    llm_timeout: float = 12.0
    llm_sample_rate: int = 100            # sampled 模式下的抽样比例 %
    llm_min_score: int = 25               # suspect 模式下的送审门槛
    llm_max_len: int = 1500               # 超长截断，控制 token 成本
    llm_cache_ttl: int = 3600             # 相同内容结果缓存秒数
    llm_daily_limit: int = 2000           # 每日调用上限，防费用失控

    image_enabled: bool = False
    image_provider: str = "none"          # none / sightengine / generic / local
    image_api_url: str = ""
    image_api_key: str = ""
    image_api_user: str = ""
    image_api_secret: str = ""
    image_timeout: float = 8.0
    image_block_score: int = 85
    image_review_score: int = 60

    block_score: int = 75                 # >= 该分 -> 拦截
    review_score: int = 40                # >= 该分 -> 人工复核
    mask_score: int = 20                  # >= 该分 -> 打码
    category_actions: dict = field(default_factory=lambda: dict(DEFAULT_CATEGORY_ACTIONS))

    scope_post: bool = True
    scope_comment: bool = True
    scope_message: bool = True
    scope_profile: bool = True

    auto_ban_threshold: int = 0           # 7 天内被拦截次数达到该值自动封禁；0=关闭
    notify_author: bool = True            # 审查结果通知作者
    exempt_staff: bool = True             # 管理员/审查员豁免自动拦截（仅记录）

    lexicon_whitelist: list = field(default_factory=list)  # 白名单词
    blocked_domains: list = field(default_factory=list)    # 站外域名黑名单

    def action_for(self, category: str) -> str:
        act = (self.category_actions or {}).get(category)
        if act in ("pass", "mask", "review", "block"):
            return act
        return DEFAULT_CATEGORY_ACTIONS.get(category, "review")

    def scope_on(self, target_type: str) -> bool:
        return bool({
            "post": self.scope_post,
            "comment": self.scope_comment,
            "message": self.scope_message,
            "profile": self.scope_profile,
        }.get(target_type, True))

    def as_dict(self, *, mask_secret: bool = False) -> dict:
        data = asdict(self)
        if mask_secret:
            for key in ("llm_api_key", "image_api_key", "image_api_secret"):
                val = data.get(key) or ""
                data[key] = ("*" * 8 + val[-4:]) if len(val) > 4 else ("*" * len(val))
            data["llm_api_key_set"] = bool(self.llm_api_key)
            data["image_api_key_set"] = bool(self.image_api_key or self.image_api_secret)
        data["llm_presets"] = LLM_PRESETS
        data["image_presets"] = IMAGE_PRESETS
        data["llm_trigger_modes"] = LLM_TRIGGER_MODES
        data["category_catalog"] = [
            {"key": k, "label": v["label"], "severity": v["severity"],
             "legal": v["legal"], "hint": v["hint"]}
            for k, v in CATEGORIES.items()
        ]
        return data


_BOOL_KEYS = (
    "enabled", "dry_run", "local_enabled", "image_enabled",
    "scope_post", "scope_comment", "scope_message", "scope_profile",
    "notify_author", "exempt_staff",
)
_INT_KEYS = {
    "llm_sample_rate": (0, 100), "llm_min_score": (0, 100), "llm_max_len": (100, 8000),
    "llm_cache_ttl": (0, 86400), "llm_daily_limit": (0, 1000000),
    "block_score": (0, 100), "review_score": (0, 100), "mask_score": (0, 100),
    "image_block_score": (0, 100), "image_review_score": (0, 100),
    "auto_ban_threshold": (0, 1000),
}
_STR_KEYS = {
    "llm_trigger": {"off", "suspect", "sampled", "always"},
    "llm_provider": set(LLM_PRESETS.keys()),
    "image_provider": set(IMAGE_PRESETS.keys()),
}


def default_config() -> AIConfig:
    return AIConfig()


def parse_config(raw) -> AIConfig:
    """把数据库里的 JSON 字符串解析成配置对象；任何异常都回退默认值。"""
    cfg = AIConfig()
    if not raw:
        return cfg
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        logger.warning("AI 审查配置解析失败，使用默认值")
        return cfg
    if not isinstance(obj, dict):
        return cfg

    for key in _BOOL_KEYS:
        if key in obj:
            val = obj[key]
            setattr(cfg, key, bool(val) if isinstance(val, bool) else str(val) == "1")
    for key, (lo, hi) in _INT_KEYS.items():
        if key in obj:
            try:
                setattr(cfg, key, max(lo, min(hi, int(float(obj[key])))))
            except (TypeError, ValueError):
                pass
    for key, allowed in _STR_KEYS.items():
        if obj.get(key) in allowed:
            setattr(cfg, key, obj[key])
    for key in ("llm_base_url", "llm_model", "image_api_url", "image_api_key",
                "image_api_user", "image_api_secret", "llm_api_key"):
        if key in obj and isinstance(obj[key], str):
            setattr(cfg, key, obj[key].strip())
    if "llm_timeout" in obj:
        try:
            cfg.llm_timeout = max(2.0, min(60.0, float(obj["llm_timeout"])))
        except (TypeError, ValueError):
            pass
    if "image_timeout" in obj:
        try:
            cfg.image_timeout = max(2.0, min(30.0, float(obj["image_timeout"])))
        except (TypeError, ValueError):
            pass

    actions = obj.get("category_actions")
    if isinstance(actions, dict):
        clean = dict(DEFAULT_CATEGORY_ACTIONS)
        for k, v in actions.items():
            if k in CATEGORIES and v in ("pass", "mask", "review", "block"):
                clean[k] = v
        cfg.category_actions = clean

    for key in ("lexicon_whitelist", "blocked_domains"):
        val = obj.get(key)
        if isinstance(val, list):
            setattr(cfg, key, [str(x).strip() for x in val if str(x).strip()][:20000])
    return cfg


def apply_provider_preset(cfg: AIConfig) -> AIConfig:
    """当 base_url/model 为空时按服务商预设补齐。"""
    preset = LLM_PRESETS.get(cfg.llm_provider)
    if preset:
        if not cfg.llm_base_url:
            cfg.llm_base_url = preset["base_url"]
        if not cfg.llm_model:
            cfg.llm_model = preset["model"]
    return cfg


def merge_updates(current: AIConfig, payload: dict) -> AIConfig:
    """把后台提交的部分字段合并进当前配置（未提交的字段保持不变）。

    API Key 特殊处理：提交空串表示「不修改」，提交 "__CLEAR__" 表示清空。
    """
    base = asdict(current)
    for key, value in (payload or {}).items():
        if key not in base:
            continue
        if key in ("llm_api_key", "image_api_key", "image_api_secret"):
            if value == "__CLEAR__":
                base[key] = ""
            elif isinstance(value, str):
                value = value.strip()
                if value:
                    base[key] = value
            continue
        base[key] = value
    return parse_config(base)
