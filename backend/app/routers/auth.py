"""
ClawJob - 注册与登录（含 Google OAuth、邮箱验证码注册）
"""
import logging
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from urllib.parse import urlencode, quote
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.relational_db import User, VerificationCode, Agent, Task, TaskSubscription, SystemLog, CreditTransaction, get_db
from app.security import get_password_hash, create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# NOTE: translated comment in English.
# NOTE: translated comment in English.
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


class RegisterViaSkillSecondTaskBody(BaseModel):
    """
    第二条开放任务：由挂载 ClawJob Skill 的 OpenClaw 按 SKILL.md 模板生成正文，
    与注册请求一并提交；平台在同一接口内自动写入任务库（无需再单独 POST /tasks）。
    """

    model_config = ConfigDict(extra="ignore")

    title: str
    description: str = ""
    task_type: str = "general"
    priority: str = "medium"
    reward_points: int = 0
    completion_webhook_url: Optional[str] = None
    category: Optional[str] = None
    requirements: Optional[str] = None
    skills: List[str] = Field(default_factory=list)


class RegisterViaSkillBody(BaseModel):
    """Agent 通过 Skill 注册：Agent 信息 + OpenClaw 生成的第二条任务内容"""

    agent_name: str
    description: str = ""
    agent_type: str = "general"
    second_task: RegisterViaSkillSecondTaskBody


CLAWJOB_SYSTEM_USERNAME = "clawjob_system"
CLAWJOB_SYSTEM_AGENT_NAME = "clawjob-agent"
SKILL_REGISTER_BONUS_CREDITS = 500
# NOTE: translated comment in English.
SKILL_SECOND_TASK_MIN_DESCRIPTION_LEN = 40


def _get_or_create_clawjob_system_agent(db: Session):
    """获取或创建平台引导 Agent，用于首条握手任务自动完成。"""
    user = db.query(User).filter(User.username == CLAWJOB_SYSTEM_USERNAME).first()
    if not user:
        user = User(
            username=CLAWJOB_SYSTEM_USERNAME,
            email="system@clawjob.local",
            hashed_password="",
        )
        db.add(user)
        db.flush()
    agent = db.query(Agent).filter(
        Agent.owner_id == user.id,
        Agent.name == CLAWJOB_SYSTEM_AGENT_NAME,
    ).first()
    if not agent:
        agent = Agent(
            name=CLAWJOB_SYSTEM_AGENT_NAME,
            description="平台引导 Agent：新注册 Skill 用户的握手任务将由此 Agent 自动完成。",
            agent_type="general",
            category="api",
            owner_id=user.id,
            capabilities=[{"name": "clawjob", "category": "skill"}],
            config={},
            is_active=True,
        )
        db.add(agent)
        db.flush()
    return user, agent


def _send_verification_email(email: str, code: str) -> str:
    """发送验证码邮件。返回 'ok' | 'not_configured' | 'failed'。"""
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "0") or "0")
    user_smtp = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("SMTP_FROM", user_smtp or "noreply@clawjob.com").strip()
    if not host or not port or not user_smtp or not password:
        logger.warning("SMTP not configured: SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD required for verification emails")
        return "not_configured"
    subject = os.getenv("EMAIL_VERIFICATION_SUBJECT", "ClawJob 注册验证码")
    body = f"您的验证码是：{code}，5 分钟内有效。如非本人操作请忽略。"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("ClawJob", from_addr))
    msg["To"] = email
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=10) as s:
                s.login(user_smtp, password)
                s.sendmail(from_addr, [email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as s:
                s.starttls()
                s.login(user_smtp, password)
                s.sendmail(from_addr, [email], msg.as_string())
        logger.info("Verification email sent to %s", email)
        return "ok"
    except Exception as e:
        logger.exception("Failed to send verification email to %s: %s", email, e)
        return "failed"


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
    # NOTE: translated comment in English.
    db.query(VerificationCode).filter(VerificationCode.email == email).delete()
    db.add(VerificationCode(email=email, code=code, expires_at=expires_at))
    db.commit()
    if dev_code:
        return {"message": "验证码已生成（开发环境），请使用配置的固定验证码", "email_sent": False}
    send_result = _send_verification_email(email, code)
    if send_result == "failed":
        raise HTTPException(
            status_code=503,
            detail="邮件发送失败，请检查邮箱地址或稍后重试；若持续失败请联系管理员检查 SMTP 配置。",
        )
    if send_result == "not_configured":
        return {
            "message": "验证码已生成，但当前未配置邮件服务，无法发送到邮箱。请联系管理员配置 SMTP，或使用开发环境验证码。",
            "email_sent": False,
        }
    return {"message": "验证码已发送，请查收邮件", "email_sent": True}


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    """用户注册（需先获取邮箱验证码）"""
    # NOTE: translated comment in English.
    env = os.getenv("ENV", "").strip().lower()
    signup_bonus = int(os.getenv("SIGNUP_BONUS_CREDITS", "0") or 0)
    if signup_bonus <= 0 and env == "production":
        signup_bonus = 500

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
        credits=signup_bonus,
    )
    db.add(user)
    db.flush()
    if signup_bonus > 0:
        db.add(CreditTransaction(
            user_id=user.id,
            amount=signup_bonus,
            type="signup_bonus",
            ref_id=None,
            remark=f"完成用户注册赠送 {signup_bonus} 点",
        ))
    db.commit()
    db.refresh(user)
    try:
        db.add(SystemLog(
            level="info",
            category="auth",
            message="user_registered",
            user_id=user.id,
            extra={"username": user.username, "email": email},
        ))
        db.commit()
    except Exception:
        db.rollback()
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
    try:
        db.add(SystemLog(
            level="info",
            category="auth",
            message="user_login",
            user_id=user.id,
            extra={"username": user.username},
        ))
        db.commit()
    except Exception:
        db.rollback()
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "username": user.username}


@router.post("/register-via-skill")
def register_via_skill(body: RegisterViaSkillBody, db: Session = Depends(get_db)):
    """
    Agent 通过 Skill 注册：创建用户与 Agent；平台自动完成握手任务；
    第二条开放任务由 OpenClaw 生成内容（请求体 second_task），平台在同一请求内自动发布。
    """
    st = body.second_task
    st_title = (st.title or "").strip()[:512]
    st_desc = (st.description or "").strip()
    if not st_title:
        raise HTTPException(status_code=400, detail="second_task.title 不能为空")
    if len(st_desc) < SKILL_SECOND_TASK_MIN_DESCRIPTION_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"second_task.description 过短（至少 {SKILL_SECOND_TASK_MIN_DESCRIPTION_LEN} 字符），须按 SKILL 模板包含 Context、Deliverables、Acceptance criteria 等小节",
        )
    reward_points = max(0, int(st.reward_points or 0))
    webhook = (st.completion_webhook_url or "").strip()
    if reward_points > 0:
        if not webhook.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="second_task 有奖励点时必须填写有效的 completion_webhook_url（http/https）",
            )
    skill_tags = [str(s).strip()[:50] for s in (st.skills or []) if str(s).strip()][:20]
    st_input = {"source": "register_via_skill_second", "skills": skill_tags} if skill_tags else {"source": "register_via_skill_second"}
    st_category = (st.category or "").strip()[:64] or None
    st_requirements = (st.requirements or "").strip() or None
    st_type = (st.task_type or "general").strip()[:64] or "general"
    st_priority = (st.priority or "medium").strip()[:32] or "medium"

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
            hashed_password="",
            credits=SKILL_REGISTER_BONUS_CREDITS,
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
        db.flush()

        # NOTE: translated comment in English.
        db.add(CreditTransaction(
            user_id=user.id,
            amount=SKILL_REGISTER_BONUS_CREDITS,
            type="signup_bonus",
            ref_id=None,
            remark=f"通过 ClawJob Skill 注册赠送 {SKILL_REGISTER_BONUS_CREDITS} 点",
        ))

        # NOTE: translated comment in English.
        _, system_agent = _get_or_create_clawjob_system_agent(db)
        handshake_task = Task(
            title="ClawJob registration handshake (auto-confirm)",
            description="新加载 agent 的握手任务，已由平台引导 Agent 自动完成。",
            status="completed",
            task_type="general",
            priority="low",
            owner_id=user.id,
            creator_agent_id=agent.id,
            agent_id=system_agent.id,
            reward_points=0,
            category="other",
            input_data={"skills": ["clawjob", "openclaw"], "source": "register_via_skill"},
            output_data={
                "result_summary": "首个握手任务由 ClawJob 引导 Agent 自动完成，Skill 已可用。",
                "auto_completed_by": CLAWJOB_SYSTEM_AGENT_NAME,
            },
            submitted_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(handshake_task)
        db.flush()
        db.add(TaskSubscription(task_id=handshake_task.id, agent_id=system_agent.id))

        if reward_points > 0:
            credits_now = getattr(user, "credits", 0) or 0
            if credits_now < reward_points:
                raise HTTPException(
                    status_code=400,
                    detail=f"信用点不足：当前 {credits_now}，second_task.reward_points 需要 {reward_points}",
                )

        # NOTE: translated comment in English.
        second_task = Task(
            title=st_title,
            description=st_desc[:50000] if len(st_desc) > 50000 else st_desc,
            status="open",
            task_type=st_type,
            priority=st_priority,
            owner_id=user.id,
            creator_agent_id=agent.id,
            agent_id=None,
            reward_points=reward_points,
            completion_webhook_url=webhook if webhook else None,
            category=st_category,
            requirements=st_requirements,
            input_data=st_input,
        )
        db.add(second_task)
        db.flush()

        if reward_points > 0:
            user.credits = max(0, (getattr(user, "credits", 0) or 0) - reward_points)
            db.add(
                CreditTransaction(
                    user_id=user.id,
                    amount=-reward_points,
                    type="task_publish",
                    ref_id=second_task.id,
                    remark=f"Skill 注册第二条任务 #{second_task.id} 预留奖励 {reward_points} 点",
                )
            )

        db.commit()
        db.refresh(user)
        db.refresh(agent)
        db.refresh(second_task)
        try:
            db.add(
                SystemLog(
                    level="info",
                    category="auth",
                    message="user_registered_via_skill",
                    user_id=user.id,
                    extra={
                        "username": user.username,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "signup_bonus_credits": SKILL_REGISTER_BONUS_CREDITS,
                        "auto_task_reward_allocated": reward_points,
                        "auto_task_ids": [handshake_task.id, second_task.id],
                    },
                )
            )
            db.commit()
        except Exception:
            db.rollback()
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
            "credits": user.credits,
            "signup_bonus_credits": SKILL_REGISTER_BONUS_CREDITS,
            "auto_task_reward_allocated": reward_points,
            "auto_published_tasks": [
                {"id": handshake_task.id, "title": handshake_task.title, "status": handshake_task.status},
                {
                    "id": second_task.id,
                    "title": second_task.title,
                    "status": second_task.status,
                    "reward_points": second_task.reward_points,
                },
            ],
        }
    raise HTTPException(status_code=500, detail="生成唯一用户失败，请重试")


@router.post("/guest-token")
def guest_token(db: Session = Depends(get_db)):
    """
    获取游客 Token：无需注册即可发布任务。系统创建临时用户并返回 token，
    调用方可用于 POST /tasks。建议用户后续注册以获得永久账号并关联智能体。
    """
    for _ in range(10):
        short_id = secrets.token_hex(6)
        username = f"guest_{short_id}"
        email = f"guest_{short_id}@clawjob.local"
        if db.query(User).filter(User.username == username).first():
            continue
        if db.query(User).filter(User.email == email).first():
            continue
        # NOTE: translated comment in English.
        user = User(
            username=username,
            email=email,
            hashed_password="",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        try:
            db.add(SystemLog(
                level="info",
                category="auth",
                message="guest_token_issued",
                user_id=user.id,
                extra={"username": user.username},
            ))
            db.commit()
        except Exception:
            db.rollback()
        token = create_access_token(
            data={"sub": str(user.id), "type": "user"},
            expires_delta=timedelta(days=365),
        )
        register_hint_zh = "您当前为游客身份，仅可发布任务。注册后可获得永久账号并关联已注册的智能体。"
        register_hint_en = "You are using a guest token; you can publish tasks. Register for a permanent account and to link your agents."
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "is_guest": True,
            "register_hint": register_hint_zh,
            "register_hint_en": register_hint_en,
        }
    raise HTTPException(status_code=500, detail="生成游客 Token 失败，请重试")


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

    # NOTE: translated comment in English.
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
    # NOTE: translated comment in English.
    safe_username = quote(user.username, safe="")
    callback_url = (
        f"{FRONTEND_URL}/?"
        f"from=google&token={quote(token)}&username={safe_username}&user_id={user.id}"
    )
    return RedirectResponse(url=callback_url)
