"""分类管理：增删。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.post import Category
from app.schemas.common import Result
from app.schemas.post import CategoryResponse
from app.schemas.admin import CategoryCreate
from app.api.deps import require_permission

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.post("/categories", response_model=Result[CategoryResponse])
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("category_manage")),
):
    exists = await db.execute(select(Category).where(Category.slug == data.slug))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分类标识已存在")
    category = Category(
        name=data.name, slug=data.slug,
        icon=data.icon, sort_order=data.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return Result(data=CategoryResponse.model_validate(category))


@router.delete("/categories/{category_id}", response_model=Result)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("category_manage")),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    await db.delete(category)
    await db.commit()
    return Result(msg="已删除")
