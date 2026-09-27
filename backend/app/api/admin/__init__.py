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

# 备注：
# - /api/admin/tools 下的工具管理接口仍位于 app/api/tools.py 的 admin_router，
#   由 main.py 单独 include（保持原路径不变）。
# - /api/ai-review 下的 AI 审查接口仍位于 app/api/ai_review.py，由 main.py 单独 include。
# - app/api/admin/_utils.py 提供确认 token 与 _purge_user 等公共函数。

__all__ = ["router"]
