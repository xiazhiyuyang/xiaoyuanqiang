#!/usr/bin/env python3
"""清理 uploads 目录下的孤儿文件。

背景：帖子删除是软删（status='deleted'），头像/帖子图更换后旧文件也不会被移除，
代码里没有任何 unlink/os.remove，磁盘只增不减。实测改造前 8 张图片中已有 2 张孤儿。

策略（保守优先，宁可不删也不要误删）：
1. 收集数据库中所有被引用的媒体路径：post_images.url、users.avatar、
   site_settings 里的 site_logo、banners.image_url、posts.video_url；
2. 扫描 uploads 目录下的实际文件（APK 目录 app/ 单独处理，不按引用判断）；
3. 只删除「未被任何记录引用」且「mtime 早于宽限期」的文件；
4. 默认 --dry-run，必须显式加 --apply 才真的删除。

APK 目录（uploads/app）不按引用清理，改为按文件名版本号保留最新 KEEP_APK 个，
其余移动到归档目录而不是删除——历史版本可能需要给老用户提供下载。

用法：
    python scripts/cleanup_orphan_uploads.py            # 只报告，不删除
    python scripts/cleanup_orphan_uploads.py --apply    # 实际清理
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_DB = PROJECT_DIR / "data" / "campus_wall.db"
ARCHIVE_DIR = Path("/root/campus_releases/apk_archive")

# 宽限期：新上传但尚未提交发帖的图片不能被当成孤儿删掉
GRACE_SECONDS = 7 * 24 * 3600
KEEP_APK = 2

_APK_RE = re.compile(r"(\d+)\.apk$", re.IGNORECASE)


def _collect_referenced(db_path: Path) -> set[str]:
    """从数据库收集所有被引用的 /uploads/... 路径。"""
    refs: set[str] = set()
    if not db_path.exists():
        raise SystemExit(f"数据库不存在：{db_path}")

    # 优先按 .env 的 DATABASE_URL 判断，这里只处理 SQLite（MySQL 场景请改用 --refs-file）
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    queries = [
        "SELECT url FROM post_images WHERE url IS NOT NULL",
        "SELECT avatar FROM users WHERE avatar IS NOT NULL",
        "SELECT video_url FROM posts WHERE video_url IS NOT NULL",
        "SELECT image_url FROM banners WHERE image_url IS NOT NULL",
        "SELECT value FROM site_settings WHERE key IN ('site_logo') AND value IS NOT NULL",
    ]
    for sql in queries:
        try:
            for (value,) in conn.execute(sql):
                if isinstance(value, str) and value.startswith("/uploads/"):
                    refs.add(value.strip())
        except sqlite3.Error:
            # 表不存在（老库）时跳过，不能因此中断整个清理
            continue
    conn.close()
    return refs


def _scan_disk(upload_dir: Path) -> list[Path]:
    files: list[Path] = []
    for root, _dirs, names in os.walk(upload_dir):
        for name in names:
            if name in (".gitkeep",):
                continue
            files.append(Path(root) / name)
    return files


def _apk_version(path: Path) -> tuple[int, int]:
    """从文件名解析 (versionCode, mtime)，用于保留最新版本。"""
    m = _APK_RE.search(path.name)
    code = int(m.group(1)) if m else 0
    return (code, int(path.stat().st_mtime))


def main() -> int:
    parser = argparse.ArgumentParser(description="清理 uploads 孤儿文件")
    parser.add_argument("--apply", action="store_true", help="实际删除/归档（默认只报告）")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite 数据库路径")
    parser.add_argument("--upload-dir", default=str(BACKEND_DIR / "uploads"), help="uploads 目录")
    parser.add_argument("--grace-days", type=int, default=GRACE_SECONDS // 86400,
                        help="宽限期天数，小于该天龄的文件不删")
    parser.add_argument("--keep-apk", type=int, default=KEEP_APK, help="APK 保留最新几个版本")
    args = parser.parse_args()

    upload_dir = Path(args.upload_dir).resolve()
    db_path = Path(args.db).resolve()
    grace = args.grace_days * 86400
    now = time.time()
    mode = "APPLY" if args.apply else "DRY-RUN"

    if not upload_dir.exists():
        print(f"uploads 目录不存在：{upload_dir}")
        return 1

    refs = _collect_referenced(db_path)
    ref_paths = {(upload_dir / r[len("/uploads/"):]).resolve() for r in refs}

    orphans: list[Path] = []
    apks: list[Path] = []
    total_bytes = 0
    for f in _scan_disk(upload_dir):
        total_bytes += f.stat().st_size
        # APK 走版本保留策略，不参与引用判断（下载链接在 app-update.json 里，不在上述表）
        if f.parent.name == "app" and f.suffix.lower() == ".apk":
            apks.append(f)
            continue
        if f.resolve() in ref_paths:
            continue
        if now - f.stat().st_mtime < grace:
            # 还在宽限期内：可能是刚上传还没发帖的图片
            continue
        orphans.append(f)

    apk_sorted = sorted(apks, key=_apk_version, reverse=True)
    apk_archive = apk_sorted[args.keep_apk:]

    print(f"[{mode}] 数据库引用 {len(refs)} 条；孤儿 {len(orphans)} 个；"
          f"待归档 APK {len(apk_archive)} 个；uploads 占用 {total_bytes / 1024 / 1024:.1f}MB")

    freed = 0
    for f in orphans:
        size = f.stat().st_size
        freed += size
        print(f"  删除孤儿: {f.relative_to(upload_dir)} ({size / 1024:.0f}KB)")
        if args.apply:
            f.unlink(missing_ok=True)

    if apk_archive:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(ARCHIVE_DIR, 0o700)
    for f in apk_archive:
        size = f.stat().st_size
        freed += size
        print(f"  归档APK: {f.name} ({size / 1024 / 1024:.1f}MB) -> {ARCHIVE_DIR}")
        if args.apply:
            shutil.move(str(f), str(ARCHIVE_DIR / f.name))

    # 删完清理空目录，避免按月份堆积空壳
    if args.apply:
        for root, dirs, _files in os.walk(upload_dir, topdown=False):
            for d in dirs:
                p = Path(root) / d
                try:
                    if not any(p.iterdir()):
                        p.rmdir()
                except OSError:
                    pass

    print(f"[{mode}] {'可释放' if args.apply else '预计可释放'} {_human(freed)}"
          + ("" if args.apply else "（加 --apply 才会真正执行）"))
    return 0


def _human(num_bytes: int) -> str:
    """按量级选单位，避免出现「可释放 0.0MB」这种明明删了文件却显示为 0 的误导输出。"""
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / 1024 / 1024:.1f}MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.0f}KB"
    return f"{num_bytes}B"


if __name__ == "__main__":
    raise SystemExit(main())
