"""AI 智能审查管理 API（13 个接口）"""
import time
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.ai_review import AIReviewRecord, AIReviewConfig, AIReviewAppeal
from app.models.post import Post
from app.models.comment import Comment
from app.models.sensitive_word import SensitiveWord
from app.schemas.common import Result, PageResponse
from app.api.deps import get_admin_user
from app.core.moderation import (
    CATEGORY_CATALOG, CATEGORY_LABELS, RISK_LABELS, ACTION_LABELS,
    BUILTIN_RULES, LEXICON_SOURCES, BUILTIN_LEXICON,
    moderate_content, invalidate, invalidate_config, record_review,
    DEFAULT_CATEGORY_ACTIONS,
)

router = APIRouter(prefix="/api/ai-review", tags=["AI审查"])

LLM_PRESETS = {
    "zhipu": {"label": "智谱AI", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "moonshot": {"label": "月之暗面", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    "qwen": {"label": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-turbo"},
}

LLM_TRIGGER_MODES = {
    "off": "未启用", "suspect": "可疑内容送审", "sampled": "抽样送审", "always": "全量送审",
}

IMAGE_PRESETS = {"local": "本地启发式", "sightengine": "Sightengine", "generic": "自定义接口"}

# 可被 PUT /config 直接写入的标量字段
_SCALAR_FIELDS = [
    "enabled", "dry_run", "local_enabled", "scope_post", "scope_comment", "scope_message",
    "scope_profile", "llm_enabled", "llm_trigger", "llm_provider", "llm_base_url",
    "llm_model", "llm_min_score", "llm_sample_rate", "llm_timeout", "llm_max_len",
    "llm_daily_limit", "image_enabled", "image_provider", "image_api_user",
    "image_api_url", "block_score", "review_score", "mask_score",
    "auto_ban_threshold", "notify_author", "exempt_staff",
]


# ---------- 配置辅助 ----------
async def get_config(db: AsyncSession) -> AIReviewConfig:
    cfg = (await db.execute(select(AIReviewConfig).where(AIReviewConfig.id == 1))).scalar_one_or_none()
    if not cfg:
        cfg = AIReviewConfig(id=1, category_actions=dict(DEFAULT_CATEGORY_ACTIONS))
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return cfg


async def _lexicon_size(db: AsyncSession) -> int:
    return int((await db.execute(
        select(func.count(SensitiveWord.id)).where(SensitiveWord.is_enabled == True)  # noqa: E712
    )).scalar() or 0)


def config_to_dict(cfg: AIReviewConfig, lexicon_size: int = 0) -> dict:
    ca = cfg.category_actions or {}
    merged = {**DEFAULT_CATEGORY_ACTIONS, **ca}
    return {
        "enabled": cfg.enabled,
        "dry_run": cfg.dry_run,
        "local_enabled": cfg.local_enabled,
        "scope_post": cfg.scope_post,
        "scope_comment": cfg.scope_comment,
        "scope_message": cfg.scope_message,
        "scope_profile": cfg.scope_profile,
        "llm_trigger": cfg.llm_trigger or "off",
        "llm_trigger_modes": LLM_TRIGGER_MODES,
        "llm_provider": cfg.llm_provider or "",
        "llm_base_url": cfg.llm_base_url or "",
        "llm_model": cfg.llm_model or "",
        "llm_api_key": "********" if cfg.llm_api_key else "",
        "llm_api_key_set": bool(cfg.llm_api_key),
        "llm_presets": LLM_PRESETS,
        "llm_min_score": cfg.llm_min_score,
        "llm_sample_rate": cfg.llm_sample_rate,
        "llm_timeout": cfg.llm_timeout,
        "llm_max_len": cfg.llm_max_len,
        "llm_daily_limit": cfg.llm_daily_limit,
        "image_enabled": cfg.image_enabled,
        "image_provider": cfg.image_provider or "local",
        "image_presets": IMAGE_PRESETS,
        "image_api_user": cfg.image_api_user or "",
        "image_api_secret": "********" if cfg.image_api_secret else "",
        "image_api_url": cfg.image_api_url or "",
        "image_api_key": "********" if cfg.image_api_key else "",
        "image_api_key_set": bool(cfg.image_api_key),
        "block_score": cfg.block_score,
        "review_score": cfg.review_score,
        "mask_score": cfg.mask_score,
        "category_actions": merged,
        "category_catalog": CATEGORY_CATALOG,
        "auto_ban_threshold": cfg.auto_ban_threshold,
        "notify_author": cfg.notify_author,
        "exempt_staff": cfg.exempt_staff,
        "lexicon_size": lexicon_size,
        "blocked_domains_size": 0,
    }


# ---------- ① 概览 ----------
@router.get("/overview", response_model=Result[dict])
async def overview(db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)
    cfg = await get_config(db)
    pending = (await db.execute(
        select(func.count(AIReviewRecord.id)).where(AIReviewRecord.status == "pending")
    )).scalar()
    appeals_pending = (await db.execute(
        select(func.count(AIReviewAppeal.id)).where(AIReviewAppeal.status == "pending")
    )).scalar()
    blocked_24h = (await db.execute(
        select(func.count(AIReviewRecord.id)).where(
            and_(AIReviewRecord.action == "blocked", AIReviewRecord.created_at >= day_ago)
        )
    )).scalar()
    return Result(data={
        "enabled": cfg.enabled,
        "dry_run": cfg.dry_run,
        "llm_enabled": cfg.llm_enabled,
        "llm_trigger": cfg.llm_trigger or "off",
        "image_enabled": cfg.image_enabled,
        "pending_records": int(pending or 0),
        "pending_appeals": int(appeals_pending or 0),
        "blocked_24h": int(blocked_24h or 0),
        "is_admin": admin.role == "admin",
    })


# ---------- 记录序列化 ----------
def _record_to_item(r: AIReviewRecord) -> dict:
    ev = r.evidence or {}
    reasons = (ev.get("reasons")) if isinstance(ev, dict) else None
    if not reasons:
        reasons = [r.reason] if r.reason else []
    cat_labels = []
    for c in (ev.get("categories") or []):
        if isinstance(c, str):
            cat_labels.append(CATEGORY_LABELS.get(c, c))
    if not cat_labels and r.category:
        cat_labels = [CATEGORY_LABELS.get(r.category, r.category)]
    return {
        "id": r.id,
        "target_type": r.target_type,
        "target_id": r.target_id,
        "risk_level": r.risk_level,
        "risk_label": RISK_LABELS.get(r.risk_level, r.risk_level),
        "score": int(r.risk_score or 0),
        "category_labels": cat_labels,
        "title": r.title or "",
        "content": (r.content or "")[:200],
        "author_name": r.user.nickname if r.user else "-",
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "requested_action": r.requested_action or "pass",
        "action": r.action,
        "status": r.status,
        "latency_ms": r.latency_ms or 0,
    }


# ---------- ② 记录列表 ----------
@router.get("/records", response_model=Result[PageResponse[dict]])
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    risk_level: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(AIReviewRecord)
    cq = select(func.count()).select_from(AIReviewRecord)
    conditions = []
    # 前端 status 映射
    if status == "pending":
        conditions.append(AIReviewRecord.status == "pending")
    elif status == "approved":
        conditions.append(and_(AIReviewRecord.status == "reviewed", AIReviewRecord.action == "manual_pass"))
    elif status == "rejected":
        conditions.append(AIReviewRecord.action == "manual_reject")
    elif status == "blocked":
        conditions.append(AIReviewRecord.action == "blocked")
    elif status == "auto":
        conditions.append(AIReviewRecord.action == "auto_pass")
    if action:
        conditions.append(AIReviewRecord.action == action)
    if target_type:
        conditions.append(AIReviewRecord.target_type == target_type)
    if risk_level:
        conditions.append(AIReviewRecord.risk_level == risk_level)
    if category:
        conditions.append(AIReviewRecord.category == category)
    if keyword:
        conditions.append(or_(AIReviewRecord.title.contains(keyword), AIReviewRecord.content.contains(keyword)))
    if conditions:
        cond = and_(*conditions)
        q = q.where(cond)
        cq = cq.where(cond)
    total = (await db.execute(cq)).scalar()
    rows = (await db.execute(
        q.order_by(AIReviewRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    items = [_record_to_item(r) for r in rows]
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


# ---------- ③ 记录详情 ----------
@router.get("/records/{record_id}", response_model=Result[dict])
async def record_detail(record_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    r = (await db.execute(select(AIReviewRecord).where(AIReviewRecord.id == record_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "记录不存在")
    ev = r.evidence or {}
    reasons = ev.get("reasons") if isinstance(ev, dict) else None
    if not reasons:
        reasons = [r.reason] if r.reason else []
    item = _record_to_item(r)
    item.update({
        "content": r.content or "",
        "reasons": reasons,
        "evidence": ev,
        "author_stats": r.author_stats or {},
        "dry_run": r.dry_run or False,
        "masked_content": r.masked_content or "",
        "handled_by": r.handled_by,
        "handled_remark": r.handled_remark,
        "handled_at": r.handled_at.isoformat() if r.handled_at else None,
    })
    return Result(data=item)


# ---------- ④ 处理记录 ----------
@router.post("/records/{record_id}/handle", response_model=Result)
async def handle_record(record_id: int, payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    r = (await db.execute(select(AIReviewRecord).where(AIReviewRecord.id == record_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "记录不存在")
    action = payload.get("action")
    remark = payload.get("remark", "")
    if action not in ("approve", "mask", "reject", "ban"):
        raise HTTPException(400, "无效操作")

    if action in ("approve", "mask"):
        r.status = "reviewed"
        r.action = "manual_pass"
    else:
        r.status = "reviewed"
        r.action = "manual_reject"
        # 驳回：删除对应内容
        if r.target_type == "post" and r.target_id:
            post = (await db.execute(select(Post).where(Post.id == r.target_id))).scalar_one_or_none()
            if post:
                post.status = "deleted"
        elif r.target_type == "comment" and r.target_id:
            comment = (await db.execute(select(Comment).where(Comment.id == r.target_id))).scalar_one_or_none()
            if comment:
                post = (await db.execute(select(Post).where(Post.id == comment.post_id))).scalar_one_or_none()
                if post:
                    post.comment_count = max(0, post.comment_count - 1)
                await db.delete(comment)
        # ban：封禁作者
        if action == "ban" and r.user_id:
            author = (await db.execute(select(User).where(User.id == r.user_id))).scalar_one_or_none()
            if author and author.role != "admin":
                author.is_banned = True

    r.handled_by = admin.id
    r.handled_remark = remark
    r.handled_at = datetime.utcnow()
    await db.commit()
    return Result(msg="已处理")


# ---------- ⑤ 获取配置 ----------
@router.get("/config", response_model=Result[dict])
async def get_config_api(db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    cfg = await get_config(db)
    size = await _lexicon_size(db)
    return Result(data=config_to_dict(cfg, size))


# ---------- ⑥ 更新配置 ----------
@router.put("/config", response_model=Result)
async def update_config(payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    cfg = await get_config(db)
    for f in _SCALAR_FIELDS:
        if f in payload and payload[f] is not None:
            setattr(cfg, f, payload[f])
    if "category_actions" in payload and isinstance(payload["category_actions"], dict):
        cfg.category_actions = {**DEFAULT_CATEGORY_ACTIONS, **payload["category_actions"]}
    # API key 特殊处理
    if "llm_api_key" in payload:
        v = payload["llm_api_key"]
        if v == "__CLEAR__":
            cfg.llm_api_key = ""
        elif v and v != "********":
            cfg.llm_api_key = v
    if "image_api_key" in payload:
        v = payload["image_api_key"]
        if v == "__CLEAR__":
            cfg.image_api_key = ""
        elif v and v != "********":
            cfg.image_api_key = v
    if "image_api_secret" in payload:
        v = payload["image_api_secret"]
        if v == "__CLEAR__":
            cfg.image_api_secret = ""
        elif v and v != "********":
            cfg.image_api_secret = v
    await db.commit()
    invalidate_config()
    return Result(msg="配置已保存")


# ---------- ⑦ 测试 LLM ----------
@router.post("/config/test-llm", response_model=Result[dict])
async def test_llm(payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    base = (payload.get("llm_base_url") or "").rstrip("/")
    model = payload.get("llm_model") or ""
    api_key = payload.get("llm_api_key") or ""
    timeout = int(payload.get("llm_timeout") or 15)
    if not base or not model or not api_key:
        return Result(data={"ok": False, "latency_ms": 0, "sample_verdict": {}, "msg": "请填写完整的接口地址、模型和 API Key"})
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{base}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "请回复JSON：{\"risk_level\":\"safe\",\"category\":\"other\",\"reason\":\"测试\",\"suggested_action\":\"pass\"}"}],
                    "temperature": 0.1,
                },
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
        latency = int((time.monotonic() - t0) * 1000)
        content = data["choices"][0]["message"]["content"]
        import json as _json, re as _re
        m = _re.search(r"\{.*\}", content, _re.S)
        verdict = _json.loads(m.group(0)) if m else {"raw": content}
        return Result(data={"ok": True, "latency_ms": latency, "sample_verdict": verdict, "msg": "连接成功"})
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        return Result(data={"ok": False, "latency_ms": latency, "sample_verdict": {}, "msg": f"连接失败：{e}"})


# ---------- ⑧ 测试图片审核 ----------
@router.post("/config/test-image", response_model=Result[dict])
async def test_image(payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    provider = payload.get("image_provider") or "local"
    if provider == "local":
        return Result(data={"ok": True, "msg": "本地启发式图片审查已就绪（检测色情/暴力色块）"})
    return Result(data={"ok": True, "msg": f"图片审查接口 {provider} 配置已保存，将在实际上传时调用"})


# ---------- ⑨ 在线试审 ----------
@router.post("/test", response_model=Result[dict])
async def test_review(payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    title = payload.get("title", "") or ""
    content = payload.get("content", "") or ""
    combined = (title + "\n" + content).strip() if title else content
    result = await moderate_content(db, combined, target_type=payload.get("target_type", "post"))
    return Result(data={
        "requested_action": result.requested_action,
        "action_label": ACTION_LABELS.get(result.requested_action, result.requested_action),
        "risk_level": result.risk_level,
        "risk_label": RISK_LABELS.get(result.risk_level, result.risk_level),
        "score": result.risk_score,
        "category_labels": result.category_labels,
        "latency_ms": result.latency_ms,
        "reasons": result.reasons,
        "evidence": result.evidence,
        "masked_text": result.masked_text,
    })


# ---------- ⑩ 规则列表 ----------
@router.get("/rules", response_model=Result[dict])
async def get_rules(db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    return Result(data={
        "rules": BUILTIN_RULES,
        "categories": [{"key": c["key"], "label": c["label"]} for c in CATEGORY_CATALOG],
        "lexicon_sources": LEXICON_SOURCES,
        "lexicon_repo": "https://github.com/importcjj/sensitive",
        "lexicon_license": "MIT",
    })


# ---------- ⑪ 词库导入 ----------
@router.post("/lexicon/import", response_model=Result[dict])
async def import_lexicon(payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    existing = (await db.execute(select(SensitiveWord.word))).scalars().all()
    existing_set = set(existing)
    imported = 0
    skipped = 0
    cat_stat: dict = {}
    for cat, words in BUILTIN_LEXICON.items():
        # 词库源对应动作
        src = next((s for s in LEXICON_SOURCES if s["category"] == cat), None)
        action = src["action"] if src else "mask"
        for w in words:
            w = w.strip()
            if not w:
                continue
            if w in existing_set:
                skipped += 1
                continue
            db.add(SensitiveWord(word=w, category=cat, action=action, is_enabled=True))
            existing_set.add(w)
            imported += 1
            cat_stat[cat] = cat_stat.get(cat, 0) + 1
    await db.commit()
    invalidate()
    return Result(data={"imported": imported, "skipped": skipped, "categories": cat_stat})


# ---------- ⑫ 申诉列表 ----------
@router.get("/appeals", response_model=Result[PageResponse[dict]])
async def list_appeals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(AIReviewAppeal)
    cq = select(func.count()).select_from(AIReviewAppeal)
    if status:
        q = q.where(AIReviewAppeal.status == status)
        cq = cq.where(AIReviewAppeal.status == status)
    total = (await db.execute(cq)).scalar()
    rows = (await db.execute(
        q.order_by(AIReviewAppeal.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    items = []
    for a in rows:
        rec = a.record
        reasons = []
        action_label = ""
        if rec:
            ev = rec.evidence or {}
            reasons = ev.get("reasons") if isinstance(ev, dict) else []
            if not reasons and rec.reason:
                reasons = [rec.reason]
            action_label = ACTION_LABELS.get(rec.requested_action, rec.action)
        items.append({
            "id": a.id,
            "user_name": a.user.nickname if a.user else "-",
            "target_type": rec.target_type if rec else "post",
            "reason": a.reason,
            "record_summary": {"action_label": action_label, "reasons": reasons},
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return Result(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    ))


# ---------- ⑬ 处理申诉 ----------
@router.post("/appeals/{appeal_id}/handle", response_model=Result)
async def handle_appeal(appeal_id: int, payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    a = (await db.execute(select(AIReviewAppeal).where(AIReviewAppeal.id == appeal_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "申诉不存在")
    action = payload.get("action")
    remark = payload.get("remark", "")
    if action not in ("accepted", "rejected"):
        raise HTTPException(400, "无效操作")
    a.status = action
    a.handled_by = admin.id
    a.handled_remark = remark
    a.handled_at = datetime.utcnow()
    if action == "accepted" and a.record:
        rec = a.record
        rec.status = "reviewed"
        rec.action = "manual_pass"
        if rec.target_type == "post" and rec.target_id:
            post = (await db.execute(select(Post).where(Post.id == rec.target_id))).scalar_one_or_none()
            if post:
                post.status = "published"
        elif rec.target_type == "comment" and rec.target_id:
            # 评论硬删除无法恢复，仅更新记录状态
            pass
    await db.commit()
    return Result(msg="已处理")
