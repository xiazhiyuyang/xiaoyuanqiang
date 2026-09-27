"""站外域名黑名单（涉黄/涉赌/诈骗域名）。

数据来源：scripts/import_lexicon.py 从开源词库 `非法网址.txt` 抽取，
落盘为 backend/data/blocked_domains.txt（一行一个域名）。
放文件而不是数据库，是为了避免把上万条域名塞进 site_settings 的 JSON 配置里。
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

logger = logging.getLogger("campus-wall")

_PATH = Path(__file__).resolve().parents[3] / "data" / "blocked_domains.txt"
_URL_RE = re.compile(r"(?:https?://|www\.)([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)", re.I)

_domains: set[str] = set()
_mtime: float = -1.0
_loaded_at: float = 0.0
_TTL = 300.0


def _load(force: bool = False) -> set[str]:
    global _domains, _mtime, _loaded_at
    now = time.time()
    if not force and _domains and now - _loaded_at < _TTL:
        return _domains
    try:
        if not _PATH.exists():
            _domains = set()
            _loaded_at = now
            return _domains
        mtime = _PATH.stat().st_mtime
        if not force and mtime == _mtime:
            _loaded_at = now
            return _domains
        data = set()
        for line in _PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            d = line.strip().lower().lstrip(".")
            if d and " " not in d:
                data.add(d)
        _domains = data
        _mtime = mtime
        _loaded_at = now
        logger.info("域名黑名单已加载 %d 条", len(_domains))
    except Exception:
        logger.warning("域名黑名单加载失败", exc_info=True)
        _domains = set()
    return _domains


def size() -> int:
    return len(_load())


def extract_domains(text: str) -> list[str]:
    if not text:
        return []
    return [m.group(1).lower() for m in _URL_RE.finditer(text)]


def matched_blocked_domains(text: str) -> list[str]:
    """返回文本中出现且命中黑名单的域名。"""
    domains = _load()
    if not domains or not text:
        return []
    hits = []
    for d in extract_domains(text):
        if d in domains:
            hits.append(d)
            continue
        # 逐级父域匹配：a.b.example.com 命中 example.com
        parts = d.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in domains:
                hits.append(d)
                break
    return hits


def invalidate() -> None:
    global _mtime
    _mtime = -1.0
