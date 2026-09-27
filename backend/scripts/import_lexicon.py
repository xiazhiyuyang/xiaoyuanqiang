#!/usr/bin/env python
"""导入开源敏感词库 / 生成字符归一化表 / 抽取域名黑名单。

用法（在 backend 目录下，使用项目虚拟环境）：

    # 全量：下载词库 -> 清洗导入 -> 生成繁简映射 -> 抽取域名黑名单
    venv/bin/python scripts/import_lexicon.py

    # 只看会导入多少词，不写库
    venv/bin/python scripts/import_lexicon.py --dry-run

    # 从已下载的目录导入（不联网）
    venv/bin/python scripts/import_lexicon.py --local /root/Sensitive-lexicon-main

    # 连同噪音词库一起导入
    venv/bin/python scripts/import_lexicon.py --include-noisy

词库来源：https://github.com/Konsheng/Sensitive-lexicon （MIT 许可）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> int:
    parser = argparse.ArgumentParser(description="导入开源敏感词库")
    parser.add_argument("--local", help="本地词库仓库根目录（含 Vocabulary/）")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写数据库")
    parser.add_argument("--include-noisy", action="store_true", help="包含噪音较大的词库")
    parser.add_argument("--no-domains", action="store_true", help="不导入域名黑名单")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的开源词条")
    args = parser.parse_args()

    from app.core.ai_moderation import lexicon_import as importer

    if args.local:
        root = Path(args.local).resolve()
        if not importer.repo_available(root):
            print(f"[x] {root} 下没有找到 Vocabulary 目录")
            return 2
    else:
        root = await importer.download_repo()

    table, stats = importer.collect_words(root, include_noisy=args.include_noisy)

    print("=" * 64)
    print(f"词库来源：{importer.REPO_URL}  ({importer.REPO_LICENSE})")
    print(f"仓库目录：{root}")
    print("-" * 64)
    print(f"{'文件':<34}{'原始行':>10}{'导入':>10}  动作")
    for name, st in stats.items():
        if "error" in st:
            print(f"{name:<34}{'-':>10}{'-':>10}  {st['error']}")
            continue
        print(f"{name:<34}{st['raw']:>10}{st['added']:>10}  "
              f"{st['category']}/{st['action']}/L{st['severity']}")
    print("-" * 64)
    print(f"合计去重后可导入：{len(table)} 条")

    by_cat: dict[str, int] = {}
    by_act: dict[str, int] = {}
    for info in table.values():
        by_cat[info["category"]] = by_cat.get(info["category"], 0) + 1
        by_act[info["action"]] = by_act.get(info["action"], 0) + 1
    print("按分类：", json.dumps(by_cat, ensure_ascii=False))
    print("按动作：", json.dumps(by_act, ensure_ascii=False))
    print("=" * 64)

    if args.dry_run:
        print("[dry-run] 未写入数据库")
        return 0

    from app.database import AsyncSessionLocal, init_db
    await init_db()

    async with AsyncSessionLocal() as db:
        result = await importer.import_to_db(db, table, overwrite=args.overwrite)
    print(f"数据库写入：新增 {result['added']}，更新 {result['updated']}，跳过 {result['skipped']}")

    cmap = importer.build_char_map(list(table.keys()))
    size = importer.write_char_map(cmap)
    print(f"繁简/异体字符归一表：{size} 条 -> {importer.CHAR_MAP_PATH}")

    if not args.no_domains:
        domains = importer.extract_domains(root)
        importer.write_domains(domains)
        print(f"违规域名黑名单：{len(domains)} 条 -> {importer.DOMAIN_PATH}")

    print("完成。服务端敏感词引擎会在下次调用时自动重载。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
