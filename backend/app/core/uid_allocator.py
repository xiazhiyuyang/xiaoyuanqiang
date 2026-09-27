"""UID 号段分配核心逻辑（重设计版）。

号段规则：
  尊享号段：00001-00999，预生成，需管理员授予，取最小可用号。
  普通号段：01000 起，新用户注册自动分配。
    分配策略：优先取池中 available 的最小普通号（管理员解封的），
    没有则取当前最大普通号 +1（直接查表，不依赖外部 counter）。

用户注销/删除：UID 状态改为 reserved（永久封存）。
管理员解封：reserved → available，重新进入分配池。
"""
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.uid import UIDAllocation

PREMIUM_START = 1
PREMIUM_END = 999
NORMAL_START = 1000


def _fmt(n: int) -> str:
    return f"{n:05d}"


async def init_premium_pool(db: AsyncSession) -> int:
    """初始化尊享号段 00001-00999。已存在则跳过。返回新增数量。"""
    existing = set((await db.execute(select(UIDAllocation.uid))).scalars().all())
    added = 0
    for n in range(PREMIUM_START, PREMIUM_END + 1):
        uid = _fmt(n)
        if uid not in existing:
            db.add(UIDAllocation(uid=uid, status="available", is_premium=True))
            added += 1
    if added:
        await db.commit()
    return added


async def _next_normal_number(db: AsyncSession) -> int:
    """取当前最大普通号 +1。表为空则从 NORMAL_START 开始。"""
    max_uid = (await db.execute(
        select(func.max(UIDAllocation.uid)).where(UIDAllocation.is_premium == False)  # noqa: E712
    )).scalar()
    if not max_uid:
        return NORMAL_START
    try:
        return int(max_uid) + 1
    except (TypeError, ValueError):
        return NORMAL_START


async def allocate_normal_uid(db: AsyncSession, user_id: int) -> str:
    """为用户分配普通 UID。优先池中解封的最小号，否则最大号+1。"""
    # 1. 优先取池中 available 的最小普通号
    row = (await db.execute(
        select(UIDAllocation).where(
            UIDAllocation.status == "available",
            UIDAllocation.is_premium == False,  # noqa: E712
        ).order_by(UIDAllocation.uid.asc()).limit(1)
    )).scalar_one_or_none()

    if row:
        uid = row.uid
        row.status = "assigned"
        row.user_id = user_id
        row.assigned_at = datetime.now(timezone.utc)
    else:
        # 2. 最大普通号 +1 生成新号
        n = await _next_normal_number(db)
        uid = _fmt(n)
        db.add(UIDAllocation(
            uid=uid, status="assigned", is_premium=False,
            user_id=user_id, assigned_at=datetime.now(timezone.utc),
        ))

    await db.commit()
    return uid


async def allocate_premium_uid(db: AsyncSession, user_id: int) -> str | None:
    """授予用户尊享号（取最小可用尊享号）。无可用号返回 None。"""
    row = (await db.execute(
        select(UIDAllocation).where(
            UIDAllocation.status == "available",
            UIDAllocation.is_premium == True,  # noqa: E712
        ).order_by(UIDAllocation.uid.asc()).limit(1)
    )).scalar_one_or_none()
    if not row:
        return None
    row.status = "assigned"
    row.user_id = user_id
    row.assigned_at = datetime.now(timezone.utc)
    await db.commit()
    return row.uid


async def reserve_uid(db: AsyncSession, user_id: int) -> str | None:
    """用户注销/删除时，将其 UID 封存（reserved）。返回被封存的 UID。"""
    row = (await db.execute(
        select(UIDAllocation).where(UIDAllocation.user_id == user_id)
    )).scalar_one_or_none()
    if not row:
        return None
    row.status = "reserved"
    row.user_id = None
    row.assigned_at = None
    await db.commit()
    return row.uid


async def unreserve_uid(db: AsyncSession, uid: str) -> bool:
    """管理员把封存的 UID 重新放回分配池。"""
    row = (await db.execute(select(UIDAllocation).where(UIDAllocation.uid == uid))).scalar_one_or_none()
    if not row or row.status != "reserved":
        return False
    row.status = "available"
    await db.commit()
    return True


async def assign_specific_uid(db: AsyncSession, uid: str, user_id: int) -> bool:
    """管理员手动把指定 UID 分配给用户（UID 必须 available）。"""
    row = (await db.execute(select(UIDAllocation).where(UIDAllocation.uid == uid))).scalar_one_or_none()
    if not row or row.status != "available":
        return False
    row.status = "assigned"
    row.user_id = user_id
    row.assigned_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def get_uid_stats(db: AsyncSession) -> dict:
    """统计各状态 UID 数量。"""
    rows = (await db.execute(
        select(UIDAllocation.status, UIDAllocation.is_premium, func.count())
        .group_by(UIDAllocation.status, UIDAllocation.is_premium)
    )).all()
    result = {
        "premium_total": PREMIUM_END - PREMIUM_START + 1,
        "premium_available": 0, "premium_assigned": 0, "premium_reserved": 0,
        "normal_assigned": 0, "normal_reserved": 0,
    }
    for status, is_premium, cnt in rows:
        if is_premium:
            if status == "available":
                result["premium_available"] = cnt
            elif status == "assigned":
                result["premium_assigned"] = cnt
            elif status == "reserved":
                result["premium_reserved"] = cnt
        else:
            if status == "assigned":
                result["normal_assigned"] = cnt
            elif status == "reserved":
                result["normal_reserved"] = cnt
    return result
