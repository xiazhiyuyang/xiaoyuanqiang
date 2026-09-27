"""操作日志：列表 / 动作字典。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.operation_log import OperationLog
from app.schemas.common import Result, PageResponse
from app.core.activity import ACTION_LABELS
from app.api.deps import require_permission

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/logs", response_model=Result[PageResponse[dict]])
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    action: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("operation_log")),
):
    query = select(OperationLog)
    count_query = select(func.count()).select_from(OperationLog)
    if action:
        query = query.where(OperationLog.action == action)
        count_query = count_query.where(OperationLog.action == action)
    if keyword:
        cond = OperationLog.username.contains(keyword) | OperationLog.detail.contains(keyword)
        query = query.where(cond)
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()
    items = [{
        "id": lg.id, "user_id": lg.user_id, "username": lg.username,
        "action": lg.action, "action_text": ACTION_LABELS.get(lg.action, lg.action),
        "target_type": lg.target_type, "target_id": lg.target_id,
        "detail": lg.detail, "ip": lg.ip, "status": lg.status,
        "created_at": lg.created_at,
    } for lg in logs]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.get("/logs/actions", response_model=Result[list[dict]])
async def log_actions(
    admin: User = Depends(require_permission("operation_log")),
):
    return Result(data=[{"action": k, "label": v} for k, v in ACTION_LABELS.items()])
