"""Redis 客户端（可选依赖，故障时自动降级）。

设计原则：**Redis 挂了不能把业务打挂。**
所有调用方都必须通过本模块提供的封装，且封装内部吞掉连接异常并返回 None，
由调用方决定降级行为（限流退化为进程内计数、缓存退化为直接查库）。

配置：环境变量 REDIS_URL，例如
    redis://:password@127.0.0.1:6379/0
未配置时本模块完全禁用，行为与引入 Redis 之前一致。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("campus-wall")

_client = None
_init_attempted = False
_available = False


def _init() -> None:
    """惰性初始化。只尝试一次，失败则永久降级为不可用（避免每个请求都重试拖慢）。"""
    global _client, _init_attempted, _available
    if _init_attempted:
        return
    _init_attempted = True
    if not settings.REDIS_URL:
        logger.info("未配置 REDIS_URL，缓存/分布式限流已禁用（使用进程内降级实现）")
        return
    try:
        from redis import asyncio as aioredis
    except ImportError:  # redis 包未安装
        logger.warning("redis 包未安装，已降级为进程内实现")
        return
    try:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            health_check_interval=30,
        )
        _available = True
        logger.info("Redis 客户端已初始化")
    except Exception:
        _client = None
        _available = False
        logger.warning("Redis 初始化失败，已降级为进程内实现", exc_info=True)


def get_client():
    """返回 redis 异步客户端；不可用时返回 None。"""
    _init()
    return _client if _available else None


def is_available() -> bool:
    _init()
    return _available


async def ping() -> bool:
    """健康探测：供 /api/health 与启动自检使用。"""
    client = get_client()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        return False


async def safe_get(key: str) -> Optional[str]:
    client = get_client()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception:
        logger.warning("Redis GET 失败 key=%s，本次降级", key, exc_info=True)
        return None


async def safe_set(key: str, value: str, ttl: int) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        await client.set(key, value, ex=ttl)
        return True
    except Exception:
        logger.warning("Redis SET 失败 key=%s，本次降级", key, exc_info=True)
        return False


async def safe_delete(*keys: str) -> None:
    """删除缓存键；键数量可能较大时分批，避免单条命令过长。"""
    client = get_client()
    if client is None or not keys:
        return
    try:
        flat = [k for k in keys if k]
        for i in range(0, len(flat), 200):
            await client.delete(*flat[i:i + 200])
    except Exception:
        logger.warning("Redis DEL 失败，忽略（缓存将自然过期）", exc_info=True)


async def safe_delete_pattern(pattern: str) -> None:
    """按前缀批量失效。用 SCAN 而非 KEYS，避免阻塞 Redis 主线程。"""
    client = get_client()
    if client is None:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning("Redis SCAN/DEL 失败 pattern=%s，忽略", pattern, exc_info=True)


async def close() -> None:
    global _client, _available
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
    _client = None
    _available = False
