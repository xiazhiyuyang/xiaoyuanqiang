"""文本深度归一化：对抗「谐音、拆字、跳字、全角、繁体、零宽字符」等绕过手法。

与 app/core/moderation.py 的 _normalize 的分工：
- _normalize 服务于 DFA 精确匹配，必须严格保持字符索引映射（用于打码定位）；
- 本模块的 deep_normalize 服务于「规则正则 / 相似度 / 特征打分」，
  允许做更激进的改写（谐音归一、重复字折叠），不保证索引可用。
"""
from __future__ import annotations

import re

# 全角 -> 半角 区间
_FW_START, _FW_END, _FW_OFFSET = 0xFF01, 0xFF5E, 0xFEE0

# 零宽 / 不可见字符
_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u180e\u00ad\u2028\u2029]")

# 干扰符号：空白与常见标点/表情（保留字母、数字与汉字）
_NOISE = re.compile(
    r"[\s.,!?;:~·\-—_/\\|@#$%^&*()\[\]{}<>\"'`。，！？；：～…、“”‘’（）【】《》"
    r"✦✨⭐♥♡💢❓💰🔍💬❤️🔥😂🙏😅😭🥰😍🤔😊😉😎🤣😳😏🙄😴🤤😱🤯🥳]+"
)

# 谐音 / 形近归一表。
# 刻意保持极小：只收录在校园场景里**几乎只用于规避过滤**的字符，
# 避免把正常表达改写成违规词（例如 沙/煞 -> 傻 会把「长沙」「沙发」变成「长傻」）。
# 更复杂的谐音绕过（威信、v信、w信…）交给 rules.py 的显式正则处理，精确且可控。
_HOMOPHONE = {
    "薇": "微",   # 薇信 / 加薇
    "溦": "微",
    "嶶": "微",
}

# 重复字符折叠阈值：同一字符连续出现 >=3 次折叠为 1 次（"傻傻傻逼" -> "傻逼" 的前置处理）
_REPEAT = re.compile(r"(.)\1{2,}")


def fullwidth_to_halfwidth(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            out.append(" ")
        elif _FW_START <= code <= _FW_END:
            out.append(chr(code - _FW_OFFSET))
        else:
            out.append(ch)
    return "".join(out)


def deep_normalize(text: str, *, fold_repeat: bool = True) -> str:
    """激进归一化：用于规则匹配与相似度计算。

    步骤：全角转半角 -> 去零宽 -> 去干扰符号 -> 谐音归一 -> 小写
          -> 重复字符折叠。
    注意：会改变长度，不能用于打码定位。
    """
    if not text:
        return ""
    text = fullwidth_to_halfwidth(text)
    text = _ZERO_WIDTH.sub("", text)
    text = _NOISE.sub("", text)
    text = text.lower()
    if _HOMOPHONE:
        text = "".join(_HOMOPHONE.get(ch, ch) for ch in text)
    if fold_repeat:
        text = _REPEAT.sub(r"\1", text)
        text = _REPEAT.sub(r"\1", text)  # 再折一次，处理 AABB 型
    return text


def compact(text: str) -> str:
    """仅去噪、不改写语义的紧凑形式：用于「跳字绕过」检测（如「加 微 信」）。"""
    if not text:
        return ""
    text = fullwidth_to_halfwidth(text)
    text = _ZERO_WIDTH.sub("", text)
    return _NOISE.sub("", text).lower()


def collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def char_bigrams(text: str) -> set[str]:
    """字符二元组集合，用于轻量相似度计算（无需依赖分词/向量）。"""
    s = compact(text)
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def bigram_similarity(a: str, b: str) -> float:
    """Jaccard 相似度，0~1。"""
    ga, gb = char_bigrams(a), char_bigrams(b)
    if not ga or not gb:
        return 0.0
    inter = len(ga & gb)
    union = len(ga | gb)
    return inter / union if union else 0.0
