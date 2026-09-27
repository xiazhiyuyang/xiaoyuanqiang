from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str | None] = mapped_column(String(8), unique=True, nullable=True, index=True, comment="社区UID号，5位数字")
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="登录名")
    nickname: Mapped[str] = mapped_column(String(32), comment="昵称")
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="头像URL")
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="个人主页封面图URL")
    bio: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="简介")
    gender: Mapped[str] = mapped_column(String(16), default="unknown", comment="unknown/male/female")
    grade: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="年级")
    college: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="学院")
    major: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="专业")
    location: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="所在地/校区")
    birthday: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="生日 YYYY-MM-DD")
    student_id: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="学号")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True, comment="邮箱")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="邮箱是否已验证")
    # 第三方登录后是否需要完善资料（设置密码等）
    need_profile_completion: Mapped[bool] = mapped_column(Boolean, default=False, comment="第三方登录后需完善资料")
    # 资料可见范围：JSON 字符串，键 gender/school/location/birthday/contact，值 public/members/private
    privacy: Mapped[str | None] = mapped_column(Text, nullable=True, comment="资料可见范围JSON")
    # 个人偏好：JSON 字符串（配色主题/明暗模式/四类通知开关）
    preferences: Mapped[str | None] = mapped_column(Text, nullable=True, comment="个人偏好JSON")
    wechat_openid: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True, comment="微信openid")
    role: Mapped[str] = mapped_column(String(16), default="user", index=True, comment="user/admin")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # 软删除：True 表示账号已被注销（保留数据但不可登录/不可见）
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, comment="是否已软删除")
    deleted_at: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="注销时间 ISO")
    # 账号注销冷静期：提交申请后7天冷静期，到期自动执行注销；期间可撤销
    deletion_requested_at: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="注销申请时间 ISO")
    deletion_scheduled_at: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="计划注销时间 ISO（申请后7天）")
    # 登录失败计数与锁定（连续失败 5 次锁定 15 分钟）
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, comment="连续登录失败次数")
    locked_until: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="锁定截止时间 ISO")
    # 经验等级
    exp: Mapped[int] = mapped_column(Integer, default=0, comment="经验值")
    level: Mapped[int] = mapped_column(Integer, default=1, comment="等级（由exp重算的快照）")
    # 细粒度授权（逗号分隔的权限 key）；管理员默认拥有全部，但授权用户不等于管理员
    permissions: Mapped[str] = mapped_column(Text, default="", comment="被授予的单项权限，逗号分隔")
    # 找回密码密保
    security_question: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="密保问题")
    security_answer_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="密保答案哈希")
    last_login_date: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="最近登录日期，用于每日经验")
    # 隐私政策/用户协议同意时间（ISO 字符串）；未同意不允许注册
    agreement_at: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="同意隐私协议的时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # 细粒度权限目录（新增权限在此登记）
    PERMISSION_CATALOG = {
        "stats_view": "数据概览（查看统计看板与趋势）",
        "user_manage": "用户管理（查看/封禁/编辑用户资料）",
        "post_manage": "帖子管理（置顶/审核/删除/恢复帖子）",
        "comment_manage": "评论管理（查看/删除评论）",
        "content_review": "内容审查（帖子+评论审核快捷权限）",
        "report_review": "举报审核（查看/处理用户举报）",
        "sensitive_word": "敏感词管理（增删改敏感词）",
        "category_manage": "分类管理（增删帖子分类）",
        "ad_manage": "广告与公告（Banner/公告管理）",
        "operation_log": "操作日志（只读查看管理员操作记录）",
    }

    @property
    def permission_list(self) -> list[str]:
        if not self.permissions:
            return []
        return [p.strip() for p in self.permissions.split(",") if p.strip()]

    def has_permission(self, key: str) -> bool:
        """管理员拥有全部权限；普通用户仅在被单独授权时拥有对应权限，且不获得任何其他管理员能力。"""
        if self.role == "admin":
            return True
        return key in self.permission_list

    posts: Mapped[list["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="author", cascade="all, delete-orphan",
        foreign_keys="Comment.user_id",
    )


def staff_tags_of(user: "User") -> list[str]:
    """社区身份标签（用于前端展示审核员/审查员/管理员标志）。
    管理员只展示管理员；被细粒度授权的普通用户展示对应身份。"""
    if not user:
        return []
    if user.role == "admin":
        return ["admin"]
    tags = []
    perms = user.permission_list
    if "content_review" in perms:
        tags.append("content_review")
    if "report_review" in perms:
        tags.append("report_review")
    return tags
