"""业务接口层的 AI 审查接线。

统一处理三件事，避免每个接口各写一遍：
1. 调用 ai_moderation.review()；
2. block 时**先提交审查记录与通知再抛 400**（否则事务回滚会把证据一起丢掉）；
3. review / mask 时给作者发站内通知，并按配置做违规累积自动封禁。
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ai_moderation
from app.core.ai_moderation import ACTION_LABELS, ReviewOutcome

logger = logging.getLogger("campus-wall")

_SCENE_LABEL = {
    "post": "帖子",
    "comment": "评论",
    "message": "私信",
    "profile": "个人资料",
}


async def guard_content(
    db: AsyncSession,
    *,
    target_type: str,
    user_id: int | None,
    title: str = "",
    content: str = "",
    images: list[str] | None = None,
    request: Request | None = None,
    notify: bool = True,
    actor_is_staff: bool = False,
) -> ReviewOutcome:
    """跑一遍 AI 审查并按结果执行统一处置。

    返回的 outcome.verdict 里带有打码后的 cleaned_title / cleaned_content，
    调用方应把它们写回业务表。
    """
    cfg = await ai_moderation.get_config()
    outcome = await ai_moderation.review(
        db, target_type=target_type, target_id=None, user_id=user_id,
        title=title, content=content, images=images,
    )
    if outcome.skipped:
        return outcome

    v = outcome.verdict
    real_action = v.requested_action
    # 工作人员豁免：管理员/审查员的内容只记录不自动处置，避免把自己锁死
    if actor_is_staff and cfg.exempt_staff and real_action in ("block", "review"):
        v.action = "pass"
        v.reasons.insert(0, "【工作人员豁免】仅记录，未自动处置")
        return outcome

    scene = _SCENE_LABEL.get(target_type, "内容")

    if real_action == "block" and v.action == "block":
        if notify and user_id:
            from app.core.activity import notify_user
            await notify_user(
                db, user_id, "内容未通过安全审查",
                f"你提交的{scene}未通过 AI 安全审查。{outcome.message()}",
            )
        await _maybe_auto_ban(db, cfg, user_id, scene)
        try:
            await db.commit()
        except Exception:
            logger.warning("审查拦截记录提交失败", exc_info=True)
        raise HTTPException(status_code=400, detail=outcome.message() or "内容未通过安全审查")

    if notify and user_id and real_action in ("review", "mask") and not cfg.dry_run:
        from app.core.activity import notify_user
        if real_action == "review":
            if target_type == "message":
                title_text = "私信触发安全审查"
                body = (f"你发送的私信被 AI 智能审查标记并记录，管理员会进行复核。"
                        f"判定要点：{'；'.join(v.reasons[:2]) or '综合风险分偏高'}")
            else:
                title_text = "内容已提交人工复核"
                body = (f"你提交的{scene}被 AI 智能审查标记为需要人工确认，"
                        f"通过后将公开展示。判定要点：{'；'.join(v.reasons[:2]) or '综合风险分偏高'}")
        else:
            title_text = "内容部分词语已打码"
            body = f"你提交的{scene}含不适宜直接展示的内容，已自动打码处理。{'；'.join(v.reasons[:1])}"
        await notify_user(db, user_id, title_text, body)

    if cfg.auto_ban_threshold and real_action in ("block", "review"):
        await _maybe_auto_ban(db, cfg, user_id, scene)
    return outcome


async def _maybe_auto_ban(db: AsyncSession, cfg, user_id: int | None, scene: str) -> None:
    """违规累积自动封禁（默认关闭，auto_ban_threshold=0）。"""
    if not user_id or not cfg.auto_ban_threshold:
        return
    try:
        stats = await ai_moderation.user_violation_stats(db, user_id, days=7)
        if stats["blocked"] < cfg.auto_ban_threshold:
            return
        from app.models.user import User
        user = await db.get(User, user_id)
        if not user or user.is_banned or user.role == "admin":
            return
        user.is_banned = True
        from app.core.activity import log_action, notify_user
        await notify_user(
            db, user_id, "账号已被限制",
            f"近 7 天内你有 {stats['blocked']} 条内容因违反社区规范被拦截，账号已被临时限制。"
            f"如有疑问可在「我的-申诉」提交申诉。",
        )
        await log_action(
            user_id=user_id, username=user.username, action="ai_auto_ban",
            target_type="user", target_id=user_id,
            detail=f"AI 审查违规累积自动封禁（7天内被拦截 {stats['blocked']} 次）",
        )
    except Exception:
        logger.warning("自动封禁判定失败", exc_info=True)


def block_message(outcome: ReviewOutcome) -> str:
    return f"{ACTION_LABELS.get(outcome.verdict.requested_action, '拦截')}：{outcome.message()}"


async def attach_record_target(db: AsyncSession, outcome: ReviewOutcome, target_id: int) -> None:
    """内容落库拿到主键后，回填审查记录的 target_id，保证后台能一键跳转。"""
    if not outcome.record_id:
        return
    try:
        await ai_moderation.attach_target(db, outcome.record_id, target_id)
    except Exception:
        logger.warning("回填审查记录 target_id 失败", exc_info=True)
