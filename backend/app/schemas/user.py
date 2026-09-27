import re
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator

from app.core.activity import DEFAULT_PRIVACY, PRIVACY_LEVELS

# bcrypt 只使用前 72 字节：超过部分会被静默丢弃，
# 意味着两个只有第 73 字节起不同的密码会互相通过校验。
# 中文等多字节字符下 64 个"字符"可达 192 字节，因此必须按字节数设限。
BCRYPT_MAX_BYTES = 72

# 允许的特殊字符集
_SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
# 常见弱密码黑名单（小写匹配）
_WEAK_PASSWORDS = {
    "password", "password1", "password12", "password123", "passw0rd",
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "admin", "admin123", "admin123456", "root", "root123",
    "qwerty", "qwerty123", "abc123", "iloveyou", "monkey",
    "dragon", "letmein", "welcome", "football", "master",
    "111111", "000000", "666666", "888888",
}


def validate_password_strength(value: str) -> str:
    """统一密码强度校验：至少8位；命中常见弱密码直接拒绝。
    不要求大小写、数字、特殊字符，降低用户注册门槛。校验通过后仍做 bcrypt 72 字节截断检查。"""
    v = value or ""
    if len(v) < 8:
        raise ValueError("密码至少需要 8 位")
    if v.lower() in _WEAK_PASSWORDS:
        raise ValueError("密码过于常见，请勿使用弱密码")
    return _check_password_bytes(v)


def _check_password_bytes(value: str) -> str:
    if len((value or "").encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"密码过长，最多 {BCRYPT_MAX_BYTES} 个字节（中文约 24 个字）")
    return value


def _empty_to_none(value):
    if value is None:
        return None
    value = value.strip()
    return value or None


class UserCreate(BaseModel):
    username: str = Field(max_length=32)
    password: str = Field(max_length=64)
    nickname: str = Field(max_length=32)
    student_id: str | None = Field(None, max_length=20)
    phone: str | None = Field(None, max_length=20)
    agree: bool = Field(False, description="是否同意隐私政策与用户协议")
    device_code: str | None = Field(None, max_length=128, description="前端生成的设备唯一标识码")
    fingerprint_hash: str | None = Field(None, max_length=32, description="浏览器设备指纹哈希")

    @field_validator("username")
    @classmethod
    def _username_rule(cls, v: str) -> str:
        v = (v or "").strip()
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,32}", v):
            raise ValueError("用户名需为 3-32 位字母、数字或下划线")
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("nickname")
    @classmethod
    def _nickname_rule(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("昵称不能为空")
        return v[:32]


class UserLogin(BaseModel):
    username: str
    password: str
    device_code: str | None = Field(None, max_length=128, description="前端生成的设备唯一标识码")
    fingerprint_hash: str | None = Field(None, max_length=32, description="浏览器设备指纹哈希（Canvas/WebGL等）")


class WechatLogin(BaseModel):
    code: str = Field(min_length=1, description="微信登录凭证 code")
    scene: str = Field("mp", pattern=r"^(mp|open)$",
                       description="mp=小程序jscode2session / open=公众号H5或App开放平台oauth2")


class EmailRegister(BaseModel):
    email: str = Field(min_length=3, max_length=128, description="邮箱地址")
    username: str = Field(min_length=3, max_length=32, description="用户名")
    nickname: str = Field(max_length=32, description="昵称")
    password: str = Field(max_length=64, description="密码")
    student_id: str | None = Field(None, max_length=20)
    device_code: str | None = Field(None, max_length=128)
    fingerprint_hash: str | None = Field(None, max_length=32)


class EmailVerify(BaseModel):
    token: str = Field(min_length=1, description="验证token")


class EmailForgot(BaseModel):
    email: str = Field(min_length=3, max_length=128, description="邮箱地址")


class EmailReset(BaseModel):
    token: str = Field(min_length=1, description="重置token")
    password: str = Field(max_length=64, description="新密码")


class EmailLogin(BaseModel):
    email: str = Field(min_length=3, max_length=128, description="邮箱地址")
    password: str = Field(max_length=64, description="密码")
    device_code: str | None = Field(None, max_length=128)
    fingerprint_hash: str | None = Field(None, max_length=32)


class ProfileCompletion(BaseModel):
    """第三方登录后完善资料。"""
    username: str | None = Field(None, min_length=3, max_length=32)
    nickname: str | None = Field(None, max_length=32)
    password: str | None = Field(None, max_length=64)
    email: str | None = Field(None, max_length=128)


class UserUpdate(BaseModel):
    nickname: str | None = Field(None, max_length=32)
    avatar: str | None = Field(None, max_length=500)
    cover_image: str | None = Field(None, max_length=500)
    bio: str | None = Field(None, max_length=200)
    gender: str | None = Field(None, pattern=r"^(unknown|male|female)$")
    grade: str | None = Field(None, max_length=32)
    college: str | None = Field(None, max_length=64)
    major: str | None = Field(None, max_length=64)
    location: str | None = Field(None, max_length=64)
    birthday: str | None = Field(None, max_length=10)
    student_id: str | None = Field(None, max_length=20)
    phone: str | None = Field(None, max_length=20)
    privacy: dict | None = None
    preferences: dict | None = None

    @field_validator("preferences")
    @classmethod
    def _preferences_valid(cls, v):
        if v is None:
            return None
        from app.core.activity import sanitize_preferences
        return sanitize_preferences(v)

    @field_validator(
        "bio", "grade", "college", "major", "location",
        "birthday", "student_id", "phone",
    )
    @classmethod
    def _trim_optional(cls, v):
        return _empty_to_none(v)

    @field_validator("nickname")
    @classmethod
    def _nickname_required(cls, v):
        v = _empty_to_none(v)
        if v is not None and not v.strip():
            raise ValueError("昵称不能为空")
        return v.strip() if v else v

    @field_validator("avatar")
    @classmethod
    def _avatar_safe(cls, v):
        v = _empty_to_none(v)
        if v and not (v.startswith("/uploads/") or re.match(r"^https?://", v)):
            raise ValueError("头像地址不合法")
        return v

    @field_validator("birthday")
    @classmethod
    def _birthday_valid(cls, v):
        v = _empty_to_none(v)
        if v:
            try:
                parsed = date.fromisoformat(v)
            except ValueError as exc:
                raise ValueError("生日格式应为 YYYY-MM-DD") from exc
            if parsed.year < 1900 or parsed > date.today():
                raise ValueError("生日日期不正确")
        return v

    @field_validator("phone")
    @classmethod
    def _phone_valid(cls, v):
        v = _empty_to_none(v)
        if v and not re.fullmatch(r"1[3-9]\d{9}", v):
            raise ValueError("请输入正确的 11 位手机号")
        return v

    @field_validator("student_id")
    @classmethod
    def _student_id_valid(cls, v):
        v = _empty_to_none(v)
        if v and not re.fullmatch(r"[A-Za-z0-9_-]{4,20}", v):
            raise ValueError("学号应为 4-20 位字母、数字、下划线或短横线")
        return v

    @field_validator("privacy")
    @classmethod
    def _privacy_valid(cls, v):
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("可见范围格式不正确")
        result = dict(DEFAULT_PRIVACY)
        for key in DEFAULT_PRIVACY:
            val = v.get(key)
            if val is not None:
                if val not in PRIVACY_LEVELS:
                    raise ValueError("可见范围取值不合法")
                result[key] = val
        return result


class UserResponse(BaseModel):
    id: int
    uid: str | None = None
    username: str
    nickname: str
    avatar: str | None
    cover_image: str | None = None
    bio: str | None
    gender: str = "unknown"
    grade: str | None = None
    college: str | None = None
    major: str | None = None
    location: str | None = None
    birthday: str | None = None
    student_id: str | None = None
    phone: str | None = None
    email: str | None = None
    email_verified: bool = False
    need_profile_completion: bool = False
    privacy: dict | None = None
    preferences: dict | None = None
    role: str
    is_banned: bool
    exp: int = 0
    level: int = 1
    perms: list[str] = []
    has_security: bool = False
    created_at: datetime
    model_config = {"from_attributes": True }

    @field_validator("privacy", mode="before")
    @classmethod
    def _parse_privacy(cls, v):
        from app.core.activity import parse_privacy
        if isinstance(v, dict):
            return v
        return parse_privacy(v)

    @field_validator("preferences", mode="before")
    @classmethod
    def _parse_preferences(cls, v):
        from app.core.activity import parse_preferences
        if isinstance(v, dict):
            return v
        return parse_preferences(v)

    @classmethod
    def from_user(cls, user):
        """统一构造：把 ORM 上的 permission_list 映射到 perms。"""
        return cls.model_validate({
            "id": user.id, "uid": getattr(user, "uid", None), "username": user.username, "nickname": user.nickname,
            "avatar": user.avatar, "cover_image": getattr(user, "cover_image", None),
            "bio": user.bio, "gender": user.gender,
            "grade": user.grade, "college": user.college, "major": user.major,
            "location": user.location, "birthday": user.birthday,
            "student_id": user.student_id, "phone": user.phone,
            "email": getattr(user, "email", None), "email_verified": getattr(user, "email_verified", False),
            "need_profile_completion": getattr(user, "need_profile_completion", False),
            "privacy": user.privacy, "preferences": getattr(user, "preferences", None),
            "role": user.role, "is_banned": user.is_banned,
            "exp": user.exp or 0, "level": user.level or 1,
            "perms": user.permission_list,
            "has_security": bool(user.security_question),
            "created_at": user.created_at,
        })


# ---------- 账号安全 / 管理相关 ----------
class ChangePassword(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(max_length=64)

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v):
        return validate_password_strength(v)


class SecurityQuestionSet(BaseModel):
    question: str = Field(min_length=2, max_length=100)
    answer: str = Field(min_length=1, max_length=64)

    @field_validator("answer")
    @classmethod
    def _answer_bytes(cls, v):
        return _check_password_bytes(v)


class ForgotQuestion(BaseModel):
    username: str = Field(min_length=3, max_length=32)


class ForgotReset(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    answer: str = Field(min_length=1, max_length=64)
    new_password: str = Field(max_length=64)

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v):
        return validate_password_strength(v)


class AdminUserCreate(BaseModel):
    username: str = Field(max_length=32)
    password: str = Field(max_length=64)
    nickname: str = Field(max_length=32)
    role: str = Field("user", pattern=r"^(user|admin)$")

    @field_validator("username")
    @classmethod
    def _u(cls, v):
        v = (v or "").strip()
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,32}", v):
            raise ValueError("用户名需为 3-32 位字母、数字或下划线")
        return v.lower()

    @field_validator("password")
    @classmethod
    def _p(cls, v):
        return validate_password_strength(v)

    @field_validator("nickname")
    @classmethod
    def _n(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("昵称不能为空")
        return v[:32]


class AdminUserUpdate(BaseModel):
    nickname: str | None = Field(None, max_length=32)
    role: str | None = Field(None, pattern=r"^(user|admin)$")
    gender: str | None = Field(None, pattern=r"^(unknown|male|female)$")
    college: str | None = Field(None, max_length=64)
    grade: str | None = Field(None, max_length=32)
    major: str | None = Field(None, max_length=64)
    location: str | None = Field(None, max_length=64)
    bio: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=20)
    avatar: str | None = Field(None, max_length=500)
    cover_image: str | None = Field(None, max_length=500)
    exp: int | None = Field(None, ge=0, le=10_000_000)


class AdminResetPassword(BaseModel):
    new_password: str | None = Field(None, max_length=64)

    @field_validator("new_password")
    @classmethod
    def _p(cls, v):
        if v is None:
            return None
        return validate_password_strength(v)


class PermissionUpdate(BaseModel):
    permissions: list[str] = []

    @field_validator("permissions")
    @classmethod
    def _valid(cls, v):
        from app.models.user import User
        allowed = set(User.PERMISSION_CATALOG)
        bad = [x for x in v if x not in allowed]
        if bad:
            raise ValueError(f"未知权限：{','.join(bad)}")
        return v


class UserProfileResponse(BaseModel):
    id: int
    uid: str | None = None
    username: str
    nickname: str
    avatar: str | None
    cover_image: str | None = None
    bio: str | None
    gender: str = "unknown"
    grade: str | None = None
    college: str | None = None
    major: str | None = None
    location: str | None = None
    birthday: str | None = None
    role: str
    perm_tags: list[str] = []
    post_count: int = 0
    like_count: int = 0
    favorite_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    is_following: bool = False
    created_at: datetime
    model_config = {"from_attributes": True}


class FollowUser(BaseModel):
    """关注/粉丝/推荐列表中的精简用户结构"""
    id: int
    nickname: str
    avatar: str | None = None
    bio: str | None = None
    role: str = "user"
    perm_tags: list[str] = []
    level: int = 1
    is_following: bool = False
    follow_each_other: bool = False
    created_at: datetime | None = None


class UserStats(BaseModel):
    post_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    favorite_count: int = 0
    view_count: int = 0
    completion: int = 0
    followers_count: int = 0
    following_count: int = 0


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
