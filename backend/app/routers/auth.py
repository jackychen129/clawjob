"""
ClawJob - 注册与登录（含 Google OAuth、邮箱验证码注册）
"""
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from urllib.parse import urlencode, quote
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import User, VerificationCode, Agent, get_db
from app.security import get_password_hash, create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Google OAuth 配置（从环境变量读取）
# GOOGLE_REDIRECT_URI 必须与 Google Cloud Console 中配置的「授权重定向 URI」完全一致（后端地址，如 http://localhost:8000/auth/google/callback）
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = (os.getenv("FRONTEND_URL", "http://localhost:3000")).rstrip("/")


class SendVerificationCodeBody(BaseModel):
    email: str


class RegisterBody(BaseModel):
    username: str
    email: str
    password: str
    verification_code: str  # 邮箱验证码，先调用 send-verification-code 获取


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterViaSkillBody(BaseModel):
    """Agent 通过 Skill 注册：仅填 Agent 信息，自动创建用户并返回专属 token"""
    agent_name: str
    description: str = ""
    agent_type: str = "general"


def _send_verification_email(email: str, code: str) -> bool:
    """发送验证码邮件；未配置 SMTP 时返回 False（开发环境可用验证码表或固定码）"""
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "0") or "0")
    user_smtp = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("SMTP_FROM", user_smtp or "noreply@clawjob.com").strip()
    if not host or not port or not user_smtp or not password:
        return False
    subject = os.getenv("EMAIL_VERIFICATION_SUBJECT", "ClawJob 注册验证码")
    body = f"您的验证码是：{code}，5 分钟内有效。如非本人操作请忽略。"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("ClawJob", from_addr))
    msg["To"] = email
    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            s.login(user_smtp, password)
            s.sendmail(from_addr, [email], msg.as_string())
        return True
    except Exception:
        return False


@router.post("/send-verification-code")
def send_verification_code(body: SendVerificationCodeBody, db: Session = Depends(get_db)):
    """向邮箱发送注册验证码（6 位数字），5 分钟内有效。未配置 SMTP 时使用开发用固定码。"""
    email = (body.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="请输入有效邮箱")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="该邮箱已注册，请直接登录")
    dev_code = os.getenv("VERIFICATION_CODE_DEV", "").strip()
    if dev_code:
        code = dev_code
    else:
        code = "".join(secrets.choice("0123456789") for _ in range(6))
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    # 同一邮箱只保留最新一条
    db.query(VerificationCode).filter(VerificationCode.email == email).delete()
    db.add(VerificationCode(email=email, code=code, expires_at=expires_at))
    db.commit()
    if not dev_code:
        _send_verification_email(email, code)
    return {"message": "验证码已发送，请查收邮件（未配置邮件服务时请使用开发环境验证码）"}


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    """用户注册（需先获取邮箱验证码）"""
    email = (body.email or "").strip().lower()
    code = (body.verification_code or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="请输入有效邮箱")
    if not code:
        raise HTTPException(status_code=400, detail="请输入验证码")
    row = (
        db.query(VerificationCode)
        .filter(VerificationCode.email == email, VerificationCode.code == code)
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=400, detail="验证码错误")
    if row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="邮箱已存在")
    user = User(
        username=body.username.strip(),
        email=email,
        hashed_password=get_password_hash(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.delete(row)
    db.commit()
    token = create_access_token(
        data={"sub": str(user.id), "type": "user"},
        expires_delta=timedelta(days=7),
    )
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "username": user.username}


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == body.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.hashed_password:
        raise HTTPException(status_code=401, detail="该账号仅支持 Google 登录")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(
        data={"sub": str(user.id), "type": "user"},
        expires_delta=timedelta(days=7),
    )
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "username": user.username}


@router.post("/register-via-skill")
def register_via_skill(body: RegisterViaSkillBody, db: Session = Depends(get_db)):
    """
    Agent 通过 Skill 注册：无需先有人类用户，自动创建用户与 Agent，并返回用户专属 token。
    调用方（如 OpenClaw）可将返回的 access_token 设为 CLAWJOB_ACCESS_TOKEN 后直接发任务、接任务。
    """
    name = (body.agent_name or "").strip() or "SkillAgent"
    for _ in range(10):
        short_id = secrets.token_hex(6)
        username = f"skill_{short_id}"
        email = f"skill_{short_id}@clawjob.local"
        if db.query(User).filter(User.username == username).first():
            continue
        if db.query(User).filter(User.email == email).first():
            continue
        user = User(
            username=username,
            email=email,
            hashed_password=None,
        )
        db.add(user)
        db.flush()
        agent = Agent(
            name=name[:255],
            description=(body.description or "")[:2000] or "",
            agent_type=(body.agent_type or "general")[:64],
            owner_id=user.id,
            capabilities=[],
            config={},
        )
        db.add(agent)
        db.commit()
        db.refresh(user)
        db.refresh(agent)
        token = create_access_token(
            data={"sub": str(user.id), "type": "user"},
            expires_delta=timedelta(days=365),
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "agent_id": agent.id,
            "agent_name": agent.name,
        }
    raise HTTPException(status_code=500, detail="生成唯一用户失败，请重试")


# ---------- Google OAuth ----------
@router.get("/google/status")
def google_oauth_status():
    """返回 Google OAuth 是否已配置及回调地址（用于排查 Sign in with Google 不工作）"""
    configured = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    config_error = None
    if not configured:
        if not GOOGLE_CLIENT_ID:
            config_error = "未配置 GOOGLE_CLIENT_ID"
        elif not GOOGLE_CLIENT_SECRET:
            config_error = "未配置 GOOGLE_CLIENT_SECRET"
        else:
            config_error = "未配置 GOOGLE_CLIENT_ID 或 GOOGLE_CLIENT_SECRET"
    return {
        "configured": configured,
        "config_error": config_error,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "frontend_url": FRONTEND_URL,
        "hint": "Google Cloud Console 中「授权重定向 URI」必须与 redirect_uri 完全一致",
    }


@router.get("/google")
def google_login():
    """跳转到 Google 授权页"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="未配置 GOOGLE_CLIENT_ID")
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=url)


def _frontend_error_url(error: str, use_hash: bool = True) -> str:
    """前端错误页 URL；use_hash 便于 SPA 从 hash 读取 error（避免被重定向丢掉 query）"""
    if use_hash:
        return f"{FRONTEND_URL}#/?error={quote(error)}"
    return f"{FRONTEND_URL}?error={quote(error)}"


@router.get("/google/callback")
def google_callback(code: str = None, state: str = None, db: Session = Depends(get_db)):
    """Google 回调：用 code 换 token，取用户信息，创建/登录用户并重定向到前端带 token"""
    if not code:
        return RedirectResponse(url=_frontend_error_url("missing_code"))
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url=_frontend_error_url("server_config"))

    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except Exception as e:
        return RedirectResponse(url=_frontend_error_url("token_exchange"))

    if r.status_code != 200:
        try:
            err_body = r.json()
            detail = err_body.get("error_description") or err_body.get("error", "")
            if detail and len(detail) < 80:
                return RedirectResponse(url=_frontend_error_url(f"token_exchange:{detail}"))
        except Exception:
            pass
        return RedirectResponse(url=_frontend_error_url("token_exchange"))
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        return RedirectResponse(url=_frontend_error_url("no_access_token"))

    try:
        with httpx.Client(timeout=10.0) as client:
            ui = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except Exception:
        return RedirectResponse(url=_frontend_error_url("userinfo"))
    if ui.status_code != 200:
        return RedirectResponse(url=_frontend_error_url("userinfo"))
    profile = ui.json()
    email = profile.get("email")
    name = profile.get("name") or (profile.get("email") or "").split("@")[0]
    if not email:
        return RedirectResponse(url=_frontend_error_url("no_email"))

    # 按 email 查找或创建用户（username 用 email 前缀或 name，唯一即可）
    user = db.query(User).filter(User.email == email).first()
    if not user:
        base_username = (name or email.split("@")[0]).replace(" ", "_")[:30]
        username = base_username
        n = 0
        while db.query(User).filter(User.username == username).first():
            n += 1
            username = f"{base_username}_{n}"
        user = User(
            username=username,
            email=email,
            hashed_password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "type": "user"},
        expires_delta=timedelta(days=7),
    )
    # 重定向到前端：用 query 传参（避免部分环境 302 时丢失 fragment）；前端读取后立即清除 URL
    safe_username = quote(user.username, safe="")
    callback_url = (
        f"{FRONTEND_URL}/?"
        f"from=google&token={quote(token)}&username={safe_username}&user_id={user.id}"
    )
    return RedirectResponse(url=callback_url)
