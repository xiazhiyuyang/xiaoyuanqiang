from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


# MySQL 使用短连接回收和断线检测，避免宝塔/云数据库 wait_timeout 后连接失效。
engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}
if settings.DATABASE_URL.startswith("mysql"):
    engine_kwargs.update({
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _ensure_columns(sync_conn):
    """轻量幂等加列：老库升级时补齐新增字段（create_all 不会改已存在的表）。"""
    from sqlalchemy import inspect
    insp = inspect(sync_conn)
    # posts.visibility：公开/仅自己
    try:
        cols = {c["name"] for c in insp.get_columns("posts")}
        if "visibility" not in cols:
            sync_conn.execute(text("ALTER TABLE posts ADD COLUMN visibility VARCHAR(10) DEFAULT 'public'"))
    except Exception:
        pass  # 表尚未创建等情况，下一轮启动会再补


async def init_db():
    async with engine.begin() as conn:
        if engine.dialect.name == "mysql":
            await conn.execute(text("SET NAMES utf8mb4"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_columns)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
