"""WebSocket 实时通道：私信 / 通知推送。

端点：`/ws/realtime?token=<JWT>`

为什么用查询参数传 token 而不是 Authorization 头：
浏览器原生 WebSocket 不支持自定义请求头，H5 端拿不到 header 通道；
uni.connectSocket 在 App 端虽支持 header，但为了两端一致统一走 query。
该 URL 不写入日志（见下方访问日志中间件的排除规则），避免 token 泄漏到日志文件。

协议（服务端 → 客户端）：
    {"type":"welcome","unread_message":N,"unread_notification":N}
    {"type":"message","conversation_id":1,"message":{...}}
    {"type":"unread","message":N,"notification":N}
    {"type":"notification","notification":{...}}
    {"type":"pong"}
协议（客户端 → 服务端）：
    {"type":"ping"}
    {"type":"sub","conversation_id":1}   # 声明当前所在会话，用于精准已读推送

连接不可用时前端自动回退到轮询，因此本通道是「优化」而非「唯一路径」。
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, or_, select

from app.core.security import decode_access_token, token_version
from app.core.ws_manager import manager
from app.database import AsyncSessionLocal
from app.models.message import Conversation, Message
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger("campus-wall")

router = APIRouter(tags=["实时通道"])

HEARTBEAT_INTERVAL = 25      # 服务端心跳间隔（秒）
RECEIVE_TIMEOUT = 90         # 超过该时长收不到任何帧即判定连接已死
MAX_MESSAGE_BYTES = 4096     # 客户端帧大小上限，防内存放大


async def _authenticate(raw_token: str | None) -> User | None:
    """校验 JWT + 会话版本 + 封禁状态，失败返回 None。"""
    if not raw_token:
        return None
    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user or user.is_banned:
            return None
        # 与 HTTP 依赖同一套会话版本校验：改密后旧 token 立刻失效
        if payload.get("pv") != token_version(user):
            return None
        return user


async def _unread_counts(user_id: int) -> tuple[int, int]:
    """返回 (未读私信数, 未读通知数)。"""
    async with AsyncSessionLocal() as db:
        msg_count = (await db.execute(
            select(func.count())
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                or_(Conversation.user1_id == user_id, Conversation.user2_id == user_id),
                Message.sender_id != user_id,
                Message.is_read == False,  # noqa: E712
            )
        )).scalar() or 0
        noti_count = (await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        )).scalar() or 0
    return int(msg_count), int(noti_count)


async def push_unread(user_id: int) -> None:
    """重算并推送未读数。任何异常都不得冒泡到业务调用方。"""
    if not manager.is_online(user_id):
        return
    try:
        msg_unread, noti_unread = await _unread_counts(user_id)
        await manager.send_to_user(user_id, {
            "type": "unread", "message": msg_unread, "notification": noti_unread,
        })
    except Exception:
        logger.warning("推送未读数失败 user=%s", user_id, exc_info=True)


async def push_message(user_id: int, conversation_id: int, message_dict: dict) -> None:
    if not manager.is_online(user_id):
        return
    try:
        await manager.send_to_user(user_id, {
            "type": "message", "conversation_id": conversation_id, "message": message_dict,
        })
    except Exception:
        logger.warning("推送私信失败 user=%s", user_id, exc_info=True)


async def push_notification(user_id: int, notification_dict: dict) -> None:
    if not manager.is_online(user_id):
        return
    try:
        await manager.send_to_user(user_id, {
            "type": "notification", "notification": notification_dict,
        })
    except Exception:
        logger.warning("推送通知失败 user=%s", user_id, exc_info=True)


@router.websocket("/ws/realtime")
async def realtime(websocket: WebSocket, token: str = Query(default="")):
    user = await _authenticate(token)
    if user is None:
        # 必须先 accept 再 close，客户端才收得到 4401 这个自定义关闭码。
        # 若在 accept 之前 close，Starlette 会直接回一个 HTTP 403 拒绝握手，
        # 前端只能看到「连接失败」，无法区分「token 失效」和「网络不通」，
        # 也就没法在 token 失效时清理本地登录态。
        try:
            await websocket.accept()
            await websocket.close(code=4401)
        except Exception:
            pass
        return

    await websocket.accept()
    manager.connect(user.id, websocket)

    async def _heartbeat() -> None:
        with contextlib.suppress(Exception):
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await websocket.send_json({"type": "ping"})

    hb_task = asyncio.create_task(_heartbeat())
    try:
        msg_unread, noti_unread = await _unread_counts(user.id)
        await websocket.send_json({
            "type": "welcome",
            "user_id": user.id,
            "unread_message": msg_unread,
            "unread_notification": noti_unread,
        })
        while True:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=RECEIVE_TIMEOUT)
            if not raw or len(raw) > MAX_MESSAGE_BYTES:
                continue
            # 客户端只需心跳；其余帧忽略但不断开，保证向前兼容
            try:
                frame = json.loads(raw)
            except ValueError:
                continue
            if isinstance(frame, dict) and frame.get("type") == "ping":
                with contextlib.suppress(Exception):
                    await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        logger.info("WS 心跳超时，关闭连接 user=%s", user.id)
    except asyncio.CancelledError:
        # 客户端断连时协程会被取消：必须重新抛出，否则 asyncio 认为任务未正确结束
        raise
    except Exception:
        logger.warning("WS 异常关闭 user=%s", user.id, exc_info=True)
    finally:
        # 先做「不需要 await」的清理，保证在协程已处于 cancelling 状态时也能执行完。
        # 踩过的坑：原先这里先 `await hb_task`，而 asyncio.CancelledError 继承自
        # BaseException、`contextlib.suppress(Exception)` 压不住它，异常从 finally
        # 里外泄，后面的 disconnect() 永远执行不到 —— 表现为连接断开后
        # 在线人数只增不减（连接泄漏）。
        manager.disconnect(user.id, websocket)
        hb_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await hb_task
        with contextlib.suppress(Exception):
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
