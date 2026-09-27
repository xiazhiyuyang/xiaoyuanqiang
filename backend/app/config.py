import logging
import secrets as _secrets_mod
import string
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger("campus-wall")

# 项目根目录（backend/app/config.py -> app -> backend -> 根）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
# 旧的占位串：视为不安全
_PLACEHOLDER_SECRET = "change-this-to-a-random-secret-key-in-production"
_WEAK_DEFAULT_ADMIN_PASSWORD = "admin123456"


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "校园墙"
    APP_VERSION: str = "2.0.0"
    # 生产环境务必设为 False：关闭交互式文档、隐藏错误细节
    DEBUG: bool = False
    # 数据库 - 默认 SQLite，切换 MySQL 只需改这里
    # MySQL示例: mysql+aiomysql://user:pass@localhost:3306/campus_wall
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent / 'campus_wall.db'}"
    # JWT：生产必须通过环境变量注入随机密钥（至少 32 位）
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    # 跨域白名单，逗号分隔；默认仅同源。示例：https://wall.example.com,https://admin.example.com
    CORS_ORIGINS: str = ""
    # 初始管理员账号 / 密码：生产部署请通过环境变量覆盖；留空则首次启动自动生成强密码
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""
    # 文件上传（本地 backend/uploads，Docker /app/uploads）
    UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent / "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    # 视频上传
    MAX_VIDEO_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_VIDEO_TYPES: list = ["video/mp4", "video/quicktime", "video/webm"]
    LOG_DIR: Path = Path(__file__).resolve().parent.parent / "logs"
    # 分页
    PAGE_SIZE: int = 20
    # 微信登录（小程序 / 公众号H5）
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_OPEN_APP_ID: str = ""
    WECHAT_OPEN_APP_SECRET: str = ""
    # 站点URL（用于邮件验证链接）
    SITE_URL: str = "https://cy.ihyuan.cn"
    # SMTP邮件服务（邮箱注册验证/密码重置）
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_SSL: bool = True
    SMTP_FROM_NAME: str = "校园墙"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def insecure_secret(self) -> bool:
        return (not self.SECRET_KEY) or self.SECRET_KEY == _PLACEHOLDER_SECRET

    @property
    def weak_admin_password(self) -> bool:
        return (not self.ADMIN_PASSWORD) or self.ADMIN_PASSWORD == _WEAK_DEFAULT_ADMIN_PASSWORD


settings = Settings()


def _update_env_file(key: str, value: str) -> None:
    """在项目根 .env 中追加或更新一行 KEY=VALUE。不存在则创建。"""
    try:
        lines = []
        if _ENV_FILE.exists():
            lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
        new_line = f"{key}={value}"
        replaced = False
        out = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                out.append(new_line)
                replaced = True
            else:
                out.append(line)
        if not replaced:
            out.append(new_line)
        _ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
        try:
            _ENV_FILE.chmod(0o600)
        except OSError:
            pass
    except OSError:
        logger.warning("无法写入 %s（%s=%s），请手动配置", _ENV_FILE, key, value, exc_info=True)


def _generate_strong_password(length: int = 12) -> str:
    """生成随机强密码：必须同时含大写、小写、数字、特殊字符。"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    while True:
        pwd = "".join(_secrets_mod.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pwd)):
            return pwd


def _ensure_secret_key(s) -> None:
    """若 SECRET_KEY 为空或沿用内置占位串（可被预测、进而伪造任意管理员登录态），
    自动生成并持久化一个随机密钥。显式通过环境变量配置时不做任何改动。"""
    if not s.insecure_secret:
        return
    try:
        key_file = Path(__file__).resolve().parent.parent / "data" / ".secret_key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        persisted = key_file.read_text(encoding="utf-8").strip() if key_file.exists() else ""
        if len(persisted) >= 32:
            s.SECRET_KEY = persisted
            return
        new_key = _secrets_mod.token_urlsafe(48)
        key_file.write_text(new_key, encoding="utf-8")
        try:
            key_file.chmod(0o600)
        except OSError:
            pass
        s.SECRET_KEY = new_key
        # 同步写入项目根 .env，避免下次重启又走自动生成分支
        _update_env_file("SECRET_KEY", new_key)
        logger.warning("未配置 SECRET_KEY，已自动生成并持久化随机密钥到 %s", key_file)
    except Exception:
        s.SECRET_KEY = _secrets_mod.token_urlsafe(48)
        logger.warning("无法写入持久化密钥文件，已改用进程内随机 SECRET_KEY", exc_info=True)


def _ensure_admin_password(s) -> None:
    """若 ADMIN_PASSWORD 为空，自动生成随机强密码并打印到日志、写入 .env。"""
    if s.ADMIN_PASSWORD:
        return
    new_pwd = _generate_strong_password(12)
    s.ADMIN_PASSWORD = new_pwd
    _update_env_file("ADMIN_PASSWORD", new_pwd)
    logger.warning("首次启动自动生成管理员密码：%s （已写入 .env，请立即登录并修改）", new_pwd)


_ensure_secret_key(settings)
_ensure_admin_password(settings)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

# 启动期安全自检：把危险配置明确打到服务端日志（不影响启动）
if settings.insecure_secret:
    logger.warning("安全警告：SECRET_KEY 仍为默认值，登录态可被伪造！请设置环境变量 SECRET_KEY")
if settings.weak_admin_password:
    logger.warning("安全警告：管理员密码仍为默认 %s，请设置环境变量 ADMIN_PASSWORD", _WEAK_DEFAULT_ADMIN_PASSWORD)
if settings.DEBUG:
    logger.warning("安全警告：生产环境请勿开启DEBUG模式（DEBUG=True），将暴露交互式文档与错误堆栈")
