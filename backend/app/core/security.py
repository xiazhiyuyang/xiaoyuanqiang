from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import hmac
import re
from urllib.parse import urlparse

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 站内页面跳转白名单（App 内路由）
_INTERNAL_LINK_RE = re.compile(r"^/pages/[a-zA-Z0-9_\-/]+$")


def is_safe_link(url: str | None) -> bool:
    """判断运营位/公告配置的跳转链接是否安全。

    允许站内 /pages/... 路由与 http/https 外链；
    拒绝 javascript:/data:/vbscript: 等可执行协议、协议相对 URL。
    """
    if not url:
        return True
    url = url.strip()
    if not url or len(url) > 500:
        return False
    if _INTERNAL_LINK_RE.match(url):
        return True
    if url.startswith("//") or url.startswith("\\"):
        return False
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        return False
    return bool(parsed.netloc)


def is_own_media_url(url: str | None) -> bool:
    """帖子/头像引用的媒体必须是本站 /uploads/ 相对路径，禁止任意外链。"""
    if not url:
        return False
    return bool(re.match(r"^/uploads/[A-Za-z0-9_\-./]+$", url))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def token_version(user) -> str:
    """会话版本号：由当前密码哈希派生。

    改密 / 管理员重置密码 / 密保找回 都会让 password_hash 变化，
    从而让此前签发的所有 token 立即失效——不依赖额外的令牌表，
    也不需要数据库加字段。以 SECRET_KEY 做 HMAC，避免把密码哈希的
    摘要直接暴露在 token 载荷里。
    """
    raw = (getattr(user, "password_hash", "") or "").encode("utf-8")
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"), raw, hashlib.sha256
    ).hexdigest()[:16]


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def anonymous_alias(user_id: int, post_id: int) -> str:
    """生成「同一帖内稳定、跨帖不可关联」的匿名昵称。

    旧实现用 user_id % 10000，导致同一用户在所有匿名帖下编号相同，
    可被交叉比对去匿名化。这里以 SECRET_KEY 为密钥，对 post_id+user_id
    做 HMAC，编号只在单帖范围内稳定，无法跨帖追踪。
    """
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"anon:{post_id}:{user_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"匿名用户#{int(digest[:8], 16) % 10000:04d}"
