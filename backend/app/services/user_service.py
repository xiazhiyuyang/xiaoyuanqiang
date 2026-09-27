"""用户相关业务逻辑：创建、封禁、软删除/恢复、锁定清除。

api 层（admin/users.py、auth.py）只做参数校验与日志，
用户状态变更收敛到本服务。所有方法均不自行提交事务，由调用方统一 commit。
"""
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(func.lower(User.username) == username.lower()))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    username: str,
    nickname: str,
    password: str,
    role: str = "user",
    extra: dict | None = None,
) -> User:
    """创建用户（bcrypt 放线程池）。调用方负责 commit。"""
    data = {
        "username": username,
        "nickname": nickname,
        "password_hash": await run_in_threadpool(hash_password, password),
        "role": role,
    }
    if extra:
        data.update(extra)
    user = User(**data)
    db.add(user)
    await db.flush()
    return user


async def soft_delete_user(db: AsyncSession, user: User) -> None:
    """软删除用户：标记注销、记录时间、封存 UID。调用方 commit。"""
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        from app.core.uid_allocator import reserve_uid
        await reserve_uid(db, user.id)
    except Exception:
        pass


async def restore_user(db: AsyncSession, user: User) -> None:
    """从回收站恢复用户，同时清除锁定状态。调用方 commit。"""
    user.is_deleted = False
    user.deleted_at = None
    user.failed_login_count = 0
    user.locked_until = None


async def toggle_ban(user: User) -> bool:
    """切换封禁状态，返回切换后的 is_banned。调用方 commit。"""
    user.is_banned = not user.is_banned
    return user.is_banned


def reset_lockout(user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
