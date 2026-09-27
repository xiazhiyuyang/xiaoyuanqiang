import logging
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import select, inspect
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db, AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.user import User
from app.models.post import Category
from app.models.sensitive_word import SensitiveWord
from app.models.promotion import Banner, Announcement
import app.models  # noqa: F401  确保新模型注册到 Base.metadata
from app.api import auth, users, posts, comments, upload, notifications, admin
from app.api import messages, reports, promotions, app_update, review, settings_api, tools, ai_review

logger = logging.getLogger("campus-wall")


def _setup_file_logging():
    """日志同时输出到控制台和按大小轮转的文件。"""
    log_file = settings.LOG_DIR / "app.log"
    handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.setLevel(logging.INFO)
        root.addHandler(handler)


async def init_default_data():
    """初始化默认管理员、分类和敏感词"""
    async with AsyncSessionLocal() as db:
        admin_exists = await db.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        if not admin_exists.scalar_one_or_none():
            db.add(User(
                username=settings.ADMIN_USERNAME,
                nickname="管理员",
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            ))
        default_categories = [
            ("表白墙", "confession", "❤️", 1),
            ("吐槽", "rant", "💢", 2),
            ("提问", "question", "❓", 3),
            ("二手交易", "market", "💰", 4),
            ("失物招领", "lostfound", "🔍", 5),
            ("灌水闲聊", "chat", "💬", 6),
        ]
        for name, slug, icon, sort in default_categories:
            exists = await db.execute(select(Category).where(Category.slug == slug))
            if not exists.scalar_one_or_none():
                db.add(Category(name=name, slug=slug, icon=icon, sort_order=sort))
        default_words = [
            ("傻逼", "abuse", "mask"), ("傻b", "abuse", "mask"), ("煞笔", "abuse", "mask"),
            ("操你", "abuse", "mask"), ("狗东西", "abuse", "mask"),
            ("加微信", "ad", "block"), ("加vx", "ad", "block"), ("兼职刷单", "ad", "block"),
            ("代写论文", "ad", "block"), ("出售答案", "ad", "block"), ("代考", "ad", "block"),
            ("约炮", "porn", "block"), ("裸聊", "porn", "block"),
        ]
        for word, category, action in default_words:
            exists = await db.execute(select(SensitiveWord).where(SensitiveWord.word == word))
            if not exists.scalar_one_or_none():
                db.add(SensitiveWord(word=word, category=category, action=action))
        banner_count = (await db.execute(select(Banner))).scalars().all()
        if not banner_count:
            for title, theme, sort in [
                ("新生指南｜校园生活全攻略", "blue", 30),
                ("二手集市开张，闲置好物换起来", "gold", 20),
                ("社团招新季，找到和你同频的人", "teal", 10),
            ]:
                db.add(Banner(title=title, theme=theme, sort_order=sort))
        ann_count = (await db.execute(select(Announcement))).scalars().all()
        if not ann_count:
            for content, sort in [
                ("欢迎来到校园墙，发帖请遵守社区公约，友善交流～", 20),
                ("失物招领、二手交易请选择对应分类，信息触达更高效", 10),
            ]:
                db.add(Announcement(content=content, sort_order=sort))
        await db.commit()


async def migrate_db():
    """旧库轻量迁移：补齐新版本字段（SQLite/MySQL 通用）"""
    async with engine.begin() as conn:
        def _add_missing(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            if "users" in tables:
                cols = {c["name"] for c in insp.get_columns("users")}
                user_columns = {
                    "wechat_openid": "VARCHAR(64)",
                    "gender": "VARCHAR(16) DEFAULT 'unknown'",
                    "grade": "VARCHAR(32)",
                    "college": "VARCHAR(64)",
                    "major": "VARCHAR(64)",
                    "location": "VARCHAR(64)",
                    "birthday": "VARCHAR(10)",
                    "privacy": "TEXT",
                    "exp": "INTEGER DEFAULT 0",
                    "level": "INTEGER DEFAULT 1",
                    "permissions": "TEXT DEFAULT ''",
                    "security_question": "VARCHAR(100)",
                    "security_answer_hash": "VARCHAR(255)",
                    "last_login_date": "VARCHAR(10)",
                    "agreement_at": "VARCHAR(32)",
                    "preferences": "TEXT",
                    "is_deleted": "BOOLEAN DEFAULT 0",
                    "deleted_at": "VARCHAR(32)",
                    "deletion_requested_at": "VARCHAR(32)",
                    "deletion_scheduled_at": "VARCHAR(32)",
                    "failed_login_count": "INTEGER DEFAULT 0",
                    "locked_until": "VARCHAR(32)",
                    "email": "VARCHAR(128)",
                    "email_verified": "BOOLEAN DEFAULT 0",
                    "need_profile_completion": "BOOLEAN DEFAULT 0",
                }
                for column, ddl_type in user_columns.items():
                    if column not in cols:
                        sync_conn.exec_driver_sql(
                            f"ALTER TABLE users ADD COLUMN {column} {ddl_type}"
                        )
            if "posts" in tables:
                cols = {c["name"] for c in insp.get_columns("posts")}
                if "video_url" not in cols:
                    sync_conn.exec_driver_sql(
                        "ALTER TABLE posts ADD COLUMN video_url VARCHAR(500)"
                    )

            def _ensure_columns(table: str, spec: dict):
                if table not in insp.get_table_names():
                    return
                existing = {c["name"] for c in insp.get_columns(table)}
                for column, ddl_type in spec.items():
                    if column not in existing:
                        sync_conn.exec_driver_sql(
                            f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"
                        )

            _ensure_columns("ai_review_records", {
                "requested_action": "VARCHAR(20) DEFAULT 'pass'",
                "latency_ms": "INTEGER DEFAULT 0",
                "evidence": "TEXT",
                "dry_run": "BOOLEAN DEFAULT 0",
                "masked_content": "TEXT",
                "author_stats": "TEXT",
            })
            _ensure_columns("ai_review_config", {
                "dry_run": "BOOLEAN DEFAULT 0",
                "local_enabled": "BOOLEAN DEFAULT 1",
                "scope_post": "BOOLEAN DEFAULT 1",
                "scope_comment": "BOOLEAN DEFAULT 1",
                "scope_message": "BOOLEAN DEFAULT 1",
                "scope_profile": "BOOLEAN DEFAULT 0",
                "llm_trigger": "VARCHAR(20) DEFAULT 'off'",
                "llm_min_score": "INTEGER DEFAULT 60",
                "llm_sample_rate": "INTEGER DEFAULT 10",
                "llm_timeout": "INTEGER DEFAULT 15",
                "llm_max_len": "INTEGER DEFAULT 2000",
                "llm_daily_limit": "INTEGER DEFAULT 0",
                "image_api_user": "VARCHAR(200) DEFAULT ''",
                "image_api_url": "VARCHAR(500) DEFAULT ''",
                "block_score": "INTEGER DEFAULT 80",
                "review_score": "INTEGER DEFAULT 50",
                "mask_score": "INTEGER DEFAULT 30",
                "auto_ban_threshold": "INTEGER DEFAULT 0",
                "notify_author": "BOOLEAN DEFAULT 1",
                "exempt_staff": "BOOLEAN DEFAULT 0",
            })

            # ---- 设备与封禁表 ----
            sync_conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    device_code VARCHAR(64) NOT NULL,
                    device_name VARCHAR(128),
                    platform VARCHAR(32),
                    ip VARCHAR(64),
                    ip_location VARCHAR(128),
                    user_agent TEXT,
                    last_login_at DATETIME,
                    login_count INTEGER DEFAULT 1,
                    is_trusted BOOLEAN DEFAULT 0,
                    created_at DATETIME
                )
            """)
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_devices_user_id ON devices(user_id)")
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_devices_device_code ON devices(device_code)")
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_devices_ip ON devices(ip)")

            sync_conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS ip_bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip VARCHAR(64) NOT NULL UNIQUE,
                    reason VARCHAR(500),
                    banned_by INTEGER,
                    banned_by_name VARCHAR(32),
                    expires_at VARCHAR(32),
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME
                )
            """)
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_ip_bans_ip ON ip_bans(ip)")
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_ip_bans_is_active ON ip_bans(is_active)")

            sync_conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS device_bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_code VARCHAR(64) NOT NULL UNIQUE,
                    reason VARCHAR(500),
                    banned_by INTEGER,
                    banned_by_name VARCHAR(32),
                    expires_at VARCHAR(32),
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME
                )
            """)
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_device_bans_device_code ON device_bans(device_code)")
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_device_bans_is_active ON device_bans(is_active)")

            # ---- 封禁表字段升级（指纹哈希、CIDR、递增封禁、自动封禁）----
            alter_statements = [
                "ALTER TABLE devices ADD COLUMN fingerprint_hash VARCHAR(32)",
                "ALTER TABLE ip_bans ADD COLUMN is_cidr BOOLEAN DEFAULT 0",
                "ALTER TABLE ip_bans ADD COLUMN ban_count INTEGER DEFAULT 1",
                "ALTER TABLE ip_bans ADD COLUMN auto_banned BOOLEAN DEFAULT 0",
                "ALTER TABLE device_bans ADD COLUMN fingerprint_hash VARCHAR(32)",
            ]
            for stmt in alter_statements:
                try:
                    sync_conn.exec_driver_sql(stmt)
                except Exception:
                    pass  # 字段已存在时忽略
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_devices_fingerprint_hash ON devices(fingerprint_hash)")
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_device_bans_fingerprint_hash ON device_bans(fingerprint_hash)")

            # ---- IP白名单表 ----
            sync_conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS ip_whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip VARCHAR(64) NOT NULL UNIQUE,
                    remark VARCHAR(200),
                    created_by INTEGER,
                    created_at DATETIME
                )
            """)

            # ---- 登录失败记录表（自动封禁用，参考 fail2ban 滑动窗口）----
            sync_conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS login_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip VARCHAR(64) NOT NULL,
                    username VARCHAR(64),
                    device_code VARCHAR(128),
                    fingerprint_hash VARCHAR(32),
                    reason VARCHAR(100),
                    created_at DATETIME
                )
            """)
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_login_failures_ip ON login_failures(ip)")
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_login_failures_created_at ON login_failures(created_at)")

            # 邮箱验证表
            sync_conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS email_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(128) NOT NULL,
                    token VARCHAR(128) NOT NULL,
                    scene VARCHAR(20) DEFAULT 'register',
                    user_id INTEGER,
                    used INTEGER DEFAULT 0,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME
                )
            """)
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_email_verifications_email ON email_verifications(email)")
            sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_email_verifications_token ON email_verifications(token)")

            # ---- 性能索引补齐（CREATE INDEX IF NOT EXISTS 对已有库幂等）----
            index_statements = [
                # users：按角色/封禁筛选
                "CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)",
                "CREATE INDEX IF NOT EXISTS ix_users_is_banned ON users(is_banned)",
                # posts：个人主页按作者+时间
                "CREATE INDEX IF NOT EXISTS idx_posts_user_created ON posts(user_id, created_at)",
                # comments：按帖子分页 + 时间索引
                "CREATE INDEX IF NOT EXISTS idx_comments_post_created ON comments(post_id, created_at)",
                "CREATE INDEX IF NOT EXISTS ix_comments_created_at ON comments(created_at)",
                # messages：按会话分页
                "CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at)",
                # notifications：未读筛选 + 时间
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read)",
                "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at)",
                # reports：按状态+时间分页
                "CREATE INDEX IF NOT EXISTS idx_reports_status_created ON reports(status, created_at)",
            ]
            for stmt in index_statements:
                sync_conn.exec_driver_sql(stmt)

        await conn.run_sync(_add_missing)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_file_logging()
    await init_db()
    await migrate_db()
    await init_default_data()
    logger.info("校园墙服务启动完成 version=%s debug=%s", settings.APP_VERSION, settings.DEBUG)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

if settings.DEBUG:
    # 开发模式：放行所有源（App 端 file:// origin 为 null，必须允许）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif settings.cors_origin_list:
    # 生产且已配置白名单：仅放行白名单源，允许携带凭证
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 生产但未配置白名单：只允许同源，不放开任何跨域源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    """维护模式：普通业务接口返回 503，放行登录/管理端/公开配置/健康检查。"""
    path = request.url.path
    if path.startswith("/api/"):
        try:
            from app.core.activity import is_maintenance
            in_maintenance = await is_maintenance()
        except Exception:
            in_maintenance = False
        if in_maintenance:
            allowed = (
                path == "/api/health"
                or path.startswith("/api/admin")
                or path.startswith("/api/auth/login")
                or path.startswith("/api/settings")
            )
            if not allowed:
                return JSONResponse(
                    status_code=503,
                    content={"code": 503, "msg": "系统正在维护升级中，请稍后再试", "data": None},
                )
    return await call_next(request)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    """记录最基础的访问动态与耗时。"""
    start = time.monotonic()
    response = await call_next(request)
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        dur = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %s %.0fms ip=%s",
            request.method, request.url.path, response.status_code, dur,
            request.headers.get("x-forwarded-for", "").split(",")[-1].strip()
            or (request.client.host if request.client else "-"),
        )
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: blob: https:; "
        "media-src 'self' blob: https:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; font-src 'self' data:; object-src 'none'; frame-ancestors 'none'",
    )
    return response


# 统一业务/参数错误结构：前端始终能拿到中文 msg
def _extract_detail(detail) -> str:
    if isinstance(detail, list):
        msgs = []
        for item in detail:
            msg = item.get("msg") if isinstance(item, dict) else str(item)
            if msg:
                msgs.append(str(msg).replace("Value error, ", ""))
        return "；".join(msgs) or "请求参数有误"
    return str(detail)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "msg": _extract_detail(exc.errors()), "data": None},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": _extract_detail(exc.detail), "data": None},
    )


app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(upload.router)
app.include_router(notifications.router)
app.include_router(messages.router)
app.include_router(reports.router)
app.include_router(promotions.router)
app.include_router(app_update.router)
app.include_router(review.router)
app.include_router(settings_api.router)
app.include_router(admin.router)
app.include_router(tools.router)
app.include_router(tools.admin_router)
app.include_router(ai_review.router)
from app.api import stats as stats_api  # noqa: E402
app.include_router(stats_api.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常 %s %s", request.method, request.url.path)
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "msg": f"服务器内部错误: {str(exc)}", "data": None},
        )
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": "服务开小差了，请稍后再试（错误已记录）", "data": None},
    )


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
