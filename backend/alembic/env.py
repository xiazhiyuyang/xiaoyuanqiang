"""Alembic 环境配置。

数据库地址来自 app.config.settings.DATABASE_URL（即 .env），
这里只做一件事：把异步驱动名换成对应的同步驱动，因为 Alembic 迁移用同步连接执行。

    sqlite+aiosqlite:///x.db  ->  sqlite:///x.db
    mysql+aiomysql://...      ->  mysql+pymysql://...

这样迁移与运行时永远读同一个地址，不会出现「代码连 A 库、迁移改 B 库」。
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings          # noqa: E402
from app.database import Base            # noqa: E402
import app.models                        # noqa: F401,E402  注册全部模型到 metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sync_url(async_url: str) -> str:
    url = async_url.strip()
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    if url.startswith("mysql+aiomysql"):
        return url.replace("mysql+aiomysql", "mysql+pymysql", 1)
    if url.startswith("mysql+asyncmy"):
        return url.replace("mysql+asyncmy", "mysql+pymysql", 1)
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    return url


config.set_main_option("sqlalchemy.url", _sync_url(settings.DATABASE_URL))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：只输出 SQL，不连库。用于人工审查将要执行的 DDL。"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,   # SQLite 改列需要 batch 模式（重建表）
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        # 注意：这里**不能**在 configure 之前对 connection 执行任何 SQL。
        # SQLAlchemy 2.0 是「commit as you go」语义，先执行一条语句（例如
        # PRAGMA foreign_keys=ON）会开启隐式事务，之后 alembic 的
        # begin_transaction() 会认为自己不拥有该事务而不再提交，
        # 退出 with 块时被整体回滚——表现为「迁移日志显示成功、DDL 生效，
        # 但 alembic_version 始终为空」。（本项目踩过这个坑，勿重蹈。）
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite 不支持大部分 ALTER，必须用 batch 模式（建临时表→拷数据→改名）
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
        # 兜底再提交一次：即使上面的事务代理没有持有提交权，也保证版本号落盘。
        # 对已提交的事务调用 commit() 是无害的空操作。
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
