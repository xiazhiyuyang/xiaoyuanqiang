"""特征打分层：把「词库命中 + 规则命中 + 文本统计特征 + 违规样例相似度」
融合成一个 0-100 的风险分，并保留可解释的加分项。

设计原则：
- 分数量级只用于「是否拦截 / 是否送人工 / 是否送大模型」的门槛判断，
  真正的分类与最终动作由 decision.py 依据分类策略表决定；
- 每个加分项都带 name/detail，后台能看到「为什么被判高风险」。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalize import bigram_similarity, compact

# 违规样例库：用于识别「换了个说法」的同类内容（字符二元组相似度）
EXEMPLARS: tuple[tuple[str, str, int], ...] = (
    # (样例文本, 分类, 权重)
    ("加我微信拉你进群一起赚钱轻松日入几百", "ad", 3),
    ("招校园代理一件代发无门槛需要联系我", "ad", 3),
    ("有偿代写论文代做课程设计包过不过退款", "academic", 4),
    ("出售本次考试答案有意者私聊价格好谈", "academic", 4),
    ("兼职刷单垫付返利日结轻松赚钱", "fraud", 5),
    ("无抵押秒下款学生也能借当天到账", "fraud", 5),
    ("新平台返水高倍投稳赢带你上岸", "fraud", 5),
    ("上门服务全套特殊服务可约", "porn", 5),
    ("看片资源福利视频加群免费领取", "porn", 5),
    ("你就是个废物怎么不去死", "abuse", 3),
    ("我知道你住哪个宿舍给我等着", "violence", 4),
    ("不想活了感觉活着没有任何意义", "self_harm", 4),
)

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]"
)
_DIGIT_LETTER_RUN = re.compile(r"[a-z]{1,6}\d{3,}|\d{3,}[a-z]{1,6}", re.I)
_URL_RE = re.compile(r"(?:https?://|www\.)[a-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]{4,}", re.I)
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_BANG_RE = re.compile(r"[!！?？]{3,}")


@dataclass
class Signal:
    name: str
    weight: int
    detail: str = ""


@dataclass
class FeatureScore:
    score: int = 0
    signals: list[Signal] = field(default_factory=list)
    exemplar_hits: list[dict] = field(default_factory=list)

    def add(self, name: str, weight: int, detail: str = "") -> None:
        if weight <= 0:
            return
        self.signals.append(Signal(name=name, weight=weight, detail=detail))
        self.score += weight

    def as_dict(self) -> dict:
        return {
            "score": min(100, self.score),
            "signals": [{"name": s.name, "weight": s.weight, "detail": s.detail} for s in self.signals],
            "exemplar_hits": self.exemplar_hits,
        }


def _lexicon_signal(fs: FeatureScore, hits: list) -> None:
    """词库命中：按最高等级给基础分，命中数量做递减加权，避免堆词爆分。"""
    if not hits:
        return
    severities = [int(getattr(h, "severity", 3) or 3) for h in hits]
    max_sev = max(severities)
    base = {1: 8, 2: 14, 3: 22, 4: 32, 5: 42}.get(max_sev, 20)
    extra = min(18, max(0, len(hits) - 1) * 4)
    words = "、".join(dict.fromkeys([str(getattr(h, "word", h)) for h in hits]))[:60]
    fs.add("敏感词库", base + extra, f"命中 {len(hits)} 处（最高等级 {max_sev}）：{words}")


def _rule_signal(fs: FeatureScore, hits: list) -> None:
    """规则命中：最强规则全额计分，其余规则按 35% 累加，防止多项叠加爆分。"""
    if not hits:
        return
    weights = sorted((int(getattr(h, "weight", 20) or 20) for h in hits), reverse=True)
    total = weights[0] + int(sum(weights[1:]) * 0.35)
    names = "、".join(dict.fromkeys([str(getattr(h, "name", "")) for h in hits]))[:60]
    fs.add("规则命中", min(80, total), f"{len(hits)} 条规则：{names}")


def _statistical_signals(fs: FeatureScore, text: str) -> None:
    if not text:
        return
    length = max(1, len(text))

    # 联系方式密度：广告/引流最稳定的信号
    contacts = (
        len(_PHONE_RE.findall(text)) + len(_URL_RE.findall(text))
        + len(_DIGIT_LETTER_RUN.findall(text))
    )
    if contacts:
        fs.add("联系方式密度", min(30, 10 + contacts * 6),
               f"检出 {contacts} 处手机号/网址/疑似账号")

    # 符号与表情灌水
    emoji_n = len(_EMOJI_RE.findall(text))
    bang = len(_BANG_RE.findall(text))
    if emoji_n + bang >= 6:
        fs.add("符号灌水", min(12, (emoji_n + bang) // 2), f"表情 {emoji_n} 个、连续感叹/问号 {bang} 处")

    # 非中文占比过高且含大量数字字母：典型账号/链接堆砌
    latin = sum(1 for ch in text if ch.isascii() and ch.isalnum())
    if latin / length > 0.5 and length > 12:
        fs.add("字符构成异常", 10, f"ASCII 字符占比 {latin * 100 // length}%")

    # 极短文本 + 联系方式：典型「加vx」式一句话广告
    if length <= 20 and contacts:
        fs.add("短文本引流", 12, "极短文本中直接给出联系方式")


def _exemplar_signal(fs: FeatureScore, text: str) -> None:
    """与违规样例的字符二元组相似度：捕捉换了说法的同类内容。"""
    if not text or len(text) < 6:
        return
    best: tuple[float, str, str, int] | None = None
    for sample, category, weight in EXEMPLARS:
        sim = bigram_similarity(text, sample)
        if best is None or sim > best[0]:
            best = (sim, sample, category, weight)
    if not best:
        return
    sim, sample, category, weight = best
    if sim >= 0.34:
        add = int(min(35, sim * 55 * (weight / 3)))
        fs.exemplar_hits.append({
            "similarity": round(sim, 3), "category": category, "sample": sample,
        })
        fs.add("违规样例相似", max(8, add),
               f"与「{sample[:18]}…」相似度 {sim:.0%}")


def score_text(text: str, *, lexicon_hits: list | None = None,
               rule_hits: list | None = None) -> FeatureScore:
    """计算综合风险分。"""
    fs = FeatureScore()
    _lexicon_signal(fs, lexicon_hits or [])
    _rule_signal(fs, rule_hits or [])
    _statistical_signals(fs, text or "")
    _exemplar_signal(fs, text or "")
    fs.score = min(100, fs.score)
    return fs


def is_near_duplicate(text: str, others: list[str], threshold: float = 0.9) -> bool:
    """判断是否与最近发布内容高度重复（用于刷屏判定）。"""
    if not text or not others:
        return False
    c = compact(text)
    if len(c) < 6:
        return False
    return any(bigram_similarity(c, o) >= threshold for o in others)
