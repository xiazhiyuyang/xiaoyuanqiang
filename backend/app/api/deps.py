from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import decode_access_token, token_version
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未登录或登录已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exc

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exc
    # 密码变更后旧 token 立即失效（改密 / 管理员重置 / 密保找回）
    if payload.get("pv") != token_version(user):
        raise credentials_exc
    if user.is_deleted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被注销")
    # 检查注销冷静期是否到期，到期则执行软删除
    from app.api.users import check_and_execute_deletion
    if await check_and_execute_deletion(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被注销")
    if user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被封禁")
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """可选登录 - 未登录返回 None"""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or user.is_banned or user.is_deleted:
        return None
    # 同样校验会话版本：否则改密前的旧 token 仍能以该用户身份读取其私密内容
    if payload.get("pv") != token_version(user):
        return None
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


def require_permission(*perm_keys: str):
    """权限门：管理员直接放行；普通用户必须被授予指定权限中的任意一项。

    被授权用户只能访问被授予的单项能力，不拥有任何其他管理员权限。
    """
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role == "admin":
            return user
        if any(user.has_permission(k) for k in perm_keys):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你没有这项权限，需要管理员授权",
        )
    return _checker
