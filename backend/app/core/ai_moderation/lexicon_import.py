"""开源敏感词库导入（GitHub: Konsheng/Sensitive-lexicon, MIT）。

为什么需要「导入器」而不是直接往 DFA 里灌文件：
- 原始词库共 8.7 万行、去重后 5.1 万条，其中「零时-Tencent」7 万行是地名/错字变体，
  「网易前端过滤词库」以人名为主 —— 全量灌进去会让 2G 内存的机器吃满，
  并且误报率会让校园墙无法正常使用；
- 因此按「来源文件 -> 违规分类 + 危险等级 + 处置动作」映射后做清洗：
  长度下限、纯 ASCII 词长度下限、校园正常词汇白名单、去重。

同时抽取：
- 非法网址.txt -> backend/data/blocked_domains.txt（域名黑名单）
- 由词库反推「繁体 -> 简体」字符映射 -> app/core/ai_moderation/data/char_map.json
  （只收词库真正需要的那几百个字符，长度严格 1:1，不会破坏打码索引）
"""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger("campus-wall")

REPO_ZIP_URL = "https://codeload.github.com/Konsheng/Sensitive-lexicon/zip/refs/heads/main"
REPO_URL = "https://github.com/Konsheng/Sensitive-lexicon"
REPO_LICENSE = "MIT"

BACKEND_DIR = Path(__file__).resolve().parents[3]   # .../backend
DATA_DIR = BACKEND_DIR / "data"
CACHE_DIR = DATA_DIR / "lexicon_cache"
CHAR_MAP_PATH = Path(__file__).resolve().parent / "data" / "char_map.json"
DOMAIN_PATH = DATA_DIR / "blocked_domains.txt"


@dataclass(frozen=True)
class Source:
    """一个词库文件的导入规则。"""
    filename: str
    category: str
    action: str
    severity: int
    min_len: int = 2
    note: str = ""
    enabled: bool = True


# 只导入「映射清晰、误报可控」的文件；噪音大的文件默认跳过，可在导入时开启
SOURCES: tuple[Source, ...] = (
    Source("暴恐词库.txt", "terror", "block", 5, 2, "暴恐组织与极端主义词汇"),
    Source("涉枪涉爆.txt", "illegal", "block", 5, 2, "枪支弹药爆炸物交易词汇"),
    Source("色情词库.txt", "porn", "block", 5, 2, "色情硬词"),
    Source("色情类型.txt", "porn", "review", 3, 2, "色情软词，转人工确认"),
    Source("政治类型.txt", "politics", "block", 5, 2, "政治敏感词"),
    Source("反动词库.txt", "politics", "block", 5, 2, "反动宣传词汇"),
    Source("贪腐词库.txt", "politics", "review", 3, 2, "涉政低置信，转人工"),
    Source("COVID-19词库.txt", "politics", "review", 3, 2, "疫情相关敏感表述，转人工"),
    Source("新思想启蒙.txt", "politics", "review", 3, 2, "涉政低置信，转人工"),
    Source("广告类型.txt", "ad", "review", 2, 2, "广告引流泛词"),
    Source("补充词库.txt", "other", "review", 3, 2, "综合补充词"),
    Source("民生词库.txt", "other", "mask", 1, 4, "民生类泛词，仅打码，取长词"),
    Source("其他词库.txt", "other", "review", 2, 3, "其他泛词，取长词"),
)

# 噪音过大、默认跳过的词库（可通过 include_noisy=True 打开）
NOISY_SOURCES: tuple[Source, ...] = (
    Source("GFW补充词库.txt", "politics", "review", 3, 3, "GFW 补充词库（噪音较大）"),
    Source("零时-Tencent.txt", "other", "review", 2, 4, "腾讯零时词库（7 万行，含大量地名/错字变体）", enabled=False),
    Source("网易前端过滤敏感词库.txt", "other", "review", 2, 4, "网易词库（以人名为主）", enabled=False),
)

# 校园场景正常词汇：出现在这些词里一律不导入（含子串匹配），压低误伤
SKIP_EXACT = {
    "兼职", "招聘", "网络", "代理", "优惠", "免费", "活动", "报名", "社团", "宿舍",
    "食堂", "老师", "学生", "学生党", "考试", "答案", "论文", "作业", "成绩",
    "补考", "挂科", "实习", "找工作", "考研", "保研", "出国", "贷款", "分期",
    "手机", "电话", "微信", "直播", "网红", "主播", "游戏", "充值", "账号",
    "密码", "身份证", "户口", "疫苗", "疫情", "核酸", "隔离", "涨价", "房价",
    "工资", "加班", "裁员", "失业", "离婚", "出轨", "家暴", "抑郁", "焦虑",
    "打人", "拆迁", "腐败", "贪污", "警察", "政府", "学校", "老师", "同学",
    "视频", "照片", "群", "优惠券", "拼单", "团购", "代购", "快递", "外卖",
    "军训", "选课", "学分", "导师", "答辩", "毕业", "校招", "社招", "简历",
}
SKIP_CONTAINS = ("习近平新时代", "社会主义核心", "不忘初心", "牢记使命")

_ASCII_RE = re.compile(r"^[\x00-\x7f]+$")
_WS_RE = re.compile(r"\s+")


def repo_available(root: Path) -> bool:
    return (root / "Vocabulary").is_dir()


async def download_repo(dest: Path | None = None, timeout: float = 60.0) -> Path:
    """下载并解压开源词库，返回解压后的仓库根目录。"""
    dest = dest or CACHE_DIR
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "Sensitive-lexicon-main"
    if repo_available(target):
        logger.info("复用已下载的词库：%s", target)
        return target
    logger.info("开始下载开源敏感词库 %s", REPO_URL)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(REPO_ZIP_URL)
    if resp.status_code >= 400:
        raise RuntimeError(f"下载失败 HTTP {resp.status_code}")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(dest)
    if not repo_available(target):
        raise RuntimeError("词库压缩包结构异常，未找到 Vocabulary 目录")
    logger.info("词库下载完成 -> %s (%.1f KB)", target, len(resp.content) / 1024)
    return target


def _clean_word(raw: str, src: Source) -> str | None:
    word = _WS_RE.sub("", (raw or "").strip().lstrip("\ufeff"))
    if not word or len(word) < src.min_len:
        return None
    if word in SKIP_EXACT or any(s in word for s in SKIP_CONTAINS):
        return None
    if _ASCII_RE.match(word) and len(word) < max(3, src.min_len):
        return None
    if len(word) > 64:
        return None
    return word


def collect_words(root: Path, *, include_noisy: bool = False) -> tuple[dict[str, dict], dict]:
    """遍历词库文件，返回 (word -> 词条信息, 统计)。后导入的来源不覆盖已有词条。"""
    sources = list(SOURCES) + ([s for s in NOISY_SOURCES if s.enabled] if include_noisy else [])
    vocab = root / "Vocabulary"
    table: dict[str, dict] = {}
    stats: dict[str, dict] = {}
    for src in sources:
        path = vocab / src.filename
        if not path.exists():
            stats[src.filename] = {"error": "文件不存在", "added": 0, "raw": 0}
            continue
        added = 0
        raw_count = 0
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            raw_count += 1
            word = _clean_word(line, src)
            if not word or word in table:
                continue
            table[word] = {
                "word": word, "category": src.category, "action": src.action,
                "severity": src.severity, "source": "lexicon", "note": src.note,
            }
            added += 1
        stats[src.filename] = {
            "raw": raw_count, "added": added,
            "category": src.category, "action": src.action, "severity": src.severity,
        }
    return table, stats


def extract_domains(root: Path, *, limit: int = 60000) -> list[str]:
    """从「非法网址.txt」抽取域名黑名单。"""
    path = root / "Vocabulary" / "非法网址.txt"
    if not path.exists():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        d = line.strip().lower().lstrip(".")
        if not d or " " in d or len(d) < 4 or len(d) > 100:
            continue
        if not re.fullmatch(r"[a-z0-9\-._]+", d):
            continue
        if "." not in d or d in seen:
            continue
        seen.add(d)
        out.append(d)
        if len(out) >= limit:
            break
    return out


def write_domains(domains: list[str]) -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOMAIN_PATH.write_text("\n".join(domains) + "\n", encoding="utf-8")
    from app.core.ai_moderation import domains as domain_mod
    domain_mod.invalidate()
    return len(domains)


def build_char_map(words: list[str]) -> dict[str, str]:
    """由词库反推「繁体/异体 -> 简体」的 1:1 字符映射。

    只在两端长度一致时记录，保证映射不改变字符串长度
    （moderation._normalize 依赖长度不变的索引映射来定位打码区间）。
    """
    try:
        from zhconv import convert  # 纯 Python，体积小
    except ImportError:
        logger.warning("未安装 zhconv，跳过繁简归一化表生成（可 pip install zhconv 后重跑）")
        return {}
    cmap: dict[str, str] = {}
    for word in words:
        try:
            simple = convert(word, "zh-cn")
        except Exception:
            continue
        if len(simple) != len(word) or simple == word:
            continue
        for a, b in zip(word, simple):
            if a != b and len(a) == 1 and len(b) == 1:
                cmap[a] = b
    return cmap


def write_char_map(cmap: dict[str, str]) -> int:
    CHAR_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAR_MAP_PATH.write_text(
        json.dumps(cmap, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # 让已经加载过空表的进程重新读取
    from app.core import moderation
    moderation._char_map_loaded = False  # noqa: SLF001
    moderation.invalidate()
    return len(cmap)


async def import_to_db(
    db,
    table: dict[str, dict],
    *,
    overwrite: bool = False,
) -> dict:
    """把词表写进 sensitive_words。默认不覆盖已有词条（保护后台手工调整）。"""
    from sqlalchemy import select

    from app.models.sensitive_word import SensitiveWord

    words = list(table.keys())
    existing: dict[str, SensitiveWord] = {}
    # 分批查询，避免 IN 子句过长
    for i in range(0, len(words), 800):
        chunk = words[i:i + 800]
        rows = (await db.execute(
            select(SensitiveWord).where(SensitiveWord.word.in_(chunk))
        )).scalars().all()
        for row in rows:
            existing[row.word] = row

    added = updated = skipped = 0
    for word, info in table.items():
        row = existing.get(word)
        if row is None:
            db.add(SensitiveWord(**info))
            added += 1
            continue
        if overwrite and row.source == "lexicon":
            row.category = info["category"]
            row.action = info["action"]
            row.severity = info["severity"]
            row.note = info["note"]
            updated += 1
        else:
            skipped += 1
    await db.commit()

    from app.core import moderation
    moderation.invalidate()
    return {"added": added, "updated": updated, "skipped": skipped, "total": len(table)}


async def one_click_import(
    db, *, include_noisy: bool = False, include_domains: bool = True,
    overwrite: bool = False, root: Path | None = None,
) -> dict:
    """后台「一键导入开源词库」的完整流程。"""
    if root is None:
        root = await download_repo()
    table, stats = collect_words(root, include_noisy=include_noisy)
    result = await import_to_db(db, table, overwrite=overwrite)
    result["sources"] = stats
    result["repo"] = REPO_URL
    result["license"] = REPO_LICENSE

    # 繁简字符映射
    cmap = build_char_map(list(table.keys()))
    result["char_map_size"] = write_char_map(cmap)

    if include_domains:
        domains = extract_domains(root)
        result["blocked_domains"] = write_domains(domains)
    return result
