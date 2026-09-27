"""SQLite → MySQL 数据迁移脚本。

用法（在 backend 目录）：

    DATABASE_URL='mysql+aiomysql://user:password@127.0.0.1:3306/campus_wall?charset=utf8mb4' \
    SQLITE_PATH='/www/wwwroot/campus-wall/data/campus_wall.db' \
    python scripts/migrate_sqlite_to_mysql.py

可选：RESET_TARGET=1 表示先清空目标库再导入（危险操作，仅首次迁移使用）。
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  # 注册全部模型


DEFAULT_SQLITE = BACKEND_DIR.parent / "data" / "campus_wall.db"


def mysql_sync_url(database: str | None = None) -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        raise SystemExit("请先设置 DATABASE_URL，例如 mysql+aiomysql://user:pass@host/db?charset=utf8mb4")
    url = make_url(raw)
    if not url.drivername.startswith("mysql"):
        raise SystemExit(f"DATABASE_URL 不是 MySQL：{url.drivername}")
    drivername = "mysql+pymysql"
    password = quote_plus(url.password) if url.password else ""
    auth = url.username or ""
    if password:
        auth += f":{password}"
    if auth:
        auth += "@"
    port = f":{url.port}" if url.port else ""
    db = f"/{database}" if database else "/"
    query = "?charset=utf8mb4"
    return f"{drivername}://{auth}{url.host}{port}{db}{query}"


def ensure_database(url):
    db_name = url.database
    if not db_name:
        raise SystemExit("DATABASE_URL 中必须包含数据库名")
    server_engine = create_engine(mysql_sync_url(None), future=True)
    try:
        with server_engine.begin() as conn:
            conn.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
        print(f"[ok] 数据库 `{db_name}` 已就绪")
    finally:
        server_engine.dispose()


def normalize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return value


def main():
    sqlite_path = Path(os.getenv("SQLITE_PATH", str(DEFAULT_SQLITE))).expanduser()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite 文件不存在：{sqlite_path}")

    target_url = make_url(os.getenv("DATABASE_URL", "").strip())
    ensure_database(target_url)
    target_engine = create_engine(mysql_sync_url(target_url.database), future=True)
    reset_target = os.getenv("RESET_TARGET", "") == "1"

    source_engine = create_engine(f"sqlite:///{sqlite_path}", future=True)

    src_inspector = inspect(source_engine)
    src_tables = set(src_inspector.get_table_names())

    try:
        with source_engine.connect() as source, target_engine.begin() as target:
            target.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            Base.metadata.create_all(target)

            if reset_target:
                for table in reversed(Base.metadata.sorted_tables):
                    target.execute(table.delete())
                print("[ok] 已清空目标库旧数据")

            for table in Base.metadata.sorted_tables:
                if table.name not in src_tables:
                    print(f"[skip] {table.name}: SQLite 中不存在")
                    continue

                existing = target.execute(text(f"SELECT COUNT(*) FROM `{table.name}`")).scalar()
                if existing:
                    raise SystemExit(f"目标表 `{table.name}` 已有 {existing} 行；确认覆盖请设置 RESET_TARGET=1")

                src_cols = [column["name"] for column in src_inspector.get_columns(table.name)]
                dst_cols = {column.name for column in table.columns}
                columns = [c for c in src_cols if c in dst_cols]
                if not columns:
                    continue

                result = source.execute(text(f"SELECT {', '.join(columns)} FROM {table.name}"))
                rows = [
                    {col: normalize(row[col]) for col in columns}
                    for row in result.mappings()
                ]
                if rows:
                    target.execute(table.insert(), rows)
                print(f"[ok] {table.name}: 导入 {len(rows)} 行")

            target.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    finally:
        source_engine.dispose()
        target_engine.dispose()

    print("迁移完成。请检查应用 .env 的 DATABASE_URL 后重启服务。")


if __name__ == "__main__":
    main()
