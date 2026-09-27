"""工具箱 API：公开查询 + 管理员 CRUD。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tool import Tool, ToolCategory
from app.models.user import User
from app.api.deps import get_admin_user
from app.schemas.common import Result, PageResponse

router = APIRouter(prefix="/api/tools", tags=["tools"])


# ---------- 公开 API ----------

@router.get("/categories", response_model=Result[list])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """工具分类列表（含每个分类的工具数）。"""
    rows = (await db.execute(
        select(ToolCategory).order_by(ToolCategory.sort_order, ToolCategory.id)
    )).scalars().all()
    # 统计每个分类已发布工具数
    counts = {}
    if rows:
        cnt_rows = (await db.execute(
            select(Tool.category_id, func.count())
            .where(Tool.status == "published")
            .group_by(Tool.category_id)
        )).all()
        counts = {r[0]: r[1] for r in cnt_rows}
    data = [{"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon,
             "tool_count": counts.get(c.id, 0)} for c in rows]
    return Result(data=data)


@router.get("", response_model=Result[list])
async def list_tools(
    category: str | None = Query(None, description="分类slug筛选"),
    db: AsyncSession = Depends(get_db),
):
    """已发布工具列表，按分类分组返回。"""
    q = select(Tool).where(Tool.status == "published")
    if category:
        cat = (await db.execute(select(ToolCategory).where(ToolCategory.slug == category))).scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail="分类不存在")
        q = q.where(Tool.category_id == cat.id)
    rows = (await db.execute(q.order_by(Tool.sort_order, Tool.id.desc()))).scalars().all()

    # 分类映射
    cats = (await db.execute(select(ToolCategory))).scalars().all()
    cat_map = {c.id: {"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon} for c in cats}

    # 按分类分组
    groups = {}
    for t in rows:
        cid = t.category_id or 0
        if cid not in groups:
            cat_info = cat_map.get(cid, {"id": 0, "name": "其他", "slug": "other", "icon": "📦"})
            groups[cid] = {**cat_info, "tools": []}
        groups[cid]["tools"].append({
            "id": t.id, "name": t.name, "slug": t.slug, "description": t.description,
            "icon": t.icon, "tool_type": t.tool_type, "view_count": t.view_count,
            "is_featured": t.is_featured, "github_url": t.github_url,
        })
    return Result(data=list(groups.values()))


@router.get("/{slug}", response_model=Result[dict])
async def get_tool(slug: str, db: AsyncSession = Depends(get_db)):
    """工具详情（含 content/embed_url）。"""
    t = (await db.execute(select(Tool).where(Tool.slug == slug))).scalar_one_or_none()
    if not t or t.status != "published":
        raise HTTPException(status_code=404, detail="工具不存在或未上线")
    cat = None
    if t.category_id:
        c = (await db.execute(select(ToolCategory).where(ToolCategory.id == t.category_id))).scalar_one_or_none()
        if c:
            cat = {"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon}
    return Result(data={
        "id": t.id, "name": t.name, "slug": t.slug, "description": t.description,
        "icon": t.icon, "tool_type": t.tool_type, "embed_url": t.embed_url,
        "content": t.content, "github_url": t.github_url, "view_count": t.view_count,
        "is_featured": t.is_featured, "category": cat,
        "created_at": t.created_at,
    })


@router.post("/{slug}/view", response_model=Result)
async def record_tool_view(slug: str, db: AsyncSession = Depends(get_db)):
    """记录工具使用次数。"""
    t = (await db.execute(select(Tool).where(Tool.slug == slug))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="工具不存在")
    t.view_count = (t.view_count or 0) + 1
    await db.commit()
    return Result(msg="ok")


# ---------- 管理员 API ----------

admin_router = APIRouter(prefix="/api/admin/tools", tags=["admin-tools"])


@admin_router.get("", response_model=Result[PageResponse[dict]])
async def admin_list_tools(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(Tool)
    cq = select(func.count()).select_from(Tool)
    if keyword:
        cond = Tool.name.contains(keyword) | Tool.description.contains(keyword)
        q = q.where(cond); cq = cq.where(cond)
    if status:
        q = q.where(Tool.status == status); cq = cq.where(Tool.status == status)
    total = (await db.execute(cq)).scalar()
    rows = (await db.execute(
        q.order_by(Tool.sort_order, Tool.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    cats = (await db.execute(select(ToolCategory))).scalars().all()
    cat_map = {c.id: c.name for c in cats}
    items = [{
        "id": t.id, "name": t.name, "slug": t.slug, "description": t.description,
        "icon": t.icon, "tool_type": t.tool_type, "status": t.status,
        "category_name": cat_map.get(t.category_id, "—"), "category_id": t.category_id,
        "view_count": t.view_count, "is_featured": t.is_featured,
        "sort_order": t.sort_order, "github_url": t.github_url,
        "created_at": t.created_at,
    } for t in rows]
    return Result(data=PageResponse(items=items, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size))


@admin_router.post("", response_model=Result[dict])
async def admin_create_tool(
    data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user),
):
    if not data.get("name") or not data.get("slug"):
        raise HTTPException(status_code=400, detail="名称和标识必填")
    existing = (await db.execute(select(Tool).where(Tool.slug == data["slug"]))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="标识已存在")
    t = Tool(
        name=data["name"], slug=data["slug"],
        description=data.get("description", ""),
        category_id=data.get("category_id"),
        github_url=data.get("github_url", ""),
        icon=data.get("icon", "🔧"),
        tool_type=data.get("tool_type", "builtin"),
        embed_url=data.get("embed_url", ""),
        content=data.get("content", ""),
        status=data.get("status", "draft"),
        sort_order=data.get("sort_order", 0),
        is_featured=data.get("is_featured", False),
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return Result(data={"id": t.id}, msg="工具已创建")


@admin_router.put("/{tool_id}", response_model=Result)
async def admin_update_tool(
    tool_id: int, data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user),
):
    t = (await db.execute(select(Tool).where(Tool.id == tool_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="工具不存在")
    fields = ["name", "slug", "description", "category_id", "github_url", "icon",
              "tool_type", "embed_url", "content", "status", "sort_order", "is_featured"]
    for f in fields:
        if f in data:
            setattr(t, f, data[f])
    await db.commit()
    return Result(msg="工具已更新")


@admin_router.delete("/{tool_id}", response_model=Result)
async def admin_delete_tool(
    tool_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user),
):
    t = (await db.execute(select(Tool).where(Tool.id == tool_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="工具不存在")
    await db.delete(t)
    await db.commit()
    return Result(msg="工具已删除")


# 分类管理
@admin_router.get("/categories", response_model=Result[list])
async def admin_list_categories(db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    rows = (await db.execute(select(ToolCategory).order_by(ToolCategory.sort_order, ToolCategory.id))).scalars().all()
    return Result(data=[{"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon, "sort_order": c.sort_order} for c in rows])


@admin_router.post("/categories", response_model=Result[dict])
async def admin_create_category(data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    if not data.get("name") or not data.get("slug"):
        raise HTTPException(status_code=400, detail="名称和标识必填")
    c = ToolCategory(name=data["name"], slug=data["slug"], icon=data.get("icon", "📦"), sort_order=data.get("sort_order", 0))
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return Result(data={"id": c.id}, msg="分类已创建")


@admin_router.put("/categories/{cat_id}", response_model=Result)
async def admin_update_category(cat_id: int, data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    c = (await db.execute(select(ToolCategory).where(ToolCategory.id == cat_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="分类不存在")
    for f in ["name", "slug", "icon", "sort_order"]:
        if f in data:
            setattr(c, f, data[f])
    await db.commit()
    return Result(msg="分类已更新")


@admin_router.delete("/categories/{cat_id}", response_model=Result)
async def admin_delete_category(cat_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    c = (await db.execute(select(ToolCategory).where(ToolCategory.id == cat_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="分类不存在")
    # 该分类下的工具 category_id 置空
    tools = (await db.execute(select(Tool).where(Tool.category_id == cat_id))).scalars().all()
    for t in tools:
        t.category_id = None
    await db.delete(c)
    await db.commit()
    return Result(msg="分类已删除")
