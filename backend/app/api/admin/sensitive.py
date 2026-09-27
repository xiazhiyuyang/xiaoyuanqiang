"""敏感词管理：列表/增/改/删/批量导入。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.sensitive_word import SensitiveWord
from app.schemas.common import Result, PageResponse
from app.schemas.admin import (
    SensitiveWordCreate, SensitiveWordUpdate, SensitiveWordBatch,
)
from app.api.deps import require_permission
from app.core.moderation import invalidate as invalidate_words

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/sensitive-words", response_model=Result[PageResponse[dict]])
async def list_sensitive_words(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    keyword: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    query = select(SensitiveWord)
    count_query = select(func.count()).select_from(SensitiveWord)
    if keyword:
        query = query.where(SensitiveWord.word.contains(keyword))
        count_query = count_query.where(SensitiveWord.word.contains(keyword))
    if category:
        query = query.where(SensitiveWord.category == category)
        count_query = count_query.where(SensitiveWord.category == category)
    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.order_by(SensitiveWord.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    words = result.scalars().all()
    items = [{
        "id": w.id, "word": w.word, "category": w.category,
        "action": w.action, "is_enabled": w.is_enabled, "created_at": w.created_at,
    } for w in words]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=(total + page_size - 1) // page_size if total else 0))


@router.post("/sensitive-words", response_model=Result)
async def create_sensitive_word(
    data: SensitiveWordCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    word = data.word.strip()
    exists = await db.execute(select(SensitiveWord).where(SensitiveWord.word == word))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该敏感词已存在")
    db.add(SensitiveWord(word=word, category=data.category, action=data.action, is_enabled=data.is_enabled))
    await db.commit()
    invalidate_words()
    return Result(msg="已添加")


@router.put("/sensitive-words/{word_id}", response_model=Result)
async def update_sensitive_word(
    word_id: int,
    data: SensitiveWordUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    result = await db.execute(select(SensitiveWord).where(SensitiveWord.id == word_id))
    sw = result.scalar_one_or_none()
    if not sw:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    if data.category is not None:
        sw.category = data.category
    if data.action is not None:
        sw.action = data.action
    if data.is_enabled is not None:
        sw.is_enabled = data.is_enabled
    if data.word:
        sw.word = data.word.strip()
    await db.commit()
    invalidate_words()
    return Result(msg="已更新")


@router.delete("/sensitive-words/{word_id}", response_model=Result)
async def delete_sensitive_word(
    word_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    result = await db.execute(select(SensitiveWord).where(SensitiveWord.id == word_id))
    sw = result.scalar_one_or_none()
    if not sw:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    await db.delete(sw)
    await db.commit()
    invalidate_words()
    return Result(msg="已删除")


@router.post("/sensitive-words/batch", response_model=Result)
async def batch_import_sensitive_words(
    data: SensitiveWordBatch,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("sensitive_word")),
):
    category = data.category
    action = data.action
    raw_words = [w.strip() for w in data.text.replace("，", "\n").replace(",", "\n").splitlines()]
    words = [w for w in raw_words if w]
    if not words:
        raise HTTPException(status_code=400, detail="没有可导入的词")
    existing = (await db.execute(select(SensitiveWord.word).where(SensitiveWord.word.in_(words)))).all()
    existing_set = {row[0] for row in existing}
    added = 0
    for w in words:
        if w in existing_set:
            continue
        db.add(SensitiveWord(word=w, category=category, action=action))
        existing_set.add(w)
        added += 1
    await db.commit()
    invalidate_words()
    return Result(msg=f"导入完成：新增 {added} 个，跳过已存在 {len(words) - added} 个",
                  data={"added": added, "skipped": len(words) - added})
