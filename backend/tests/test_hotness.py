"""热度分测试。

锁定三件事：
1. 时间衰减真实存在（老帖分数必须低于同互动量的新帖）——这是本次改造的核心目的；
2. 权重排序符合设计（评论 > 点赞 > 浏览）；
3. 边界情况不炸（除零、naive datetime、负数）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.hotness import GRAVITY, W_COMMENT, W_LIKE, W_VIEW, compute_score


@pytest.fixture
def now():
    return datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


def test_zero_interaction_scores_zero(now):
    """没有任何互动的新帖分数为 0，靠 created_at 兜底排序，不应出现异常高分。"""
    assert compute_score(0, 0, 0, now, now=now) == 0.0


def test_fresh_post_beats_old_post_with_same_stats(now):
    """同互动量下，新帖分数必须显著高于老帖。

    改造前 `ORDER BY like_count DESC` 会让一年前的高赞帖永久霸榜，
    这条断言就是防止有人把衰减改回去。
    """
    fresh = compute_score(10, 5, 100, now - timedelta(hours=1), now=now)
    old = compute_score(10, 5, 100, now - timedelta(days=30), now=now)
    assert fresh > old
    assert fresh / old > 10   # 30 天 vs 1 小时，差距应该是数量级的


def test_score_decays_monotonically(now):
    """观测时间不断后移 => 帖子越来越老 => 分数必须单调下降。"""
    created = now - timedelta(days=3)
    scores = [
        compute_score(20, 10, 200, created, now=now + timedelta(hours=h))
        for h in range(0, 48)
    ]
    assert scores == sorted(scores, reverse=True)


def test_weight_ordering(now):
    """同等数量下，评论对热度的贡献应大于点赞，点赞大于浏览。"""
    base = compute_score(0, 0, 0, now, now=now)
    one_like = compute_score(1, 0, 0, now, now=now)
    one_comment = compute_score(0, 1, 0, now, now=now)
    one_view = compute_score(0, 0, 1, now, now=now)
    assert base == 0.0
    assert one_comment > one_like > one_view > 0
    assert W_COMMENT > W_LIKE > W_VIEW


def test_naive_datetime_is_treated_as_utc(now):
    """SQLite 取回的 datetime 常是 naive，必须按 UTC 处理而不是崩掉或算出负龄。"""
    naive_created = (now - timedelta(hours=2)).replace(tzinfo=None)
    naive_now = now.replace(tzinfo=None)
    aware = compute_score(5, 2, 10, now - timedelta(hours=2), now=now)
    naive = compute_score(5, 2, 10, naive_created, now=naive_now)
    assert naive == pytest.approx(aware, rel=1e-6)


def test_future_created_at_does_not_explode(now):
    """时钟漂移导致 created_at 在未来时，年龄按 0 处理，分数有限且确定。"""
    score = compute_score(10, 0, 0, now + timedelta(days=1), now=now)
    expected = 10 * W_LIKE / (2.0 ** GRAVITY)
    assert score == pytest.approx(expected, rel=1e-6)


def test_none_created_at_falls_back_to_now(now):
    assert compute_score(4, 0, 0, None, now=now) == pytest.approx(
        compute_score(4, 0, 0, now, now=now), rel=1e-9
    )


def test_score_is_rounded_to_six_decimals(now):
    score = compute_score(7, 3, 41, now - timedelta(hours=5), now=now)
    assert round(score, 6) == score
