"""运营推广：Banner 广告位 + 公告位管理。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.promotion import Banner, Announcement
from app.schemas.common import Result
from app.schemas.admin import (
    BannerCreate, BannerUpdate, AnnouncementCreate, AnnouncementUpdate,
)
from app.api.deps import require_permission

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def _banner_dict(b: Banner) -> dict:
    return {
        "id": b.id, "title": b.title, "image_url": b.image_url,
        "link_url": b.link_url, "theme": b.theme,
        "sort_order": b.sort_order, "is_active": b.is_active,
        "created_at": b.created_at,
    }


@router.get("/banners", response_model=Result[list[dict]])
async def admin_list_banners(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banners = (await db.execute(
        select(Banner).order_by(desc(Banner.sort_order), Banner.id.desc())
    )).scalars().all()
    return Result(data=[_banner_dict(b) for b in banners])


@router.post("/banners", response_model=Result[dict])
async def admin_create_banner(
    data: BannerCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banner = Banner(**data.model_dump())
    db.add(banner)
    await db.commit()
    await db.refresh(banner)
    return Result(data=_banner_dict(banner), msg="已添加")


@router.put("/banners/{banner_id}", response_model=Result[dict])
async def admin_update_banner(
    banner_id: int,
    data: BannerUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banner = (await db.execute(select(Banner).where(Banner.id == banner_id))).scalar_one_or_none()
    if not banner:
        raise HTTPException(status_code=404, detail="广告不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(banner, field, value)
    await db.commit()
    await db.refresh(banner)
    return Result(data=_banner_dict(banner), msg="已更新")


@router.delete("/banners/{banner_id}", response_model=Result)
async def admin_delete_banner(
    banner_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    banner = (await db.execute(select(Banner).where(Banner.id == banner_id))).scalar_one_or_none()
    if not banner:
        raise HTTPException(status_code=404, detail="广告不存在")
    await db.delete(banner)
    await db.commit()
    return Result(msg="已删除")


def _announcement_dict(a: Announcement) -> dict:
    return {
        "id": a.id, "content": a.content, "link_url": a.link_url,
        "sort_order": a.sort_order, "is_active": a.is_active,
        "created_at": a.created_at,
    }


@router.get("/announcements", response_model=Result[list[dict]])
async def admin_list_announcements(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    items = (await db.execute(
        select(Announcement).order_by(desc(Announcement.sort_order), Announcement.id.desc())
    )).scalars().all()
    return Result(data=[_announcement_dict(a) for a in items])


@router.post("/announcements", response_model=Result[dict])
async def admin_create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    ann = Announcement(**data.model_dump())
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return Result(data=_announcement_dict(ann), msg="已添加")


@router.put("/announcements/{ann_id}", response_model=Result[dict])
async def admin_update_announcement(
    ann_id: int,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    ann = (await db.execute(select(Announcement).where(Announcement.id == ann_id))).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ann, field, value)
    await db.commit()
    await db.refresh(ann)
    return Result(data=_announcement_dict(ann), msg="已更新")


@router.delete("/announcements/{ann_id}", response_model=Result)
async def admin_delete_announcement(
    ann_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("ad_manage")),
):
    ann = (await db.execute(select(Announcement).where(Announcement.id == ann_id))).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    await db.delete(ann)
    await db.commit()
    return Result(msg="已删除")
