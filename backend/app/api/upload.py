import io
import uuid
from datetime import datetime

import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from app.config import settings
from app.models.user import User
from app.schemas.common import Result
from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit
from app.core.activity import log_action

router = APIRouter(prefix="/api/upload", tags=["文件上传"])

# 限制最大解码像素，防范解压炸弹
Image.MAX_IMAGE_PIXELS = 120_000_000
# 图片最长边上限：只在超过时等比缩小，绝不放大小图，保证清晰度
MAX_IMAGE_EDGE = 2560

# PIL 格式 -> (扩展名, content_type, PIL格式名)
_FORMAT_MAP = {
    "JPEG": (".jpg", "image/jpeg", "JPEG"),
    "PNG": (".png", "image/png", "PNG"),
    "GIF": (".gif", "image/gif", "GIF"),
    "WEBP": (".webp", "image/webp", "WEBP"),
}

# 视频真实格式签名：扩展名 -> (魔数校验函数, content_type)
def _is_mp4_like(head: bytes) -> bool:
    # ISO BMFF：偏移 4..8 为 'ftyp'（MP4/MOV/M4V 均如此）
    return len(head) >= 12 and head[4:8] == b"ftyp"


def _is_webm(head: bytes) -> bool:
    return head[:4] == b"\x1a\x45\xdf\xa3"  # EBML


_VIDEO_SIGNATURES = [
    ((".mp4",), _is_mp4_like, "video/mp4"),
    ((".mov",), _is_mp4_like, "video/quicktime"),
    ((".webm",), _is_webm, "video/webm"),
]


def _verify_image(content: bytes):
    """用 PIL 真正解码校验，拒绝伪造扩展名 / 损坏 / 非图片文件。"""
    try:
        im = Image.open(io.BytesIO(content))
        im.verify()
        fmt = (im.format or "").upper()
        return _FORMAT_MAP.get(fmt)
    except Exception:
        return None


def _reencode(content: bytes, pil_format: str) -> bytes:
    """重新编码图片：剥离夹带载荷；只对超大图等比缩小，绝不放大，保证清晰度。"""
    if pil_format == "GIF":
        return content  # 保留动图
    with Image.open(io.BytesIO(content)) as im:
        out = io.BytesIO()
        w, h = im.size
        long_edge = max(w, h)
        if long_edge > MAX_IMAGE_EDGE:
            ratio = MAX_IMAGE_EDGE / long_edge
            im = im.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)
        if pil_format == "JPEG":
            im.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
        elif pil_format == "WEBP":
            im.save(out, format="WEBP", quality=92, method=4)
        else:  # PNG
            im.save(out, format="PNG", optimize=True)
        return out.getvalue()


async def _save_upload(content: bytes, ext: str, sub_dir_name: str = "images") -> str:
    filename = f"{uuid.uuid4().hex}{ext}"
    sub_dir = datetime.now().strftime("%Y%m")
    save_dir = settings.UPLOAD_DIR / sub_dir
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)
    return f"/uploads/{sub_dir}/{filename}"


@router.post("/image", response_model=Result,
             dependencies=[Depends(rate_limit("upload", 30, 60))])
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空，请重新选择图片")
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")
    # PIL 解码/重编码是 CPU 密集的同步操作（大图可达数百毫秒），
    # 放到线程池里做，避免阻塞事件循环
    detected = await run_in_threadpool(_verify_image, content)
    if not detected:
        raise HTTPException(status_code=400, detail="仅支持真实的 JPG/PNG/GIF/WEBP 图片，文件可能已损坏")
    ext, ctype, pil_fmt = detected
    if ctype not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="图片类型不被允许")
    try:
        content = await run_in_threadpool(_reencode, content, pil_fmt)
    except Exception:
        raise HTTPException(status_code=400, detail="图片处理失败，请更换图片后重试")
    url = await _save_upload(content, ext)
    return Result(data={"url": url})


@router.post("/video", response_model=Result,
             dependencies=[Depends(rate_limit("upload-video", 10, 60))])
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # 边读边限制大小，避免超大文件占满内存
    content = await file.read(settings.MAX_VIDEO_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="文件为空，请重新选择视频")
    if len(content) > settings.MAX_VIDEO_SIZE:
        raise HTTPException(status_code=400, detail="视频大小不能超过 50MB")
    head = content[:32]
    matched_ext = None
    for exts, checker, ctype in _VIDEO_SIGNATURES:
        if checker(head):
            matched_ext = exts[0]
            break
    if not matched_ext:
        raise HTTPException(status_code=400, detail="仅支持真实的 MP4/MOV/WebM 视频，文件可能已损坏")
    url = await _save_upload(content, matched_ext)
    await log_action(
        user_id=current_user.id, username=current_user.username, action="upload_video",
        detail=f"上传视频：{url}", request=request,
    )
    return Result(data={"url": url})
