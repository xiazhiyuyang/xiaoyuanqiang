"""轻量进程内滑动窗口限流（无外部依赖）。

- 按「功能:客户端标识」分桶，线程安全；
- 超限返回 429，带 Retry-After；
- 单机部署足够；多实例部署需换成 Redis 等共享存储。
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_buckets: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()
# 兜底清理：即使某个 key 再也没被访问过，也要保证桶不会无限增长
_MAX_WINDOW = 3600.0
_PRUNE_INTERVAL = 300.0
_last_prune = 0.0


def _prune(now: float) -> None:
    """定期丢弃过期条目与空桶（调用方必须已持有 _lock）。"""
    global _last_prune
    if now - _last_prune < _PRUNE_INTERVAL:
        return
    _last_prune = now
    for key in list(_buckets.keys()):
        bucket = _buckets[key]
        while bucket and now - bucket[0] > _MAX_WINDOW:
            bucket.popleft()
        if not bucket:
            del _buckets[key]


def _client_key(request: Request) -> str:
    # 反向代理会把直连来源追加到 X-Forwarded-For 末尾。
    # 最左一段可被客户端任意伪造（每次换值即可绕过限流），
    # 因此取最右一段（由最近一跳可信代理写入）；无代理时回退到直连 IP。
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        chain = [p.strip() for p in fwd.split(",") if p.strip()]
        if chain:
            return chain[-1]
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int):
    """生成限流依赖：同一 scope + 客户端在 window 内最多 limit 次。"""
    async def _dep(request: Request):
        key = f"{scope}:{_client_key(request)}"
        now = time.monotonic()
        with _lock:
            _prune(now)
            bucket = _buckets[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                retry = int(window_seconds - (now - bucket[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"操作过于频繁，请 {retry} 秒后再试",
                    headers={"Retry-After": str(retry)},
                )
            bucket.append(now)
    return _dep
