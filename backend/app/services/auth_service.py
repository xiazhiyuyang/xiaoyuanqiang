"""认证相关业务逻辑：登录锁定、失败计数、密码校验辅助。

api 层（auth.py）只负责参数校验、日志记录与 token 发放，
锁定/失败计数等核心状态变更收敛到本服务。
"""
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


def _parse_locked_until(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def assert_not_locked(user: User) -> None:
    """登录前检查账户锁定状态。

    - 未过期：抛 423
    - 已过期：在内存中清空 locked_until / failed_login_count（由调用方在成功路径提交）
    """
    until = _parse_locked_until(user.locked_until)
    if until is None:
        return
    if datetime.now(timezone.utc) < until:
        raise HTTPException(status_code=423, detail="账号已锁定，请15分钟后再试")
    user.locked_until = None
    user.failed_login_count = 0


async def record_failed_login(db: AsyncSession, user: User) -> bool:
    """记录一次失败登录。返回 True 表示已触发锁定（调用方应记录锁定日志并抛 423）。"""
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
        user.locked_until = (
            datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
        ).isoformat(timespec="seconds")
        user.failed_login_count = 0
        await db.commit()
        return True
    await db.commit()
    return False


def clear_lockout(user: User) -> None:
    """登录成功 / 重置密码后清除失败计数与锁定状态（由调用方提交）。"""
    user.failed_login_count = 0
    user.locked_until = None
