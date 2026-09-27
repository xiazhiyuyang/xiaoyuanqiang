import asyncio
import json
import re
import secrets
from urllib import request as urlrequest, parse, error as urlerror

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import rate_limit
from app.database import get_db
from app.config import settings
from app.core.security import hash_password, verify_password, create_access_token, token_version
from app.core.activity import log_action, is_register_open
from app.models.user import User
from app.core.levels import EXP_RULES, add_exp
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, Token, WechatLogin,
    ForgotQuestion, ForgotReset,
    EmailRegister, EmailVerify, EmailForgot, EmailReset, EmailLogin, ProfileCompletion,
)
from app.schemas.common import Result
from app.services import auth_service
from app.api.deps import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=Result[Token],
             dependencies=[Depends(rate_limit("register", 15, 3600))])
async def register(data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    if not await is_register_open():
        raise HTTPException(status_code=403, detail="当前已关闭注册，如有需要请联系管理员")
    if not data.agree:
        raise HTTPException(status_code=400, detail="请先阅读并同意《隐私政策与用户协议》后再注册")
    # 注册前检查IP/设备封禁（被封禁对象不能注册新账号绕过）
    from app.core.device_mgr import get_client_ip, check_ip_banned, check_device_banned
    client_ip = get_client_ip(request)
    ip_ban = await check_ip_banned(db, client_ip)
    if ip_ban:
        raise HTTPException(status_code=403, detail="当前网络环境已被限制注册，如有疑问请联系管理员")
    device_ban = await check_device_banned(db, data.device_code or "", getattr(data, "fingerprint_hash", None))
    if device_ban:
        raise HTTPException(status_code=403, detail="当前设备已被限制注册，如有疑问请联系管理员")
    # 用户名统一小写，避免同名不同大小写混淆
    exists = await db.execute(select(User).where(func.lower(User.username) == data.username))
    existing = exists.scalar_one_or_none()
    if existing:
        # 统一错误消息，避免用户名枚举（不区分已注册/已注销）
        raise HTTPException(status_code=400, detail="该用户名不可用，请换一个")
    # 手机号格式校验（选填，填写时必须是11位手机号）
    if data.phone and not re.fullmatch(r"^1[3-9]\d{9}$", data.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    # 学号格式校验（选填，6-20位字母数字）
    if data.student_id and not re.fullmatch(r"^[a-zA-Z0-9]{6,20}$", data.student_id):
        raise HTTPException(status_code=400, detail="学号格式不正确（6-20位字母或数字）")
    # bcrypt 是 CPU 密集的同步调用（cost=12 约 250ms），放到线程池执行，
    # 否则会阻塞事件循环，少量并发请求即可拖慢整个服务
    password_hash = await run_in_threadpool(hash_password, data.password)
    user = User(
        username=data.username,
        nickname=data.nickname,
        password_hash=password_hash,
        student_id=data.student_id,
        phone=data.phone,
        agreement_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    # 分配社区 UID
    from app.core.uid_allocator import allocate_normal_uid
    try:
        user.uid = await allocate_normal_uid(db, user.id)
        await db.commit()
    except Exception:
        pass  # UID 分配失败不阻断注册
    await log_action(
        user_id=user.id, username=user.username, action="register",
        detail=f"新用户注册：{user.nickname}", request=request,
    )
    # 注册即登录，记录设备信息
    from app.core.device_mgr import record_device_login
    await record_device_login(db, user.id, data.device_code or "", request, getattr(data, "fingerprint_hash", None))
    token = create_access_token({"sub": str(user.id), "pv": token_version(user)})
    return Result(data=Token(access_token=token, user=UserResponse.from_user(user)))


@router.post("/login", response_model=Result[Token],
             dependencies=[Depends(rate_limit("login", 10, 60))])
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    username = (data.username or "").strip().lower()
    result = await db.execute(select(User).where(func.lower(User.username) == username))
    user = result.scalar_one_or_none()
    if not user:
        from app.core.device_mgr import get_client_ip, record_login_failure
        client_ip = get_client_ip(request)
        await record_login_failure(db, client_ip, username, data.device_code, getattr(data, "fingerprint_hash", None), "用户不存在")
        await log_action(
            username=data.username, action="login_failed",
            detail="登录失败：用户名或密码错误", request=request, status="failed",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    # 已注销账号禁止登录
    if user.is_deleted:
        await log_action(
            user_id=user.id, username=user.username, action="login_failed",
            detail="已注销账号尝试登录", request=request, status="failed",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被注销")
    # 账户锁定检查（未过期抛 423；过期在内存中清空）
    await auth_service.assert_not_locked(user)
    # 密码校验（bcrypt 放线程池）
    if not await run_in_threadpool(verify_password, data.password, user.password_hash):
        from app.core.device_mgr import get_client_ip, record_login_failure
        client_ip = get_client_ip(request)
        await record_login_failure(db, client_ip, username, data.device_code, getattr(data, "fingerprint_hash", None), "密码错误")
        locked = await auth_service.record_failed_login(db, user)
        if locked:
            await log_action(
                user_id=user.id, username=user.username, action="login_failed",
                detail="连续登录失败5次，锁定15分钟", request=request, status="failed",
            )
            raise HTTPException(status_code=423, detail="账号已锁定，请15分钟后再试")
        await log_action(
            user_id=user.id, username=user.username, action="login_failed",
            detail="登录失败：用户名或密码错误", request=request, status="failed",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    # 登录成功：重置失败计数与锁定
    auth_service.clear_lockout(user)
    from app.core.device_mgr import get_client_ip, check_ip_banned, check_device_banned, record_device_login, clear_login_failures
    client_ip = get_client_ip(request)
    # 登录成功清空该IP的失败记录
    await clear_login_failures(db, client_ip)
    if user.is_banned:
        await log_action(
            user_id=user.id, username=user.username, action="login_failed",
            detail="被封禁账号尝试登录", request=request, status="failed",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被封禁，如有疑问请联系管理员")
    # 检查IP封禁
    ip_ban = await check_ip_banned(db, client_ip)
    if ip_ban:
        await log_action(
            user_id=user.id, username=user.username, action="login_failed",
            detail=f"被封禁IP尝试登录：{client_ip}，原因：{ip_ban.reason or '未填写'}", request=request, status="failed",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前IP已被封禁，如有疑问请联系管理员")
    # 检查设备封禁（同时检查设备码和指纹哈希）
    fingerprint_hash = getattr(data, "fingerprint_hash", None)
    device_ban = await check_device_banned(db, data.device_code or "", fingerprint_hash)
    if device_ban:
        await log_action(
            user_id=user.id, username=user.username, action="login_failed",
            detail=f"被封禁设备尝试登录：{data.device_code}，原因：{device_ban.reason or '未填写'}", request=request, status="failed",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前设备已被封禁，如有疑问请联系管理员")
    # 检查注销冷静期是否到期，到期则执行软删除
    from app.api.users import check_and_execute_deletion
    if await check_and_execute_deletion(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已注销，如有疑问请联系管理员")
    # 每日首次登录奖励经验
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if user.last_login_date != today:
        user.last_login_date = today
        await add_exp(db, user, EXP_RULES["login"], "login")
    # 记录登录设备信息（含指纹哈希）
    await record_device_login(db, user.id, data.device_code or "", request, fingerprint_hash)
    await log_action(
        user_id=user.id, username=user.username, action="login",
        detail=f"用户登录，IP：{client_ip}", request=request,
    )
    await db.commit()
    token = create_access_token({"sub": str(user.id), "pv": token_version(user)})
    return Result(data=Token(access_token=token, user=UserResponse.from_user(user)))


@router.post("/forgot/question", response_model=Result[dict],
             dependencies=[Depends(rate_limit("forgot", 8, 600))])
async def forgot_question(data: ForgotQuestion, db: AsyncSession = Depends(get_db)):
    """找回密码第一步：按用户名取回密保问题。"""
    username = data.username.strip().lower()
    result = await db.execute(select(User).where(func.lower(User.username) == username))
    user = result.scalar_one_or_none()
    question = user.security_question if user and user.security_question else None
    return Result(data={"question": question}, msg="ok" if question else "该账号暂未设置密保问题，请联系管理员重置密码")


@router.post("/forgot/reset", response_model=Result,
             dependencies=[Depends(rate_limit("forgot", 8, 600))])
async def forgot_reset(
    data: ForgotReset,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """找回密码第二步：校验密保答案后重置密码。"""
    username = data.username.strip().lower()
    result = await db.execute(select(User).where(func.lower(User.username) == username))
    user = result.scalar_one_or_none()
    answer = (data.answer or "").strip().lower()
    answer_ok = False
    if user and user.security_answer_hash:
        answer_ok = await run_in_threadpool(verify_password, answer, user.security_answer_hash)
    if not answer_ok:
        await log_action(
            username=data.username, action="forgot_failed",
            detail="找回密码密保答案错误", request=request, status="failed",
        )
        raise HTTPException(status_code=400, detail="密保答案不正确，请重试")
    if user.is_deleted:
        raise HTTPException(status_code=403, detail="账号已被注销")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="账号已被封禁")
    user.password_hash = await run_in_threadpool(hash_password, data.new_password)
    await db.commit()
    await log_action(
        user_id=user.id, username=user.username, action="password_reset",
        detail="通过密保问题找回密码", request=request,
    )
    return Result(msg="密码已重置，请使用新密码登录")


async def _wechat_code2openid(code: str, scene: str) -> str:
    """用 code 换微信 openid。mp=小程序 jscode2session；open=公众号H5/App oauth2"""
    if scene == "mp":
        app_id = settings.WECHAT_APP_ID
        app_secret = settings.WECHAT_APP_SECRET
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": app_id, "secret": app_secret,
            "js_code": code, "grant_type": "authorization_code",
        }
    else:
        app_id = settings.WECHAT_OPEN_APP_ID or settings.WECHAT_APP_ID
        app_secret = settings.WECHAT_OPEN_APP_SECRET or settings.WECHAT_APP_SECRET
        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        params = {
            "appid": app_id, "secret": app_secret,
            "code": code, "grant_type": "authorization_code",
        }
    if not app_id or not app_secret:
        raise HTTPException(status_code=503, detail="服务端未配置微信登录（缺少 WECHAT_APP_ID/SECRET）")

    def _do_request() -> dict:
        full_url = f"{url}?{parse.urlencode(params)}"
        with urlrequest.urlopen(full_url, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        data = await asyncio.to_thread(_do_request)
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="微信服务暂时不可用，请稍后再试")
    if "openid" not in data:
        raise HTTPException(
            status_code=400,
            detail=f"微信登录失败：{data.get('errmsg', 'code 无效或已过期')}（{data.get('errcode')}）",
        )
    return data["openid"]


@router.post("/wechat", response_model=Result[Token],
             dependencies=[Depends(rate_limit("wechat", 5, 60))])
async def wechat_login(data: WechatLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """微信一键登录：小程序传 uni.login 的 code；H5/App 传网页授权 code 并带 scene=open"""
    openid = await _wechat_code2openid(data.code, data.scene)
    result = await db.execute(select(User).where(User.wechat_openid == openid))
    user = result.scalar_one_or_none()
    is_new = False
    if not user:
        random_hash = await run_in_threadpool(hash_password, secrets.token_hex(16))
        user = User(
            username=f"wx_{secrets.token_hex(5)}",
            nickname=f"微信用户{secrets.randbelow(10000):04d}",
            password_hash=random_hash,
            wechat_openid=openid,
            need_profile_completion=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new = True
    if user.is_deleted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被注销")
    if user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被封禁，如有疑问请联系管理员")
    await log_action(
        user_id=user.id, username=user.username,
        action="register" if is_new else "login",
        detail="微信登录" + ("（首次注册）" if is_new else ""), request=request,
    )
    token = create_access_token({"sub": str(user.id), "pv": token_version(user)})
    return Result(data=Token(access_token=token, user=UserResponse.from_user(user)))


# ==================== 邮箱注册/登录/找回 ====================

@router.post("/email/register", response_model=Result[dict])
async def email_register(data: EmailRegister, request: Request, db: AsyncSession = Depends(get_db)):
    from app.core.email_service import is_valid_email, create_verification, send_verification_email
    from app.core.device_mgr import get_client_ip, check_ip_banned, check_device_banned
    if not await is_register_open():
        raise HTTPException(status_code=403, detail="当前已关闭注册")
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="密码至少8位")
    client_ip = get_client_ip(request)
    if await check_ip_banned(db, client_ip):
        raise HTTPException(status_code=403, detail="当前网络环境已被限制注册")
    if await check_device_banned(db, data.device_code or "", getattr(data, "fingerprint_hash", None)):
        raise HTTPException(status_code=403, detail="当前设备已被限制注册")
    if (await db.execute(select(User).where(func.lower(User.username) == data.username.lower()))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该用户名不可用，请换一个")
    if (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    user = User(
        username=data.username, nickname=data.nickname.strip(),
        password_hash=hash_password(data.password),
        email=data.email.lower(), email_verified=False,
        student_id=data.student_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    from app.core.uid_allocator import allocate_normal_uid
    user.uid = await allocate_normal_uid(db, user.id)
    await db.commit()
    record = await create_verification(db, data.email.lower(), "register", user.id)
    sent = send_verification_email(data.email.lower(), record.token, data.nickname)
    await log_action(user_id=user.id, username=user.username, action="register",
                     detail=f"邮箱注册（{'邮件已发送' if sent else '开发模式'}）", request=request)
    return Result(data={
        "user_id": user.id, "email": data.email.lower(), "email_sent": sent,
        "dev_verify_url": None if sent else f"{settings.SITE_URL}/verify-email?token={record.token}",
    }, msg="注册成功，请查收邮件完成验证" if sent else "注册成功（开发模式）")


@router.post("/email/verify", response_model=Result[Token])
async def email_verify(data: EmailVerify, request: Request, db: AsyncSession = Depends(get_db)):
    from app.core.email_service import verify_token, mark_token_used
    record = await verify_token(db, data.token, "register")
    if not record:
        raise HTTPException(status_code=400, detail="验证链接无效或已过期")
    user = (await db.execute(select(User).where(User.id == record.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="邮箱已验证")
    user.email_verified = True
    await mark_token_used(db, record)
    await db.commit()
    token = create_access_token({"sub": str(user.id), "pv": token_version(user)})
    return Result(data=Token(access_token=token, user=UserResponse.from_user(user)))


@router.post("/email/forgot", response_model=Result[dict])
async def email_forgot(data: EmailForgot, request: Request, db: AsyncSession = Depends(get_db)):
    from app.core.email_service import is_valid_email, create_verification, send_reset_email
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    user = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    if user and not user.is_deleted:
        record = await create_verification(db, data.email.lower(), "reset", user.id)
        sent = send_reset_email(data.email.lower(), record.token, user.nickname)
        return Result(data={
            "email_sent": sent,
            "dev_reset_url": None if sent else f"{settings.SITE_URL}/reset-password?token={record.token}",
        }, msg="重置链接已发送到你的邮箱" if sent else "重置链接已生成（开发模式）")
    return Result(data={"email_sent": False}, msg="如果该邮箱已注册，重置链接将发送到邮箱")


@router.post("/email/reset", response_model=Result[dict])
async def email_reset(data: EmailReset, request: Request, db: AsyncSession = Depends(get_db)):
    from app.core.email_service import verify_token, mark_token_used
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="密码至少8位")
    record = await verify_token(db, data.token, "reset")
    if not record:
        raise HTTPException(status_code=400, detail="重置链接无效或已过期")
    user = (await db.execute(select(User).where(User.id == record.user_id))).scalar_one_or_none()
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = hash_password(data.password)
    await mark_token_used(db, record)
    await db.commit()
    return Result(data={}, msg="密码重置成功，请使用新密码登录")


@router.post("/email/login", response_model=Result[Token])
async def email_login(data: EmailLogin, request: Request, db: AsyncSession = Depends(get_db)):
    from app.core.device_mgr import get_client_ip, check_ip_banned, check_device_banned, record_device_login, clear_login_failures
    from app.core.email_service import is_valid_email
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    client_ip = get_client_ip(request)
    if await check_ip_banned(db, client_ip):
        raise HTTPException(status_code=403, detail="当前网络环境已被限制登录")
    if await check_device_banned(db, data.device_code or "", getattr(data, "fingerprint_hash", None)):
        raise HTTPException(status_code=403, detail="当前设备已被限制登录")
    user = (await db.execute(select(User).where(User.email == data.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="邮箱未验证，请先验证邮箱")
    if user.is_deleted:
        raise HTTPException(status_code=403, detail="账号已被注销")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="账号已被封禁，如有疑问请联系管理员")
    await clear_login_failures(db, client_ip)
    await record_device_login(db, user.id, data.device_code or "", request,
                              fingerprint_hash=getattr(data, "fingerprint_hash", None))
    token = create_access_token({"sub": str(user.id), "pv": token_version(user)})
    return Result(data=Token(access_token=token, user=UserResponse.from_user(user)))


@router.post("/me/complete-profile", response_model=Result[UserResponse])
async def complete_profile(data: ProfileCompletion, request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    if data.username:
        if not re.fullmatch(r"^[A-Za-z0-9_]{3,32}$", data.username):
            raise HTTPException(status_code=400, detail="用户名格式不正确")
        exists = await db.execute(select(User).where(func.lower(User.username) == data.username.lower(), User.id != current_user.id))
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该用户名已被使用")
        current_user.username = data.username
    if data.nickname:
        current_user.nickname = data.nickname.strip()
    if data.password:
        if len(data.password) < 8:
            raise HTTPException(status_code=400, detail="密码至少8位")
        current_user.password_hash = hash_password(data.password)
    if data.email:
        from app.core.email_service import is_valid_email
        if not is_valid_email(data.email):
            raise HTTPException(status_code=400, detail="邮箱格式不正确")
        exists = await db.execute(select(User).where(User.email == data.email.lower(), User.id != current_user.id))
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该邮箱已被使用")
        current_user.email = data.email.lower()
        current_user.email_verified = False
    current_user.need_profile_completion = False
    await db.commit()
    await db.refresh(current_user)
    return Result(data=UserResponse.from_user(current_user))

