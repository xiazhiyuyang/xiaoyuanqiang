from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.security import is_own_media_url


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    icon: str | None
    sort_order: int
    model_config = {"from_attributes": True}


class PostImageResponse(BaseModel):
    id: int
    url: str
    sort_order: int
    model_config = {"from_attributes": True}


class PostCreate(BaseModel):
    title: str = Field(max_length=100)
    content: str = Field(max_length=10000)
    category_id: int | None = None
    is_anonymous: bool = False
    visibility: str = Field("public", description="public=公开 private=仅自己")
    images: list[str] = Field(default_factory=list, max_length=9, description="已上传图片URL列表，最多9张")
    video_url: str | None = Field(None, description="已上传视频URL")

    @field_validator("visibility")
    @classmethod
    def _visibility_ok(cls, v):
        if v not in ("public", "private"):
            raise ValueError("可见范围只能是 public 或 private")
        return v
    @field_validator("images")
    @classmethod
    def _images_safe(cls, v):
        for url in v:
            if not is_own_media_url(url):
                raise ValueError("图片地址不合法")
        return v

    @field_validator("video_url")
    @classmethod
    def _video_safe(cls, v):
        if v and not is_own_media_url(v):
            raise ValueError("视频地址不合法")
        return v

    @model_validator(mode="after")
    def _media_exclusive(self):
        if self.video_url and self.images:
            raise ValueError("视频和图片不能同时发布")
        return self


class PostUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100)
    content: str | None = Field(None, min_length=1, max_length=10000)
    category_id: int | None = None
    is_anonymous: bool | None = None
    visibility: str | None = Field(None, description="public/private")

    @field_validator("visibility")
    @classmethod
    def _visibility_ok(cls, v):
        if v is not None and v not in ("public", "private"):
            raise ValueError("可见范围只能是 public 或 private")
        return v


class PostAuthor(BaseModel):
    id: int
    nickname: str
    avatar: str | None
    level: int = 1
    level_name: str = ""
    level_color: str = ""
    # 社区身份标签：admin=管理员 / content_review=审核员 / report_review=审查员
    role: str = "user"
    staff_tags: list[str] = []
    # 当前浏览者是否已关注该作者（未登录恒为 false）
    is_following: bool = False
    model_config = {"from_attributes": True}


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    is_anonymous: bool
    visibility: str = "public"
    user_id: int | None = None  # 非匿名时的作者ID（匿名时不返回）
    author: PostAuthor | None = None
    author_name: str | None = None  # 匿名时的显示名
    level_badge: dict | None = None  # 发帖人等级徽章 {level,name,color}，匿名也展示
    category: CategoryResponse | None = None
    images: list[PostImageResponse] = []
    video_url: str | None = None
    view_count: int
    like_count: int
    comment_count: int
    is_top: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class PostDetail(PostResponse):
    is_liked: bool = False
    is_favorited: bool = False
    is_owner: bool = False       # 当前登录用户是否为作者（用于显示编辑/删除入口）
    can_edit: bool = False       # 是否有权编辑/删除（作者本人或管理员）
