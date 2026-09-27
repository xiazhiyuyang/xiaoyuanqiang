import json
from pathlib import Path

from fastapi import APIRouter, Query

from app.schemas.common import Result

router = APIRouter(prefix="/api/app", tags=["App版本更新"])

CONFIG_PATH = Path(__file__).resolve().parent.parent / "app-update.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "latest_version": "1.0.0",
    "version_code": 100,
    "required": False,
    "changelog": "修复已知问题，优化使用体验。",
    "apk_url": "",
}


def _compare_version(current: str, latest: str) -> int:
    """返回 1 表示 latest 更新，-1 表示 current 更新，0 表示相同。"""
    current_parts = [int(part) if part.isdigit() else 0 for part in current.split(".")]
    latest_parts = [int(part) if part.isdigit() else 0 for part in latest.split(".")]
    length = max(len(current_parts), len(latest_parts))
    for index in range(length):
        current_value = current_parts[index] if index < len(current_parts) else 0
        latest_value = latest_parts[index] if index < len(latest_parts) else 0
        if latest_value != current_value:
            return 1 if latest_value > current_value else -1
    return 0


def _load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                config.update({key: raw.get(key, config[key]) for key in DEFAULT_CONFIG})
        except (json.JSONDecodeError, OSError):
            # 配置损坏时默认不提示更新，避免把用户锁在错误更新流程里
            config["enabled"] = False
    return config


@router.get("/version", response_model=Result[dict])
async def get_app_version(
    platform: str = Query("android", description="android / ios"),
    version: str = Query("", description="当前 App versionName"),
    version_code: int = Query(0, description="当前 App versionCode"),
):
    """App 启动时检查整包 APK 冷更新。完整 APK 放到 backend/uploads/app 后由 /uploads 静态托管。"""
    config = _load_config()
    latest_version = str(config.get("latest_version") or DEFAULT_CONFIG["latest_version"])
    latest_code = int(config.get("version_code") or 0)
    current_version = (version or "").strip()
    current_code = int(version_code or 0)

    has_update = False
    if config.get("enabled"):
        code_newer = bool(current_code and latest_code and latest_code > current_code)
        version_newer = bool(current_version and _compare_version(current_version, latest_version) > 0)
        # 未传当前版本时，只要服务端启用了更新就返回新版本信息
        has_update = code_newer or version_newer or (not current_code and not current_version)

    update_type = "apk" if config.get("apk_url") else "none"
    return Result(data={
        "enabled": bool(config.get("enabled")),
        "platform": platform,
        "current_version": current_version,
        "current_version_code": current_code,
        "latest_version": latest_version,
        "version_code": latest_code,
        "required": bool(config.get("required")),
        "changelog": config.get("changelog") or DEFAULT_CONFIG["changelog"],
        "apk_url": config.get("apk_url") or "",
        "update_type": update_type,
        "has_update": has_update,
    })
