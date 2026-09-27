"""AI 智能审查引擎。

对外只需关心两个函数：

    outcome = await review(db, target_type="post", target_id=pid, user_id=uid,
                           title=t, content=c, images=urls)
    if outcome.action == "block":  ...
    elif outcome.action == "review": ...   # 落 pending，进人工队列
    else: ...                              # pass / mask

后台配置读写：

    cfg = await get_config()
    await save_config(db, payload)
"""
from .config import (
    AIConfig, IMAGE_PRESETS, LLM_PRESETS, SETTING_KEY, default_config,
    parse_config,
)
from .decision import ACTION_LABELS, Verdict
from .llm import cache_stats as llm_cache_stats
from .llm import clear_cache as clear_llm_cache
from .llm import ping as llm_ping
from .llm import reset_breaker
from .pipeline import (
    ReviewOutcome, attach_target, evaluate, get_config, invalidate_config, review,
    save_config, test_review, user_violation_stats,
)
from .rules import rule_catalog

__all__ = [
    "AIConfig", "Verdict", "ReviewOutcome", "ACTION_LABELS",
    "get_config", "save_config", "invalidate_config", "parse_config",
    "default_config", "SETTING_KEY", "LLM_PRESETS", "IMAGE_PRESETS",
    "review", "evaluate", "test_review", "rule_catalog", "attach_target",
    "user_violation_stats", "llm_ping", "llm_cache_stats", "clear_llm_cache",
    "reset_breaker",
]
