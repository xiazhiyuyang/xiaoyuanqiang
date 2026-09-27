"""预览服务：单进程同时提供 API + 管理后台 + 电脑端 PC 站 + 手机端 H5（生产环境用 Docker+Nginx）

根路径 "/" 按访问终端自动分流：
- 手机 / 平板 / App 内置浏览器 -> 手机端 H5
- 桌面浏览器 -> 电脑端 PC 站（/pc/）
- 可用 ?v=h5 / ?v=pc 手动指定（仅当次访问生效）；/pc/ 始终直达电脑端
"""
import re
from pathlib import Path

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
MOBILE = ROOT / "mobile/dist/build/h5"
ADMIN = ROOT / "admin/dist"
PC = ROOT / "pc/dist"

# 移动端 UA 特征（命中即回手机版 H5；桌面微信 WindowsWeChat/MacWeChat 不含这些词，会走 PC）
MOBILE_UA_RE = re.compile(
    r"android|iphone|ipad|ipod|windows phone|harmonyos|mobile|blackberry|opera mini|ucweb|uni-app",
    re.IGNORECASE,
)

# 纵深防御：未命中任何路由时，凡疑似隐藏文件/后端源码/数据/备份/密钥的路径一律 404，
# 不回退到前端首页（避免以 200 暴露探测面，也防止把敏感路径误当前端路由）
_SENSITIVE_PATH_RE = re.compile(
    r"(^|/)\.|(^|/)backend(/|$)|"
    r"\.(env|git|svn|hg|py[co]?|db|sqlite3?|sql|log|bak|backup|old|orig|swp|"
    r"secret_key|pem|key|crt|cer|tar|gz|tgz|zip|rar|7z|conf|ini|ya?ml|sh)$",
    re.IGNORECASE,
)


class SPAStaticFiles(StaticFiles):
    """history 路由兜底：子路径找不到真实文件时返回 index.html，避免刷新子页 404"""
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return FileResponse(self.directory / "index.html")
            raise


# 移除 main.py 中占用 "/" 的 JSON 提示页，让根路径做终端分流
app.router.routes = [
    r for r in app.router.routes
    if getattr(r, "path", None) != "/" or getattr(r, "name", "") == "h5_index"
]
# 管理后台（vite base=/admin/，其资源在 /admin/assets/ 下，history 路由统一回退 index.html）
app.mount("/admin", SPAStaticFiles(directory=ADMIN, html=True), name="admin")
# 电脑端 PC 站（vite base=/pc/，history 路由统一回退 index.html；必须注册在 "/{full_path}" 兜底之前）
app.mount("/pc", SPAStaticFiles(directory=PC, html=True), name="pc")
# 手机端 H5 资源
app.mount("/assets", StaticFiles(directory=MOBILE / "assets"), name="h5-assets")
app.mount("/static", StaticFiles(directory=MOBILE / "static"), name="h5-static")


@app.get("/", include_in_schema=False)
async def root_index(request: Request):
    # 显式手动覆盖优先（仅当次访问生效）
    forced = request.query_params.get("v")
    if forced == "h5":
        return FileResponse(MOBILE / "index.html")
    if forced == "pc":
        return RedirectResponse(url="/pc/", status_code=302)
    # 按终端自动分流：手机 / 平板 / App 内置浏览器 -> 自适应 H5；
    # 桌面浏览器 -> 独立电脑端 /pc/（桌面微信 WindowsWeChat/MacWeChat 不含移动特征词，走 PC）
    ua = request.headers.get("user-agent", "")
    if MOBILE_UA_RE.search(ua):
        return FileResponse(MOBILE / "index.html")
    return RedirectResponse(url="/pc/", status_code=302)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    # API 未命中与已关闭的文档端点不回退到前端，直接 404，避免暴露框架痕迹
    if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
        raise StarletteHTTPException(status_code=404)
    # 疑似敏感文件/后端数据路径：直接 404，不回退前端首页
    if _SENSITIVE_PATH_RE.search(full_path):
        raise StarletteHTTPException(status_code=404)
    # 其余路径回 H5 首页（前端路由）
    return FileResponse(MOBILE / "index.html")
