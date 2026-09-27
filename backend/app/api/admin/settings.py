"""站点设置 + App 整包更新配置。"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.common import Result
from app.schemas.admin import SettingsUpdate, AppUpdateConfig
from app.api.deps import get_admin_user
from app.core.activity import (
    log_action, get_settings, update_settings, SETTING_DEFAULTS,
)

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


_BOOL_SETTING_KEYS = (
    "allow_register", "maintenance", "post_need_review", "allow_anonymous",
    "allow_video", "message_open", "show_level",
)
_INT_SETTING_KEYS = ("review_random_rate",)

_ENUM_FALLBACK = {
    "notice_mode": ("marquee", {"marquee", "vertical", "static"}),
    "review_mode": ("off", {"off", "random", "all"}),
    "default_theme": ("galaxy", {"galaxy", "ocean", "forest", "sunset", "rose", "midnight"}),
}


def _settings_form(data: dict) -> dict:
    """把存储的字符串配置转成后台表单需要的 bool/int/str。"""
    form = {}
    for key in SETTING_DEFAULTS:
        val = data.get(key, SETTING_DEFAULTS.get(key, ""))
        if key in _BOOL_SETTING_KEYS:
            form[key] = str(val) == "1"
        elif key in _INT_SETTING_KEYS:
            try:
                form[key] = int(float(val))
            except (TypeError, ValueError):
                form[key] = 20
        elif key in _ENUM_FALLBACK:
            default, allowed = _ENUM_FALLBACK[key]
            form[key] = val if val in allowed else default
        else:
            form[key] = val or ""
    return form


@router.get("/settings", response_model=Result[dict])
async def get_site_settings(
    admin: User = Depends(get_admin_user),
):
    data = await get_settings()
    return Result(data=_settings_form(data))


@router.put("/settings", response_model=Result[dict])
async def set_site_settings(
    data: SettingsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    changes = {}
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if key not in SETTING_DEFAULTS:
            continue
        if value is None:
            continue
        if isinstance(value, bool):
            changes[key] = "1" if value else "0"
        elif isinstance(value, int):
            changes[key] = str(value)
        else:
            changes[key] = (value or "").strip()
    # 兼容旧开关：一旦开启「发帖先审核」，同步为全部审核模式
    if changes.get("post_need_review") == "1":
        changes["review_mode"] = "all"
    if not changes:
        raise HTTPException(status_code=400, detail="没有需要更新的设置")
    result = await update_settings(db, changes)
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_setting_update",
        detail=f"修改站点设置：{'、'.join(changes.keys())}", request=request,
    )
    return Result(data=_settings_form(result), msg="设置已保存")


@router.get("/app-update", response_model=Result[dict])
async def admin_get_app_update(
    admin: User = Depends(get_admin_user),
):
    from app.api.app_update import _load_config
    return Result(data=_load_config())


@router.put("/app-update", response_model=Result[dict])
async def admin_save_app_update(
    data: AppUpdateConfig,
    request: Request,
    admin: User = Depends(get_admin_user),
):
    from app.api.app_update import CONFIG_PATH
    cfg = data.model_dump()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    await log_action(
        user_id=admin.id, username=admin.username, action="admin_app_update",
        detail=f"保存App更新配置：{cfg.get('latest_version')}（code {cfg.get('version_code')}）",
        request=request,
    )
    return Result(data=cfg, msg="更新配置已保存")
