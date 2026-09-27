from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.security import is_safe_link


def _safe_link(v):
    v = (v or "").strip() or None
    if v and not is_safe_link(v):
        raise ValueError("链接仅支持 /pages/ 站内地址或 http(s) 外链")
    return v


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    slug: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9\-]+$")
    icon: str | None = Field(None, max_length=8)
    sort_order: int = Field(0, ge=0, le=9999)


class SensitiveWordCreate(BaseModel):
    word: str = Field(min_length=1, max_length=50)
    category: str = Field("other", max_length=20)
    action: str = Field("mask", pattern="^(mask|block)$")
    is_enabled: bool = True


class SensitiveWordUpdate(BaseModel):
    word: str | None = Field(None, min_length=1, max_length=50)
    category: str | None = Field(None, max_length=20)
    action: str | None = Field(None, pattern="^(mask|block)$")
    is_enabled: bool | None = None


class SensitiveWordBatch(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    category: str = Field("other", max_length=20)
    action: str = Field("mask", pattern="^(mask|block)$")


class BannerCreate(BaseModel):
    title: str = Field(min_length=1, max_length=30)
    image_url: str | None = Field(None, max_length=500)
    link_url: str | None = Field(None, max_length=500)
    theme: str = Field("blue", pattern="^(blue|teal|gold|ink)$")
    sort_order: int = Field(0, ge=0, le=9999)
    is_active: bool = True

    _link = field_validator("link_url")(staticmethod(_safe_link))


class BannerUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=30)
    image_url: str | None = Field(None, max_length=500)
    link_url: str | None = Field(None, max_length=500)
    theme: str | None = Field(None, pattern="^(blue|teal|gold|ink)$")
    sort_order: int | None = Field(None, ge=0, le=9999)
    is_active: bool | None = None

    _link = field_validator("link_url")(staticmethod(_safe_link))


class AnnouncementCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100)
    link_url: str | None = Field(None, max_length=500)
    sort_order: int = Field(0, ge=0, le=9999)
    is_active: bool = True

    _link = field_validator("link_url")(staticmethod(_safe_link))


class AnnouncementUpdate(BaseModel):
    content: str | None = Field(None, min_length=1, max_length=100)
    link_url: str | None = Field(None, max_length=500)
    sort_order: int | None = Field(None, ge=0, le=9999)
    is_active: bool | None = None

    _link = field_validator("link_url")(staticmethod(_safe_link))


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(user|admin)$")


class AdminUserProfileUpdate(BaseModel):
    """管理员修改用户个人资料。所有字段可选，只更新传入的非 None 字段。"""
    nickname: str | None = Field(None, min_length=1, max_length=32)
    bio: str | None = Field(None, max_length=200)
    gender: str | None = Field(None, pattern=r"^(unknown|male|female)$")
    grade: str | None = Field(None, max_length=32)
    college: str | None = Field(None, max_length=64)
    major: str | None = Field(None, max_length=64)
    location: str | None = Field(None, max_length=64)
    avatar: str | None = Field(None, max_length=500)
    cover_image: str | None = Field(None, max_length=500)


class AdminResetPassword(BaseModel):
    """管理员重置用户密码。不填 new_password 则生成 8 位随机密码。"""
    new_password: str | None = Field(None, min_length=6, max_length=64)


_SETTINGS_ENUM_WHITELIST = {
    "notice_mode": {"marquee", "vertical", "static"},
    "review_mode": {"off", "random", "all"},
    "default_theme": {"galaxy", "ocean", "forest", "sunset", "rose", "midnight"},
}


class SettingsUpdate(BaseModel):
    # 基础
    site_name: str | None = Field(None, min_length=1, max_length=30)
    site_slogan: str | None = Field(None, max_length=60)
    contact: str | None = Field(None, max_length=100)
    footer_note: str | None = Field(None, max_length=200)
    # 品牌与前台文案
    site_logo: str | None = Field(None, max_length=500)
    home_subtitle: str | None = Field(None, max_length=60)
    brand_sub: str | None = Field(None, max_length=60)
    publish_text: str | None = Field(None, max_length=12)
    notice_mode: str | None = Field(None, max_length=12)  # 白名单见 _enum_fallback
    # 备案信息
    icp_number: str | None = Field(None, max_length=60)
    icp_link: str | None = Field(None, max_length=200)
    police_number: str | None = Field(None, max_length=60)
    police_link: str | None = Field(None, max_length=200)
    # 注册与访问
    allow_register: bool | None = None
    maintenance: bool | None = None
    # 内容审核
    post_need_review: bool | None = None  # 兼容旧开关
    review_mode: str | None = Field(None, max_length=12)  # 白名单见 _enum_fallback
    review_random_rate: int | None = Field(None, ge=0, le=100)
    # 外观与功能
    default_theme: str | None = Field(None, max_length=20)  # 白名单见 _enum_fallback
    allow_anonymous: bool | None = None
    allow_video: bool | None = None
    message_open: bool | None = None
    show_level: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _blank_to_none(cls, values):
        # 纯空白字符串（全是空格/tab，长度>0）视为"不修改该字段"；
        # 空字符串 "" 保留，允许用户主动清空字段（如页脚备注、备案号等）。
        if isinstance(values, dict):
            return {
                k: (None if isinstance(x, str) and len(x) > 0 and not x.strip() else x)
                for k, x in values.items()
            }
        return values

    @field_validator("notice_mode", "review_mode", "default_theme")
    @classmethod
    def _enum_fallback(cls, v, info):
        # 空值放行（不更新）；非白名单的非法值同样置 None，绝不让单个枚举字段阻断整页设置保存
        if v is None:
            return None
        v = v.strip()
        allowed = _SETTINGS_ENUM_WHITELIST.get(info.field_name, set())
        return v if v in allowed else None


class AppUpdateConfig(BaseModel):
    """App 整包 APK 冷更新配置（写入 app-update.json）。"""
    enabled: bool = False
    latest_version: str = Field("1.0.0", max_length=20)
    version_code: int = Field(100, ge=1, le=999999)
    required: bool = False
    changelog: str | None = Field(None, max_length=1000)
    apk_url: str | None = Field(None, max_length=500)

    @field_validator("latest_version")
    @classmethod
    def _version(cls, v):
        import re
        if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){0,2}", v or ""):
            raise ValueError("版本号格式应为 x.y.z，如 1.0.2")
        return v

    @field_validator("apk_url")
    @classmethod
    def _url(cls, v):
        v = (v or "").strip() or None
        if v and not (v.startswith("/uploads/") or v.startswith("http://") or v.startswith("https://")):
            raise ValueError("更新包地址需为 /uploads/ 相对路径或 http(s) 链接")
        return v
