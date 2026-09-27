"""管理后台路由聚合包。

将原 admin.py 按功能拆分为多个子模块，统一在此聚合为一个 router。
所有子路由均挂在 /api/admin 前缀下，保持原有接口路径与行为不变。
"""
from fastapi import APIRouter

from app.api.admin import (
    dashboard,
    users,
    posts,
    comments,
    categories,
    reports,
    sensitive,
    promotions,
    logs,
    settings,
    bans,
)

# 聚合路由本身不再加前缀：每个子模块的 router 已自带 /api/admin 前缀，
# 否则会出现 /api/admin/api/admin 的双重前缀。
router = APIRouter(tags=["管理后台"])

router.include_router(dashboard.router)
router.include_router(users.router)
router.include_router(posts.router)
router.include_router(comments.router)
router.include_router(categories.router)
router.include_router(reports.router)
router.include_router(sensitive.router)
router.include_router(promotions.router)
router.include_router(logs.router)
router.include_router(settings.router)
router.include_router(bans.router)

# 工具管理接口在 tools.py 的 admin_router，AI审查接口在 ai_review.py，均由 main.py 单独 include。

__all__ = ["router"]
