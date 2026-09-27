"""图片审查层（可选）。

三种后端：
- sightengine：国外成熟的 NSFW / 违规图片 API，有免费额度，接入简单；
- generic    ：自定义 HTTP 图片审核接口（阿里云/腾讯云/自建服务的适配位）；
- local      ：本地轻量启发式（肤色占比 + 纹理方差），
               **只作为「疑似」提示、最多转人工复核，绝不参与自动拦截**，
              因为颜色启发式的误报率天然偏高（沙滩、泳装、木地板都会命中）。

设计原则：图片审查永远不阻塞内容发布 —— 超时/失败一律按「未检出」处理并记录。
"""
from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass, field

import httpx
from fastapi.concurrency import run_in_threadpool

from app.config import settings

from .config import AIConfig

logger = logging.getLogger("campus-wall")

_LOCAL_CATEGORY = "porn"


@dataclass
class ImageVerdict:
    checked: int = 0
    max_score: int = 0
    categories: list[str] = field(default_factory=list)
    details: list[dict] = field(default_factory=list)
    provider: str = ""
    error: str = ""
    local_only: bool = False       # True 表示结果仅来自本地启发式（不可用于拦截）

    def as_dict(self) -> dict:
        return {
            "checked": self.checked, "max_score": self.max_score,
            "categories": self.categories, "details": self.details,
            "provider": self.provider, "error": self.error,
            "local_only": self.local_only,
        }


def _resolve_local_path(url: str) -> str | None:
    """把 /uploads/xxx 映射到本地上传目录；其他形式返回 None。"""
    if not url or not url.startswith("/uploads/"):
        return None
    rel = url[len("/uploads/"):].lstrip("/")
    if not rel or ".." in rel:
        return None
    path = settings.UPLOAD_DIR / rel
    return str(path) if path.exists() else None


# ---------------- 本地启发式 ----------------
def _local_analyze_bytes(content: bytes) -> dict:
    """肤色占比 + 纹理方差。返回 {"score": 0-100, "skin_ratio": float}。"""
    from PIL import Image

    with Image.open(io.BytesIO(content)) as im:
        im = im.convert("RGB")
        im.thumbnail((256, 256))
        w, h = im.size
        if w < 8 or h < 8:
            return {"score": 0, "skin_ratio": 0.0}
        # 只统计画面中央区域，边缘背景（墙面/地板）不参与判定
        left, top = int(w * 0.2), int(h * 0.15)
        right, bottom = int(w * 0.8), int(h * 0.9)
        px = im.load()
        total = 0
        skin = 0
        lumas: list[int] = []
        for y in range(top, bottom, 2):
            for x in range(left, right, 2):
                r, g, b = px[x, y]
                total += 1
                lumas.append((r * 299 + g * 587 + b * 114) // 1000)
                # 经典 RGB 肤色判定（对黄种人肤色做了放宽）
                if r > 95 and g > 40 and b > 20 and r > g and r > b \
                        and (max(r, g, b) - min(r, g, b)) > 15 and abs(r - g) > 15:
                    # 再叠一层 YCbCr 判定，降低木色/沙色误报
                    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
                    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
                    if 77 <= cb <= 127 and 133 <= cr <= 173:
                        skin += 1
        if not total:
            return {"score": 0, "skin_ratio": 0.0}
        ratio = skin / total
        # 纹理方差：纯色大面积（墙面/地板）虽然肤色占比高，但方差极低，予以削弱
        if lumas:
            mean = sum(lumas) / len(lumas)
            var = sum((v - mean) ** 2 for v in lumas) / len(lumas)
        else:
            var = 0.0
        texture = min(1.0, (var ** 0.5) / 40.0)
        effective = ratio * (0.45 + 0.55 * texture)
        if effective < 0.28:
            score = 0
        elif effective < 0.45:
            score = int(40 + (effective - 0.28) * 120)
        else:
            score = min(90, int(60 + (effective - 0.45) * 200))
        return {"score": score, "skin_ratio": round(ratio, 3),
                "texture": round(texture, 3), "pixels": total}


async def _local_check(url: str) -> tuple[int, dict]:
    path = _resolve_local_path(url)
    if not path:
        return 0, {"url": url, "skipped": "本地文件不存在"}
    try:
        with open(path, "rb") as f:
            content = f.read(8 * 1024 * 1024)
        info = await run_in_threadpool(_local_analyze_bytes, content)
        return int(info.get("score", 0)), {"url": url, **info}
    except Exception as exc:
        return 0, {"url": url, "error": f"{type(exc).__name__}: {str(exc)[:100]}"}


# ---------------- Sightengine ----------------
async def _sightengine_check(url: str, cfg: AIConfig) -> tuple[int, dict]:
    endpoint = "https://api.sightengine.com/1.0/check.json"
    data = {
        "models": "nudity-2.1,weapon,offensive,gore-2.0",
        "api_user": cfg.image_api_user,
        "api_secret": cfg.image_api_secret,
    }
    path = _resolve_local_path(url)
    files = None
    if path:
        files = {"media": (path.rsplit("/", 1)[-1], open(path, "rb"), "image/jpeg")}
    else:
        data["url"] = url
    try:
        async with httpx.AsyncClient(timeout=cfg.image_timeout) as client:
            if files:
                resp = await client.post(endpoint, data=data, files=files)
            else:
                resp = await client.post(endpoint, data=data)
        if resp.status_code >= 400:
            return 0, {"url": url, "error": f"HTTP {resp.status_code}: {resp.text[:150]}"}
        obj = resp.json()
        if obj.get("status") != "success":
            return 0, {"url": url, "error": f"接口返回异常：{str(obj)[:150]}"}
        nudity = obj.get("nudity", {}) or {}
        sexual = float(nudity.get("sexual_activity", 0) or 0)
        display = float(nudity.get("sexual_display", 0) or 0)
        very_suggestive = float(nudity.get("very_suggestive", 0) or 0)
        suggestive = float(nudity.get("suggestive", 0) or 0)
        gore = float((obj.get("gore", {}) or {}).get("prob", 0) or 0)
        weapon = float((obj.get("weapon", {}) or {}).get("prob", 0) or 0)
        offensive = float((obj.get("offensive", {}) or {}).get("prob", 0) or 0)
        worst = max(sexual, display)
        score = int(min(100, max(
            worst * 100,
            very_suggestive * 85,
            suggestive * 55,
            gore * 100,
            weapon * 90,
            offensive * 70,
        )))
        cats = []
        if max(sexual, display, very_suggestive, suggestive) > 0.3:
            cats.append("porn")
        if gore > 0.3:
            cats.append("violence")
        if weapon > 0.3:
            cats.append("illegal")
        return score, {
            "url": url, "sexual_activity": sexual, "sexual_display": display,
            "very_suggestive": very_suggestive, "suggestive": suggestive,
            "gore": gore, "weapon": weapon, "offensive": offensive,
            "categories": cats,
        }
    except Exception as exc:
        return 0, {"url": url, "error": f"{type(exc).__name__}: {str(exc)[:120]}"}
    finally:
        if files:
            try:
                files["media"][1].close()
            except Exception:
                pass


# ---------------- 通用 HTTP 接口 ----------------
def _dig_score(obj) -> int:
    """从各种可能的返回结构里挖出 0-100 的风险分。"""
    if not isinstance(obj, dict):
        return 0
    for key in ("score", "risk_score", "probability", "prob", "confidence", "risk"):
        val = obj.get(key)
        if isinstance(val, (int, float)):
            v = float(val)
            return int(min(100, v * 100 if v <= 1 else v))
    for key in ("data", "result", "detail", "response"):
        if isinstance(obj.get(key), dict):
            got = _dig_score(obj[key])
            if got:
                return got
        if isinstance(obj.get(key), list) and obj[key]:
            got = _dig_score(obj[key][0])
            if got:
                return got
    return 0


async def _generic_check(url: str, cfg: AIConfig) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if cfg.image_api_key:
        headers["Authorization"] = f"Bearer {cfg.image_api_key}"
    payload = {"image_url": url, "url": url}
    path = _resolve_local_path(url)
    if path:
        try:
            with open(path, "rb") as f:
                payload["image_base64"] = base64.b64encode(f.read(8 * 1024 * 1024)).decode()
        except Exception:
            pass
    try:
        async with httpx.AsyncClient(timeout=cfg.image_timeout) as client:
            resp = await client.post(cfg.image_api_url, json=payload, headers=headers)
        if resp.status_code >= 400:
            return 0, {"url": url, "error": f"HTTP {resp.status_code}: {resp.text[:150]}"}
        obj = resp.json()
        score = _dig_score(obj)
        return score, {"url": url, "score": score, "raw": str(obj)[:300]}
    except Exception as exc:
        return 0, {"url": url, "error": f"{type(exc).__name__}: {str(exc)[:120]}"}


async def review_images(urls: list[str], cfg: AIConfig) -> ImageVerdict:
    """批量审查图片。任一图片超时/失败都不会抛出异常。"""
    verdict = ImageVerdict(provider=cfg.image_provider)
    if not cfg.image_enabled or not urls:
        return verdict
    targets = [u for u in urls if isinstance(u, str) and u.strip()][:9]
    if not targets:
        return verdict
    verdict.checked = len(targets)

    if cfg.image_provider == "local":
        verdict.local_only = True
        for url in targets:
            score, detail = await _local_check(url)
            verdict.details.append(detail)
            verdict.max_score = max(verdict.max_score, score)
    elif cfg.image_provider == "sightengine" and cfg.image_api_user and cfg.image_api_secret:
        for url in targets:
            score, detail = await _sightengine_check(url, cfg)
            verdict.details.append(detail)
            verdict.max_score = max(verdict.max_score, score)
            for c in detail.get("categories", []) or []:
                if c not in verdict.categories:
                    verdict.categories.append(c)
    elif cfg.image_provider == "generic" and cfg.image_api_url:
        for url in targets:
            score, detail = await _generic_check(url, cfg)
            verdict.details.append(detail)
            verdict.max_score = max(verdict.max_score, score)
    else:
        verdict.error = "图片审查已启用，但服务商参数不完整，本次跳过"

    if verdict.max_score and not verdict.categories:
        if verdict.max_score >= cfg.image_block_score:
            verdict.categories.append(_LOCAL_CATEGORY)
        else:
            verdict.categories.append(_LOCAL_CATEGORY)
    if verdict.error:
        logger.warning("图片审查未生效：%s", verdict.error)
    return verdict


async def test_provider(cfg: AIConfig, sample_url: str = "") -> dict:
    """后台「测试图片审查」：用一张测试图或给定 URL 跑一次。"""
    if cfg.image_provider == "none":
        return {"ok": False, "msg": "图片审查未启用"}
    if cfg.image_provider == "local":
        if not sample_url:
            return {"ok": True, "msg": "本地启发式已就绪（无需外部配置）"}
        score, detail = await _local_check(sample_url)
        return {"ok": True, "msg": f"本地检测完成，得分 {score}", "detail": detail}
    if not sample_url:
        return {"ok": False, "msg": "请先填写一张图片地址再测试"}
    if cfg.image_provider == "sightengine":
        score, detail = await _sightengine_check(sample_url, cfg)
    else:
        score, detail = await _generic_check(sample_url, cfg)
    ok = not detail.get("error")
    return {"ok": ok, "msg": "检测完成" if ok else detail.get("error", "调用失败"),
            "score": score, "detail": detail}
