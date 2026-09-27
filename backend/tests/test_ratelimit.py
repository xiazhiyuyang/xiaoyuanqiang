"""限流测试。

conftest 里把 REDIS_URL 置空，因此这里测的是**进程内降级路径**——
也就是 Redis 挂掉时真正生效的那条代码路径，反而更需要被测试覆盖。

关键行为：
1. 未超限放行，超限抛 429 且带 Retry-After；
2. 不同客户端互不影响；
3. X-Forwarded-For 取最右一段（最左可被伪造，用它限流等于没限流）；
4. 窗口滑动后恢复可用。
"""
from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import ratelimit
from app.core.ratelimit import _client_key, rate_limit


class _FakeHeaders(dict):
    def get(self, key, default=None):  # 兼容大小写不敏感的取法
        return super().get(key, super().get(key.lower(), default))


def _request(ip: str = "1.2.3.4", forwarded: str | None = None):
    headers = _FakeHeaders()
    if forwarded is not None:
        headers["x-forwarded-for"] = forwarded
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=ip))


@pytest.fixture(autouse=True)
def _reset_buckets():
    """每个用例都从干净的计数状态开始，避免用例间互相污染。"""
    ratelimit._buckets.clear()
    ratelimit._last_prune = 0.0
    yield
    ratelimit._buckets.clear()


@pytest.mark.asyncio
async def test_allows_up_to_limit_then_blocks():
    dep = rate_limit("test-scope", 3, 60)
    req = _request()
    for _ in range(3):
        await dep(req)          # 不应抛异常
    with pytest.raises(HTTPException) as exc:
        await dep(req)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers
    assert int(exc.value.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_different_clients_are_independent():
    dep = rate_limit("test-scope", 1, 60)
    await dep(_request(ip="1.1.1.1"))
    await dep(_request(ip="2.2.2.2"))   # 另一个 IP 仍可通行
    with pytest.raises(HTTPException):
        await dep(_request(ip="1.1.1.1"))


@pytest.mark.asyncio
async def test_different_scopes_are_independent():
    req = _request()
    await rate_limit("login", 1, 60)(req)
    await rate_limit("upload", 1, 60)(req)   # 换 scope 不受 login 计数影响


def test_client_key_prefers_rightmost_forwarded_entry():
    """最右一段由最近一跳可信代理写入；最左一段客户端可任意伪造。"""
    req = _request(ip="10.0.0.1", forwarded="6.6.6.6, 7.7.7.7, 8.8.8.8")
    assert _client_key(req) == "8.8.8.8"


def test_client_key_falls_back_to_direct_ip():
    assert _client_key(_request(ip="9.9.9.9")) == "9.9.9.9"


def test_client_key_handles_empty_and_whitespace_forwarded():
    assert _client_key(_request(ip="9.9.9.9", forwarded="")) == "9.9.9.9"
    assert _client_key(_request(ip="9.9.9.9", forwarded=" , , ")) == "9.9.9.9"


@pytest.mark.asyncio
async def test_spoofed_leftmost_forwarded_cannot_bypass_limit():
    """每次伪造不同的最左段，也必须被同一个限流桶拦住。"""
    dep = rate_limit("test-scope", 2, 60)
    await dep(_request(forwarded="1.0.0.1, 8.8.8.8"))
    await dep(_request(forwarded="1.0.0.2, 8.8.8.8"))
    with pytest.raises(HTTPException):
        await dep(_request(forwarded="1.0.0.3, 8.8.8.8"))


@pytest.mark.asyncio
async def test_window_slides_and_allows_again():
    dep = rate_limit("test-scope", 1, 1)
    req = _request()
    await dep(req)
    with pytest.raises(HTTPException):
        await dep(req)
    time.sleep(1.1)
    await dep(req)              # 窗口滑过后恢复可用


def test_prune_removes_expired_and_empty_buckets():
    """兜底清理按 _MAX_WINDOW(3600s) 回收，而不是按各 scope 自己的窗口。

    这是有意的设计：短窗口的桶如果按窗口回收，就需要额外的定时器；
    统一用 1 小时兜底，保证「即使某个 key 再也没被访问过，桶也不会永久驻留」。
    """
    now = time.monotonic()
    ratelimit._buckets["stale:1.1.1.1"].append(now - ratelimit._MAX_WINDOW - 10)
    ratelimit._buckets["fresh:2.2.2.2"].append(now)
    ratelimit._last_prune = 0.0          # 强制本次真正执行清理
    ratelimit._prune(now)
    assert "stale:1.1.1.1" not in ratelimit._buckets   # 过期且桶已空 -> 回收
    assert "fresh:2.2.2.2" in ratelimit._buckets       # 未过期 -> 保留


def test_prune_keeps_bucket_with_mixed_entries():
    """桶里只要还有未过期条目，整个桶就不能被回收。"""
    now = time.monotonic()
    bucket = ratelimit._buckets["mixed:3.3.3.3"]
    bucket.append(now - ratelimit._MAX_WINDOW - 10)
    bucket.append(now)
    ratelimit._last_prune = 0.0
    ratelimit._prune(now)
    assert "mixed:3.3.3.3" in ratelimit._buckets
    assert len(bucket) == 1               # 只丢过期那一条


def test_prune_is_throttled():
    """清理有节流间隔，避免每个请求都遍历全部桶。"""
    now = time.monotonic()
    ratelimit._buckets["stale:9.9.9.9"].append(now - ratelimit._MAX_WINDOW - 10)
    ratelimit._last_prune = now           # 距上次清理不足 _PRUNE_INTERVAL
    ratelimit._prune(now)
    assert "stale:9.9.9.9" in ratelimit._buckets
