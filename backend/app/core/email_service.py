"""邮件发送服务。
- 注册验证邮件（含验证链接）
- 密码重置邮件（含重置链接）
- 配置SMTP后真实发送；未配置时开发模式打印链接到日志。
使用Python标准库smtplib + email，无需额外依赖。
"""
import logging
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email_verification import EmailVerification

logger = logging.getLogger("campus-wall.email")

# 验证链接有效期（小时）
VERIFY_EXPIRE_HOURS = 24
# 重置链接有效期（小时）
RESET_EXPIRE_HOURS = 1


def is_valid_email(email: str) -> bool:
    """简单邮箱格式校验。"""
    if not email or len(email) > 128:
        return False
    import re
    return bool(re.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def generate_token() -> str:
    """生成安全的验证token。"""
    return secrets.token_urlsafe(32)


async def create_verification(db: AsyncSession, email: str, scene: str, user_id: int | None = None) -> EmailVerification:
    """创建邮箱验证记录。"""
    token = generate_token()
    expire_hours = VERIFY_EXPIRE_HOURS if scene == "register" else RESET_EXPIRE_HOURS
    record = EmailVerification(
        email=email, token=token, scene=scene, user_id=user_id,
        used=False, expires_at=datetime.now(timezone.utc) + timedelta(hours=expire_hours),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def verify_token(db: AsyncSession, token: str, scene: str) -> EmailVerification | None:
    """验证token有效性（未使用、未过期、场景匹配）。"""
    record = (await db.execute(
        select(EmailVerification).where(
            EmailVerification.token == token,
            EmailVerification.scene == scene,
            EmailVerification.used == False,  # noqa: E712
            EmailVerification.expires_at > datetime.now(timezone.utc),
        )
    )).scalar_one_or_none()
    return record


async def mark_token_used(db: AsyncSession, record: EmailVerification) -> None:
    """标记token已使用。"""
    record.used = True
    await db.commit()


def build_verify_url(token: str, scene: str) -> str:
    """构建前端验证/重置页面URL。"""
    base = settings.SITE_URL or "https://cy.ihyuan.cn"
    path = "/verify-email" if scene == "register" else "/reset-password"
    return f"{base}{path}?token={quote(token)}"


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """发送邮件。配置SMTP后真实发送，否则开发模式打印。"""
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD):
        logger.info("[开发模式] 邮件未发送（未配置SMTP）\n  收件人: %s\n  主题: %s\n  内容: %s", to_email, subject, html_content[:500])
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((settings.SMTP_FROM_NAME or "校园墙", settings.SMTP_USER))
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT or 465, timeout=30)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 587, timeout=30)
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.error("邮件发送失败: %s", e, exc_info=True)
        return False


def send_verification_email(email: str, token: str, nickname: str = "同学") -> bool:
    """发送注册验证邮件。"""
    verify_url = build_verify_url(token, "register")
    html = f"""
    <div style="max-width:600px;margin:0 auto;padding:24px;font-family:-apple-system,sans-serif;">
      <h2 style="color:#1a1a1a;">邮箱验证</h2>
      <p style="color:#555;line-height:1.6;">亲爱的 {nickname}，你好！</p>
      <p style="color:#555;line-height:1.6;">感谢你注册校园墙，请点击下方按钮完成邮箱验证：</p>
      <div style="text-align:center;margin:32px 0;">
        <a href="{verify_url}" style="display:inline-block;padding:14px 40px;background:#1f9685;color:#fff;text-decoration:none;border-radius:8px;font-size:16px;">验证邮箱</a>
      </div>
      <p style="color:#999;font-size:13px;line-height:1.6;">如果按钮无法点击，请复制以下链接到浏览器打开：<br>{verify_url}</p>
      <p style="color:#999;font-size:13px;">链接有效期为24小时，过期请重新注册。</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#999;font-size:12px;">这是一封自动发送的邮件，请勿直接回复。</p>
    </div>
    """
    return send_email(email, "校园墙 - 邮箱验证", html)


def send_reset_email(email: str, token: str, nickname: str = "同学") -> bool:
    """发送密码重置邮件。"""
    reset_url = build_verify_url(token, "reset")
    html = f"""
    <div style="max-width:600px;margin:0 auto;padding:24px;font-family:-apple-system,sans-serif;">
      <h2 style="color:#1a1a1a;">重置密码</h2>
      <p style="color:#555;line-height:1.6;">亲爱的 {nickname}，你好！</p>
      <p style="color:#555;line-height:1.6;">你请求重置校园墙账号密码，请点击下方按钮进行重置：</p>
      <div style="text-align:center;margin:32px 0;">
        <a href="{reset_url}" style="display:inline-block;padding:14px 40px;background:#1f9685;color:#fff;text-decoration:none;border-radius:8px;font-size:16px;">重置密码</a>
      </div>
      <p style="color:#999;font-size:13px;line-height:1.6;">如果按钮无法点击，请复制以下链接到浏览器打开：<br>{reset_url}</p>
      <p style="color:#999;font-size:13px;">链接有效期为1小时，过期请重新申请。</p>
      <p style="color:#e74c3c;font-size:13px;">如果你没有请求重置密码，请忽略此邮件。</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#999;font-size:12px;">这是一封自动发送的邮件，请勿直接回复。</p>
    </div>
    """
    return send_email(email, "校园墙 - 重置密码", html)
