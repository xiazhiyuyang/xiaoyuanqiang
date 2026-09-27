"""违规分类体系（校园墙社区规范）。

分类直接决定处置动作与对外提示文案，后台可按分类逐项调整策略。
"""
from __future__ import annotations

# 分类 -> 元信息
#   label     后台展示名
#   action    默认处置动作 pass/mask/review/block
#   severity  默认危险等级 1-5
#   legal     是否属于法定违法信息（《网络信息内容生态治理规定》第七条）
#   hint      拦截时给用户看的提示
CATEGORIES: dict[str, dict] = {
    "politics": {
        "label": "政治敏感", "action": "block", "severity": 5, "legal": True,
        "hint": "内容涉及政治敏感信息，不予发布。请自觉维护清朗网络空间。",
    },
    "terror": {
        "label": "暴恐极端", "action": "block", "severity": 5, "legal": True,
        "hint": "内容涉及暴力恐怖或极端主义信息，不予发布。",
    },
    "illegal": {
        "label": "违法犯罪", "action": "block", "severity": 5, "legal": True,
        "hint": "内容涉及枪支弹药、毒品、假证等违法交易，不予发布。",
    },
    "porn": {
        "label": "色情低俗", "action": "block", "severity": 5, "legal": True,
        "hint": "内容涉及色情低俗信息，不予发布。",
    },
    "minor": {
        "label": "涉未成年人", "action": "block", "severity": 5, "legal": True,
        "hint": "内容涉及未成年人不良信息，不予发布。",
    },
    "fraud": {
        "label": "诈骗赌博", "action": "block", "severity": 5, "legal": True,
        "hint": "内容涉嫌诈骗、赌博或非法金融活动，不予发布。",
    },
    "privacy": {
        "label": "隐私侵害", "action": "review", "severity": 4, "legal": False,
        "hint": "内容可能泄露他人隐私，请改用站内私信联系。",
    },
    "academic": {
        "label": "学术不端", "action": "block", "severity": 5, "legal": False,
        "hint": "代写代考、出售答案等学术不端信息，校园墙明令禁止。",
    },
    "violence": {
        "label": "暴力威胁", "action": "review", "severity": 4, "legal": False,
        "hint": "内容涉及人身威胁，需要人工确认。",
    },
    "self_harm": {
        "label": "轻生倾向", "action": "review", "severity": 4, "legal": False,
        "hint": "我们注意到你可能正处于困难时期，已转人工处理，请留意私信。",
    },
    "ad": {
        "label": "广告引流", "action": "review", "severity": 3, "legal": False,
        "hint": "内容疑似广告或站外引流，需人工确认后再展示。",
    },
    "abuse": {
        "label": "辱骂攻击", "action": "mask", "severity": 2, "legal": False,
        "hint": "内容含人身攻击用语，已做打码处理。",
    },
    "spam": {
        "label": "刷屏灌水", "action": "mask", "severity": 1, "legal": False,
        "hint": "内容疑似重复刷屏，已做处理。",
    },
    "other": {
        "label": "其他违规", "action": "review", "severity": 2, "legal": False,
        "hint": "内容需要人工复核。",
    },
}

# 默认策略表：category -> action，后台可覆盖
DEFAULT_CATEGORY_ACTIONS: dict[str, str] = {
    k: v["action"] for k, v in CATEGORIES.items()
}

RISK_LEVELS = ("safe", "low", "medium", "high", "critical")

RISK_LABELS = {
    "safe": "安全",
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "极高风险",
}


def label(category: str) -> str:
    return CATEGORIES.get(category, {}).get("label", category or "其他违规")


def default_action(category: str) -> str:
    return DEFAULT_CATEGORY_ACTIONS.get(category, "review")


def hint(category: str) -> str:
    return CATEGORIES.get(category, {}).get("hint", "内容未通过安全审查。")


def is_legal(category: str) -> bool:
    return bool(CATEGORIES.get(category, {}).get("legal"))


def catalog() -> list[dict]:
    return [
        {"key": k, "label": v["label"], "action": v["action"],
         "severity": v["severity"], "legal": v["legal"], "hint": v["hint"]}
        for k, v in CATEGORIES.items()
    ]
