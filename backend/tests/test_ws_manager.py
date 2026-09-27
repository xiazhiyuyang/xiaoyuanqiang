"""WebSocket 连接管理器测试。

重点锁死「连接计数不能泄漏」：本项目曾因 finally 里 `await hb_task` 抛出
CancelledError（BaseException，suppress(Exception) 压不住）导致 disconnect()
执行不到，在线人数只增不减。这里用假 WebSocket 覆盖计数语义与坏连接摘除。
"""
from __future__ import annotations

import pytest

from app.core.ws_manager import ConnectionManager


class FakeWS:
    """最小可用的 WebSocket 替身。"""

    def __init__(self, name: str = "ws", fail: bool = False):
        self.name = name
        self.fail = fail
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        if self.fail:
            raise RuntimeError("connection closed by peer")
        self.sent.append(payload)

    def __repr__(self) -> str:
        return f"<FakeWS {self.name}>"


@pytest.fixture
def mgr():
    return ConnectionManager()



def test_empty_manager_reports_zero(mgr):
    assert mgr.online_users == 0
    assert mgr.total_connections == 0
    assert mgr.is_online(1) is False


def test_connect_increments_counts(mgr):
    ws = FakeWS("a")
    mgr.connect(1, ws)
    assert mgr.online_users == 1
    assert mgr.total_connections == 1
    assert mgr.is_online(1) is True


def test_disconnect_removes_user_entirely(mgr):
    """核心回归：断开后用户键必须被删除，否则 online_users 永远不归零。"""
    ws = FakeWS("a")
    mgr.connect(1, ws)
    mgr.disconnect(1, ws)
    assert mgr.online_users == 0
    assert mgr.total_connections == 0
    assert mgr.is_online(1) is False


def test_multi_connection_per_user(mgr):
    """同一用户多端在线：连接数累加，但在线用户数仍为 1。"""
    a, b = FakeWS("a"), FakeWS("b")
    mgr.connect(7, a)
    mgr.connect(7, b)
    assert mgr.online_users == 1
    assert mgr.total_connections == 2
    mgr.disconnect(7, a)
    assert mgr.online_users == 1        # 还有一条连接，用户仍在线
    assert mgr.total_connections == 1
    mgr.disconnect(7, b)
    assert mgr.online_users == 0


def test_disconnect_is_idempotent(mgr):
    """重复断开不能报错，也不能把别的用户误删。"""
    ws = FakeWS("a")
    mgr.connect(1, ws)
    mgr.disconnect(1, ws)
    mgr.disconnect(1, ws)               # 再来一次
    mgr.disconnect(999, FakeWS("x"))    # 从未连接过的用户
    assert mgr.online_users == 0


def test_connect_same_socket_twice_is_deduped(mgr):
    ws = FakeWS("a")
    mgr.connect(1, ws)
    mgr.connect(1, ws)
    assert mgr.total_connections == 1


def test_multiple_users_counted_separately(mgr):
    mgr.connect(1, FakeWS("a"))
    mgr.connect(2, FakeWS("b"))
    assert mgr.online_users == 2
    assert mgr.total_connections == 2



def test_drop_removes_socket_from_all_users(mgr):
    shared = FakeWS("shared")
    mgr.connect(1, shared)
    mgr.connect(2, shared)
    mgr.drop(shared)
    assert mgr.total_connections == 0
    assert mgr.online_users == 0


@pytest.mark.asyncio
async def test_send_to_user_delivers_to_all_connections(mgr):
    a, b = FakeWS("a"), FakeWS("b")
    mgr.connect(5, a)
    mgr.connect(5, b)
    ok = await mgr.send_to_user(5, {"type": "unread", "message": 3})
    assert ok == 2
    assert a.sent == [{"type": "unread", "message": 3}]
    assert b.sent == [{"type": "unread", "message": 3}]


@pytest.mark.asyncio
async def test_send_to_offline_user_is_noop(mgr):
    assert await mgr.send_to_user(42, {"type": "ping"}) == 0


@pytest.mark.asyncio
async def test_broken_connection_is_dropped_on_send_failure(mgr):
    """发送失败必须把坏连接摘掉，否则会随每次推送反复失败并泄漏计数。"""
    good, bad = FakeWS("good"), FakeWS("bad", fail=True)
    mgr.connect(5, good)
    mgr.connect(5, bad)
    ok = await mgr.send_to_user(5, {"type": "ping"})
    assert ok == 1                      # 只有 good 投递成功
    assert good.sent == [{"type": "ping"}]
    assert mgr.total_connections == 1   # bad 已被摘除
    assert mgr.online_users == 1


@pytest.mark.asyncio
async def test_all_connections_broken_removes_user(mgr):
    bad = FakeWS("bad", fail=True)
    mgr.connect(5, bad)
    assert await mgr.send_to_user(5, {"type": "ping"}) == 0
    assert mgr.online_users == 0


@pytest.mark.asyncio
async def test_send_to_users_dedupes_targets(mgr):
    ws = FakeWS("a")
    mgr.connect(1, ws)
    ok = await mgr.send_to_users([1, 1, 1, 0, None], {"type": "ping"})
    assert ok == 1                      # 同一用户只投一次，0/None 被忽略
    assert len(ws.sent) == 1


def test_connections_of_returns_copy(mgr):
    """返回副本，避免调用方遍历时被 disconnect 改动集合。"""
    ws = FakeWS("a")
    mgr.connect(1, ws)
    snapshot = mgr.connections_of(1)
    mgr.disconnect(1, ws)
    assert snapshot == [ws]
    assert mgr.connections_of(1) == []
