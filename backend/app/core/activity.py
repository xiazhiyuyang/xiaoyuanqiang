"""操作日志 / 站点配置 / 资料可见范围 等公共能力。"""
import json
import logging

from fastapi import Request

from app.database import AsyncSessionLocal
from app.models.operation_log import OperationLog
from app.models.site_setting import SiteSetting

logger = logging.getLogger("campus-wall")

# 动作中文标签（后台日志页展示用）
ACTION_LABELS = {
    "register": "注册账号",
    "login": "登录成功",
    "login_failed": "登录失败",
    "logout": "退出登录",
    "post_create": "发布帖子",
    "post_delete": "删除自己的帖子",
    "comment_create": "发表评论",
    "message_send": "发送私信",
    "report_create": "提交举报",
    "admin_login": "后台登录",
    "admin_user_ban": "封禁/解封用户",
    "admin_user_role": "修改用户角色",
    "admin_post_delete": "后台删除帖子",
    "admin_post_restore": "恢复帖子",
    "admin_post_review": "帖子审核",
    "admin_comment_delete": "删除评论",
    "admin_report_handle": "处理举报",
    "admin_setting_update": "修改站点设置",
}


def client_ip(request: Request | None) -> str:
    """取可信对端 IP：X-Forwarded-For 最右一段（最近一跳可信代理写入）。"""
    if request is None:
        return ""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        chain = [p.strip() for p in fwd.split(",") if p.strip()]
        if chain:
            return chain[-1][:64]
    return (request.client.host if request.client else "")[:64]


async def log_action(
    *,
    user_id: int | None = None,
    username: str | None = None,
    action: str = "",
    target_type: str | None = None,
    target_id=None,
    detail: str = "",
    request: Request | None = None,
    ip: str = "",
    status: str = "success",
) -> None:
    """记录一条操作日志。使用独立事务，业务回滚不影响日志落库。"""
    try:
        async with AsyncSessionLocal() as db:
            db.add(OperationLog(
                user_id=user_id,
                username=(username or "")[:64],
                action=action[:48],
                target_type=target_type,
                target_id=str(target_id) if target_id is not None else None,
                detail=(detail or "")[:500],
                ip=ip or client_ip(request),
                user_agent=(request.headers.get("user-agent", "")[:255] if request else None),
                status=status,
            ))
            await db.commit()
    except Exception:  # 日志失败绝不能影响主流程
        logger.warning("操作日志写入失败 action=%s", action, exc_info=True)


# ---------------- 站点配置 ----------------

SETTING_DEFAULTS = {
    # 基础
    "site_name": "校园墙",
    "site_slogan": "",            # 站点标语/一句话介绍
    "contact": "",                # 联系方式（邮箱/QQ群等，展示在设置页）
    "footer_note": "",            # 页脚备注/补充说明
    # 品牌与前台文案（后台可改，三端动态读取）
    "site_logo": "",              # 站点 Logo 图片 URL（方形 PNG，用于品牌位/favicon）
    "home_subtitle": "来看看同学们在聊什么",  # 首页问候语后半句
    "brand_sub": "分享校园生活每一刻",        # 品牌位一句话副标题
    "publish_text": "发布",       # 首页发布按钮文案
    "notice_mode": "marquee",     # 公告展示：marquee=横向跑马灯/vertical=逐条轮播/static=静止
    # 备案信息（页脚展示，可点跳转）
    "icp_number": "",             # ICP 备案号，如 粤ICP备xxxx号
    "icp_link": "https://beian.miit.gov.cn/",
    "police_number": "",          # 公安备案号，如 粤公网安备xxxx号
    "police_link": "https://beian.mps.gov.cn/",
    # 注册与访问
    "allow_register": "1",        # 1 开放注册 / 0 关闭注册
    "maintenance": "0",           # 1 维护模式（仅管理员可访问接口）
    # 内容审核
    "post_need_review": "0",      # 旧开关（兼容）：1 时等同全部审核
    "review_mode": "off",         # off=免审 / random=随机抽查 / all=全部先审
    "review_random_rate": "20",   # 随机抽查比例（0-100）
    # 外观与功能
    "default_theme": "galaxy",    # App 默认主题
    "allow_anonymous": "1",       # 是否允许匿名发帖
    "allow_video": "1",           # 是否允许发布视频
    "message_open": "1",          # 是否开放私信
    "show_level": "1",            # 是否展示等级徽章
}
# 允许 App 端匿名获取的公开配置白名单（绝不含敏感项）
PUBLIC_SETTING_KEYS = (
    "site_name", "site_slogan", "contact", "footer_note",
    "site_logo", "home_subtitle", "brand_sub", "publish_text", "notice_mode",
    "icp_number", "icp_link", "police_number", "police_link",
    "allow_register", "maintenance", "default_theme",
    "allow_anonymous", "allow_video", "message_open", "show_level",
)
_BOOL_KEYS = (
    "allow_register", "maintenance", "allow_anonymous", "allow_video",
    "message_open", "show_level",
)
VALID_THEMES = ("galaxy", "ocean", "forest", "sunset", "rose", "midnight")
_setting_cache: dict | None = None


async def _load_settings_from_db() -> dict:
    global _setting_cache
    data = dict(SETTING_DEFAULTS)
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select_all_settings())).scalars().all()
            for row in rows:
                data[row.key] = row.value if row.value is not None else ""
    except Exception:
        logger.warning("站点配置读取失败，使用默认值", exc_info=True)
    _setting_cache = data
    return data


def select_all_settings():
    from sqlalchemy import select
    return select(SiteSetting)


async def get_settings() -> dict:
    if _setting_cache is None:
        return await _load_settings_from_db()
    return dict(_setting_cache)


async def get_setting(key: str) -> str:
    data = await get_settings()
    return data.get(key, SETTING_DEFAULTS.get(key, ""))


async def is_register_open() -> bool:
    return (await get_setting("allow_register")) != "0"


async def post_need_review() -> bool:
    return (await get_setting("post_need_review")) == "1"


async def update_settings(db, changes: dict) -> dict:
    for key, value in changes.items():
        if key not in SETTING_DEFAULTS:
            continue
        row = await db.get(SiteSetting, key)
        value = "" if value is None else str(value)
        if row:
            row.value = value
        else:
            db.add(SiteSetting(key=key, value=value))
    await db.commit()
    global _setting_cache
    _setting_cache = None
    return await get_settings()


# ---------------- 资料可见范围 ----------------
async def is_maintenance() -> bool:
    return (await get_setting("maintenance")) == "1"


async def get_review_policy() -> dict:
    """发帖审核策略。兼容旧 post_need_review 开关。

    返回 {"mode": "off/random/all", "rate": int}
    """
    data = await get_settings()
    if data.get("post_need_review") == "1":
        mode = "all"
    else:
        mode = data.get("review_mode", "off")
        if mode not in ("off", "random", "all"):
            mode = "off"
    try:
        rate = int(float(data.get("review_random_rate", 20)))
    except (TypeError, ValueError):
        rate = 20
    rate = max(0, min(100, rate))
    return {"mode": mode, "rate": rate}


async def feature_on(key: str, default: bool = True) -> bool:
    """读取功能开关（allow_anonymous/allow_video/message_open/show_level）。"""
    val = await get_setting(key)
    if val == "":
        return default
    return val == "1"


async def public_app_settings() -> dict:
    """供 App 匿名拉取的公开配置（白名单），并做类型转换。"""
    data = await get_settings()
    result = {}
    for key in PUBLIC_SETTING_KEYS:
        val = data.get(key, SETTING_DEFAULTS.get(key, ""))
        if key in _BOOL_KEYS:
            result[key] = val == "1"
        else:
            result[key] = val or ""
    theme = result.get("default_theme") or "galaxy"
    if theme not in VALID_THEMES:
        theme = "galaxy"
    result["default_theme"] = theme
    result["review"] = await get_review_policy()
    return result


async def notify_user(db, user_id: int, title: str, content: str = "",
                      target_id=None, ntype: str = "system", sender_id=None) -> None:
    """向用户写一条站内通知（出现在 App「消息-互动消息」）。"""
    if not user_id:
        return
    from app.models.notification import Notification
    db.add(Notification(
        user_id=user_id, sender_id=sender_id, type=ntype,
        title=title[:100], content=(content or "")[:500], target_id=target_id,
    ))


# ---------------- 资料可见范围 ----------------

DEFAULT_PRIVACY = {
    "gender": "public",
    "school": "public",     # 年级/学院/专业
    "location": "members",
    "birthday": "private",
    "contact": "private",   # 手机/学号，对他人永远不返回
}
PRIVACY_LEVELS = ("public", "members", "private")
PRIVACY_LABELS = {"public": "所有人可见", "members": "仅登录用户可见", "private": "仅自己可见"}


def parse_privacy(raw: str | None) -> dict:
    data = dict(DEFAULT_PRIVACY)
    if raw:
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                for key in DEFAULT_PRIVACY:
                    val = obj.get(key)
                    if val in PRIVACY_LEVELS:
                        data[key] = val
        except (json.JSONDecodeError, TypeError):
            pass
    return data


def can_view(level: str, viewer, is_self: bool) -> bool:
    """viewer: 当前查看者 User|None；is_self 是否查看自己。"""
    if is_self:
        return True
    if level == "public":
        return True
    if level == "members":
        return viewer is not None
    return False

# ---------------- 用户个人偏好（主题 / 明暗模式 / 通知开关） ----------------
DEFAULT_PREFERENCES = {
    "theme": "galaxy",       # 配色主题，取值见 VALID_THEMES
    "mode": "dark",          # 显示模式：dark 深色 / light 浅色 / auto 跟随系统
    "notify_like": True,     # 点赞通知
    "notify_comment": True,  # 评论/回复通知
    "notify_follow": True,   # 关注通知
    "notify_system": True,   # 系统通知
}
_VALID_MODES = ("dark", "light", "auto")
_NOTIFY_KEY_MAP = {
    "like": "notify_like",
    "comment": "notify_comment",
    "follow": "notify_follow",
    "system": "notify_system",
}

def parse_preferences(raw: str | dict | None) -> dict:
    """读取用户偏好，缺失项用默认值补齐，非法值忽略。"""
    data = dict(DEFAULT_PREFERENCES)
    obj = raw
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            obj = None
    if isinstance(obj, dict):
        if obj.get("theme") in VALID_THEMES:
            data["theme"] = obj["theme"]
        if obj.get("mode") in _VALID_MODES:
            data["mode"] = obj["mode"]
        for key in ("notify_like", "notify_comment", "notify_follow", "notify_system"):
            if isinstance(obj.get(key), bool):
                data[key] = obj[key]
    return data

def sanitize_preferences(obj: dict | None) -> dict:
    """写入前白名单过滤，只保留合法键与合法值。"""
    if not isinstance(obj, dict):
        raise ValueError("个人偏好格式不正确")
    clean = {}
    if "theme" in obj and obj["theme"] in VALID_THEMES:
        clean["theme"] = obj["theme"]
    if "mode" in obj and obj["mode"] in _VALID_MODES:
        clean["mode"] = obj["mode"]
    for key in ("notify_like", "notify_comment", "notify_follow", "notify_system"):
        if key in obj and isinstance(obj[key], bool):
            clean[key] = obj[key]
    return clean

async def user_notify_on(db, user_id: int, ntype: str) -> bool:
    """接收方是否开启了该类通知（默认开启；用户不存在时不发）。"""
    key = _NOTIFY_KEY_MAP.get(ntype)
    if not key or not user_id:
        return False
    from app.models.user import User
    target = await db.get(User, user_id)
    if not target:
        return False
    return parse_preferences(target.preferences).get(key, True)
