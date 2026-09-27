"""敏感词引擎测试。

直接测 `_DFAFilter`，不碰数据库——词库加载逻辑很简单，
真正容易改错的是归一化与长词优先匹配。
"""
from __future__ import annotations

import pytest

from app.core.moderation import ModerationResult, _DFAFilter, _normalize


@pytest.fixture
def dfa():
    f = _DFAFilter()
    f.build([
        ("傻逼", "mask"),
        ("加微信", "block"),
        ("加VX", "block"),
        ("代写论文", "block"),
        ("论文", "mask"),        # 短词，用于验证「长词优先」
    ])
    return f


def test_clean_text_untouched(dfa):
    assert dfa.scan("今天食堂的糖醋排骨不错") == []


def test_mask_word_detected(dfa):
    hits = dfa.scan("你个傻逼")
    assert len(hits) == 1
    start, end, word, action = hits[0]
    assert word == "傻逼"
    assert action == "mask"


def test_longest_match_wins(dfa):
    """「代写论文」必须整词命中 block，而不是先命中短词「论文」的 mask。"""
    hits = dfa.scan("承接代写论文业务")
    assert len(hits) == 1
    assert hits[0][2] == "代写论文"
    assert hits[0][3] == "block"


def test_fullwidth_normalization(dfa):
    """全角字母要能被识别：加ＶＸ == 加VX。"""
    hits = dfa.scan("加ＶＸ联系")
    assert len(hits) == 1
    assert hits[0][3] == "block"


def test_separator_evasion(dfa):
    """插入空格/标点的拆字绕过要能被识破：「加 微 信」。"""
    hits = dfa.scan("加 微 信")
    assert len(hits) == 1
    assert hits[0][3] == "block"


def test_normalize_returns_index_map():
    """归一化必须保留原文索引，否则 mask 会替换错位置。"""
    norm, idx_map = _normalize("加 微 信")
    assert norm == "加微信"
    assert idx_map == [0, 2, 4]


def test_normalize_fullwidth_to_halfwidth():
    norm, _ = _normalize("ＡＢＣ１２３")
    assert norm == "abc123"


def test_mask_replaces_correct_span():
    """端到端验证替换位置：只把命中字符变成 *，长度不变。"""
    f = _DFAFilter()
    f.build([("傻逼", "mask")])
    text = "你这个傻逼啊"
    hits = f.scan(text)
    chars = list(text)
    for start, end, _word, _action in hits:
        for k in range(start, end):
            chars[k] = "*"
    result = "".join(chars)
    assert result == "你这个**啊"
    assert len(result) == len(text)


def test_empty_filter_matches_nothing():
    f = _DFAFilter()
    f.build([])
    assert f.scan("任意内容") == []
    assert f.ready is True


def test_moderation_result_defaults():
    r = ModerationResult(cleaned="abc")
    assert r.hits == []
    assert r.blocked is False
    assert r.blocked_words == []
