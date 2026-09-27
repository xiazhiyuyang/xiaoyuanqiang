"""公开站点配置：App / H5 启动时匿名拉取（主题、站点名、功能开关、审核策略等）。

注意：只返回 public_app_settings() 白名单内的非敏感项，
绝不泄露 SECRET_KEY、管理员账号等任何服务端机密。
"""
from fastapi import APIRouter

from app.schemas.common import Result
from app.core.activity import public_app_settings

router = APIRouter(prefix="/api/settings", tags=["站点配置"])


@router.get("/app", response_model=Result[dict])
async def get_app_settings():
    """App 启动配置：默认主题、站点信息、功能开关、维护状态、审核策略。"""
    return Result(data=await public_app_settings())
