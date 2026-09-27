"""安全工具测试。

这些是「改错了会直接造成隐私泄漏或越权」的函数，属于必须锁死的行为：
- 匿名昵称跨帖不可关联（否则匿名用户可被交叉比对去匿名化）
- 媒体/链接白名单（否则可被用来挂外链或注入 javascript:）
- 会话版本号（否则改密后旧 token 仍然有效）
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import (
    anonymous_alias,
    create_access_token,
    decode_access_token,
    hash_password,
    is_own_media_url,
    is_safe_link,
    token_version,
    verify_password,
)


class _FakeUser:
    def __init__(self, password_hash: str):
        self.password_hash = password_hash



def test_anonymous_alias_stable_within_same_post():
    """同一用户在同一帖下的匿名编号必须稳定，否则刷新页面就换身份。"""
    a = anonymous_alias(user_id=7, post_id=42)
    b = anonymous_alias(user_id=7, post_id=42)
    assert a == b
    assert a.startswith("匿名用户#")


def test_anonymous_alias_not_correlatable_across_posts():
    """同一用户在不同帖下的编号必须不同——这是防去匿名化的核心。

    旧实现用 user_id % 10000，导致该用户在所有匿名帖下编号相同，
    只要拿到两个匿名帖就能确认是同一人。
    """
    aliases = {anonymous_alias(user_id=7, post_id=pid) for pid in range(1, 200)}
    # 200 个不同帖子应当产生大量不同编号；允许极小概率碰撞，但不能退化成 1 个
    assert len(aliases) > 150


def test_anonymous_alias_differs_between_users_in_same_post():
    a = anonymous_alias(user_id=1, post_id=42)
    b = anonymous_alias(user_id=2, post_id=42)
    assert a != b


def test_anonymous_alias_format_is_four_digits():
    alias = anonymous_alias(user_id=12345, post_id=999)
    suffix = alias.split("#")[1]
    assert len(suffix) == 4 and suffix.isdigit()



@pytest.mark.parametrize("url", [
    "/uploads/202608/01cfae78ecde4aa99a37bf6484ae3556.png",
    "/uploads/app/campuswall-1.2.12_132.apk",
])
def test_is_own_media_url_accepts_local_uploads(url):
    assert is_own_media_url(url) is True


@pytest.mark.parametrize("url", [
    "",
    None,
    "http://evil.com/x.png",
    "https://evil.com/x.png",
    "//evil.com/x.png",
    "/uploads/../../etc/passwd",
    "/uploads/202608/../../../etc/shadow",
    "/uploads//etc/passwd",
    "/uploads/a b.png",
    "javascript:alert(1)",
    "/static/logo.png",          # 非 uploads 目录一律拒绝
])
def test_is_own_media_url_rejects_everything_else(url):
    assert is_own_media_url(url) is False


def test_is_own_media_url_accepts_real_release_filenames():
    """APK 文件名含多个点号，不能被穿越检查误杀。"""
    assert is_own_media_url("/uploads/app/campuswall-1.2.12_132.apk") is True
    assert is_own_media_url("/uploads/202608/01cfae78ecde4aa99a37bf6484ae3556.png") is True



@pytest.mark.parametrize("url", [
    "/pages/post/detail?id=1",
    "http://example.com",
    "https://example.com/a?b=1",
    "",
    None,
])
def test_is_safe_link_accepts(url):
    assert is_safe_link(url) is True


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "//evil.com",                # 协议相对 URL：会继承当前页面协议
    "\\evil.com",
    "https://" + "a" * 600 + ".com",   # 超长
])
def test_is_safe_link_rejects(url):
    assert is_safe_link(url) is False



def test_token_version_changes_when_password_changes():
    """改密后 token_version 必须变化，deps 层据此让所有旧 token 立即失效。"""
    u = _FakeUser(hash_password("old-password"))
    v1 = token_version(u)
    u.password_hash = hash_password("new-password")
    v2 = token_version(u)
    assert v1 != v2
    assert len(v1) == 16


def test_token_version_stable_for_same_hash():
    u = _FakeUser("fixed-hash-value")
    assert token_version(u) == token_version(u)


def test_token_version_does_not_leak_hash():
    """版本号是 HMAC 摘要，不能包含密码哈希本身的任何片段。"""
    raw_hash = hash_password("secret-password")
    u = _FakeUser(raw_hash)
    version = token_version(u)
    assert raw_hash[:8] not in version
    assert version not in raw_hash



def test_jwt_roundtrip():
    token = create_access_token({"sub": "42", "pv": "abcd1234abcd1234"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["pv"] == "abcd1234abcd1234"


def test_jwt_expired_token_rejected():
    token = create_access_token({"sub": "42"}, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(token) is None


def test_jwt_tampered_token_rejected():
    token = create_access_token({"sub": "42"})
    assert decode_access_token(token[:-2] + "xx") is None


def test_password_hash_roundtrip():
    hashed = hash_password("p@ssw0rd-测试")
    assert verify_password("p@ssw0rd-测试", hashed) is True
    assert verify_password("wrong", hashed) is False
