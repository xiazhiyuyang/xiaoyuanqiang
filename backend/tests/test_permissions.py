"""权限模型测试。

细粒度授权是本项目最容易改错的地方：「被授予某项权限的普通用户」
绝不能因此获得其他管理员能力。这里把矩阵锁死。
"""
from __future__ import annotations

import pytest

from app.models.user import User, staff_tags_of


def _user(role: str = "user", permissions: str = "") -> User:
    u = User(username="t", nickname="t", password_hash="x")
    u.role = role
    u.permissions = permissions
    return u



@pytest.mark.parametrize("raw,expected", [
    ("", []),
    (None, []),
    ("content_review", ["content_review"]),
    ("content_review,report_review", ["content_review", "report_review"]),
    ("  content_review , report_review ", ["content_review", "report_review"]),
    ("content_review,,report_review", ["content_review", "report_review"]),
    (",,,", []),
])
def test_permission_list_parsing(raw, expected):
    assert _user(permissions=raw).permission_list == expected



def test_admin_has_every_permission_including_unregistered_keys():
    admin = _user(role="admin", permissions="")
    assert admin.has_permission("content_review") is True
    assert admin.has_permission("some_future_key") is True


def test_normal_user_denied_by_default():
    u = _user()
    assert u.has_permission("content_review") is False
    assert u.has_permission("report_review") is False


def test_granted_user_only_gets_the_granted_key():
    """核心断言：授了 A 不等于拥有 B。"""
    u = _user(permissions="content_review")
    assert u.has_permission("content_review") is True
    assert u.has_permission("report_review") is False
    assert u.has_permission("user_manage") is False


def test_permission_match_is_exact_not_substring():
    """不能被前缀/子串误命中，否则 'review' 会匹配到 'content_review'。"""
    u = _user(permissions="content_review")
    assert u.has_permission("review") is False
    assert u.has_permission("content") is False
    assert u.has_permission("content_revie") is False


def test_banned_flag_is_independent_of_permissions():
    """封禁与授权是两个维度：被封禁的授权用户仍然是 banned，由 deps 层拦截。"""
    u = _user(permissions="content_review")
    u.is_banned = True
    assert u.has_permission("content_review") is True
    assert u.is_banned is True



def test_admin_tag_only_shows_admin():
    admin = _user(role="admin", permissions="content_review,report_review")
    assert staff_tags_of(admin) == ["admin"]


def test_granted_user_shows_specific_tags():
    u = _user(permissions="content_review,report_review")
    assert staff_tags_of(u) == ["content_review", "report_review"]


def test_normal_user_has_no_staff_tag():
    assert staff_tags_of(_user()) == []


def test_staff_tags_of_none_is_safe():
    assert staff_tags_of(None) == []


def test_unknown_permission_does_not_create_tag():
    """有权限 key 但不在标签映射里的，不应凭空冒出身份标签。"""
    u = _user(permissions="some_future_key")
    assert staff_tags_of(u) == []
