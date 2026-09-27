"""经验等级体系（Galaxy 星轨等级）

- 经验值来源：登录、发帖、评论、收获点赞等
- 等级只由经验值决定，users.level 字段为冗余快照，每次增减经验时重算
- 功能解锁由等级门槛控制，前端通过 /api/users/levels 拉取展示
"""
from sqlalchemy.ext.asyncio import AsyncSession

# (等级, 名称, 所需累计经验, 主题色)
LEVEL_LADDER = [
    (1, "星尘", 0, "#94a3b8"),
    (2, "流星", 30, "#38bdf8"),
    (3, "彗星", 100, "#22d3ee"),
    (4, "行星", 240, "#34d399"),
    (5, "恒星", 500, "#fbbf24"),
    (6, "星云", 900, "#a78bfa"),
    (7, "银河", 1500, "#818cf8"),
    (8, "星穹", 2400, "#e879f9"),
    (9, "超新星", 3800, "#fb7185"),
    (10, "宇宙之心", 6000, "#f59e0b"),
]

# 功能解锁门槛：feature_key -> 最低等级
FEATURE_GATES = {
    "post": (1, "发布动态"),
    "comment": (1, "评论互动"),
    "like": (1, "点赞收藏"),
    "message": (2, "私信功能"),
    "video": (3, "发布视频"),
    "promotion": (6, "活动推广位"),
}

# 经验值获取规则
EXP_RULES = {
    "login": 2,       # 每日首次登录
    "post": 8,        # 发布一条动态
    "comment": 2,     # 发表一条评论
    "liked": 2,       # 内容被点赞（每次）
}

# 每日同一来源经验上限，防止刷分
DAILY_EXP_CAP = {
    "comment": 20,
    "liked": 40,
}


def level_of_exp(exp: int) -> int:
    """根据总经验计算当前等级。"""
    lv = 1
    for level, _name, need, _color in LEVEL_LADDER:
        if exp >= need:
            lv = level
        else:
            break
    return lv


def level_info(level: int) -> dict:
    level = max(1, min(level, len(LEVEL_LADDER)))
    idx = level - 1
    _lv, name, need, color = LEVEL_LADDER[idx]
    if level < len(LEVEL_LADDER):
        next_need = LEVEL_LADDER[idx + 1][2]
    else:
        next_need = need
    return {
        "level": level,
        "name": name,
        "color": color,
        "need": need,
        "next_need": next_need,
        "is_max": level >= len(LEVEL_LADDER),
    }


def progress(exp: int) -> dict:
    """返回当前等级、进度百分比、距下一级差值。"""
    cur = level_of_exp(exp)
    info = level_info(cur)
    if info["is_max"]:
        return {**info, "exp": exp, "progress": 100, "remain": 0}
    base = info["need"]
    span = info["next_need"] - base
    percent = round(min(100, max(0, (exp - base) / span * 100)))
    return {**info, "exp": exp, "progress": percent, "remain": info["next_need"] - exp}


def ladder() -> list[dict]:
    """完整等级表（含功能解锁说明），给等级中心页面用。"""
    result = []
    feature_by_level: dict[int, list[str]] = {}
    for key, (lv, label) in FEATURE_GATES.items():
        feature_by_level.setdefault(lv, []).append({"key": key, "label": label})
    for level, name, need, color in LEVEL_LADDER:
        result.append({
            "level": level, "name": name, "need": need, "color": color,
            "unlock": feature_by_level.get(level, []),
        })
    return result


def unlocked_features(level: int) -> dict:
    return {key: level >= lv for key, (lv, _label) in FEATURE_GATES.items()}


async def add_exp(db: AsyncSession, user, amount: int, reason: str = "") -> int:
    """给用户增加经验并重算等级，返回新等级。user 需是已在会话中的 User 对象。"""
    if not user or amount <= 0:
        return getattr(user, "level", 1) or 1
    user.exp = (user.exp or 0) + amount
    new_level = level_of_exp(user.exp)
    leveled_up = new_level != (user.level or 1)
    user.level = new_level
    return new_level
