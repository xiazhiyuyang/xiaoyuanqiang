"""WebSocket 连接管理器（进程内）。

当前部署为 uvicorn 单 worker，进程内字典即可覆盖全部在线连接。
若将来改成多 worker / 多实例，需要在这里加一层 Redis Pub/Sub 中继：
发送方 publish 到频道，各 worker 订阅后投递给本地连接。

设计要点：
- connect / disconnect 是**同步方法**。asyncio 单线程下，不含 await 的字典
  操作天然原子，加锁没有收益；更重要的是，连接清理通常发生在 `finally` 中，
  而 `finally` 里的 `await` 可能被再次取消（客户端断连时协程正处于 cancelling
  状态），导致清理逻辑执行不到 —— 这正是本项目踩过的连接泄漏坑。
  同步方法不存在这个问题。
- 所有 send 都吞掉异常并顺手摘除坏连接：推送失败绝不能影响主业务事务。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("campus-wall")


class ConnectionManager:
    def __init__(self) -> None:
        # user_id -> 该用户的多个连接（多端/多标签页同时在线）
        self._conns: dict[int, set[WebSocket]] = {}

    def connect(self, user_id: int, ws: WebSocket) -> None:
        self._conns.setdefault(user_id, set()).add(ws)
        logger.info("WS 连接建立 user=%s 在线用户=%d 连接数=%d",
                    user_id, self.online_users, self.total_connections)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        bucket = self._conns.get(user_id)
        if bucket is not None:
            bucket.discard(ws)
            if not bucket:
                self._conns.pop(user_id, None)
        logger.info("WS 连接断开 user=%s 在线用户=%d 连接数=%d",
                    user_id, self.online_users, self.total_connections)

    def drop(self, ws: WebSocket) -> None:
        """从所有用户下摘除某个连接（发送失败时用）。"""
        for bucket in self._conns.values():
            bucket.discard(ws)
        for uid in [u for u, b in self._conns.items() if not b]:
            self._conns.pop(uid, None)

    @property
    def total_connections(self) -> int:
        return sum(len(v) for v in self._conns.values())

    @property
    def online_users(self) -> int:
        return len(self._conns)

    def is_online(self, user_id: int) -> bool:
        return bool(self._conns.get(user_id))

    def connections_of(self, user_id: int) -> list[WebSocket]:
        return list(self._conns.get(user_id, ()))

    async def send_to_user(self, user_id: int, payload: dict[str, Any]) -> int:
        """推送给某个用户的所有在线连接，返回成功投递数。"""
        ok = 0
        for ws in self.connections_of(user_id):
            try:
                await ws.send_json(payload)
                ok += 1
            except Exception:
                # 连接已坏：摘除，避免后续反复失败
                self.drop(ws)
        return ok

    async def send_to_users(self, user_ids: list[int], payload: dict[str, Any]) -> int:
        total = 0
        for uid in {u for u in user_ids if u}:
            total += await self.send_to_user(uid, payload)
        return total


# 全局单例：HTTP 路由（发私信/点赞/评论）与 WS 路由共用
manager = ConnectionManager()
