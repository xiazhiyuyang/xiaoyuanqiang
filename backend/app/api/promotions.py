from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.promotion import Banner, Announcement
from app.schemas.common import Result

router = APIRouter(prefix="/api/promotions", tags=["运营位"])


def _banner_dict(b: Banner) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "image_url": b.image_url,
        "link_url": b.link_url,
        "theme": b.theme,
    }


def _announcement_dict(a: Announcement) -> dict:
    return {
        "id": a.id,
        "content": a.content,
        "link_url": a.link_url,
    }


@router.get("", response_model=Result[dict])
async def get_promotions(db: AsyncSession = Depends(get_db)):
    """首页一次性拉取上架中的广告位与公告位（无需登录）"""
    banners = (await db.execute(
        select(Banner).where(Banner.is_active == True)  # noqa: E712
        .order_by(desc(Banner.sort_order), Banner.id)
    )).scalars().all()
    announcements = (await db.execute(
        select(Announcement).where(Announcement.is_active == True)  # noqa: E712
        .order_by(desc(Announcement.sort_order), Announcement.id)
    )).scalars().all()
    return Result(data={
        "banners": [_banner_dict(b) for b in banners],
        "announcements": [_announcement_dict(a) for a in announcements],
    })
