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
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.relational_db import (
    User, VerificationCode, Agent, Task, TaskSubscription, SystemLog,
    CreditTransaction, InternalMessage, get_db,
)
from app.security import get_password_hash, create_access_token, verify_password, limiter
from app.services import referrals as _rf
from app.services import community as _community
from app.services.onboarding_quest import onboarding_tasks_for_register

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
    referral_code: Optional[str] = None  # 可选：邀请码，绑定后好友首单完成时双方获得返点


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

    model_config = ConfigDict(extra="ignore")

    agent_name: str
    description: str = ""
    agent_type: str = "general"
    second_task: RegisterViaSkillSecondTaskBody
    referral_code: Optional[str] = None
    # 部署探活 / 集成测试专用：携带正确的 `internal_probe_token` 时，
    # 第二条任务会写入 hidden_from_public=True，不进入公开大厅。
    # 服务端通过环境变量 CLAWJOB_INTERNAL_PROBE_TOKEN 启用；未配置时此字段被忽略。
    internal_probe_token: Optional[str] = None


class RegisterAgentMinimalBody(BaseModel):
    """最低摩擦 Agent 注册：无需 second_task，自动完成握手。"""

    model_config = ConfigDict(extra="ignore")

    agent_name: str
    description: str = ""
    agent_type: str = "general"
    referral_code: Optional[str] = None


CLAWJOB_SYSTEM_USERNAME = "clawjob_system"
CLAWJOB_SYSTEM_AGENT_NAME = "clawjob-agent"
SKILL_REGISTER_BONUS_CREDITS = 500
# 第二条任务 description 的最短长度（按 SKILL.md 模板计算过后的合理下限）。
SKILL_SECOND_TASK_MIN_DESCRIPTION_LEN = 80

# SKILL.md 要求的正文小节；缺任一则视为非真实 Skill 任务。
_SKILL_REQUIRED_SECTIONS: tuple = (
    "Context:",
    "Deliverables:",
    "Acceptance criteria:",
    "Constraints:",
    "Time estimate:",
)

# 常见占位 / 模板 / 测试 / 自动化标记，出现在 title 或 description 中一律拒绝。
_SKILL_PLACEHOLDER_TOKENS: tuple = (
    "你的领域", "你的具体目标", "xxx",
    "【verify】", "[verify]", "【test】", "[test]", "【smoke】", "[smoke]",
    "【demo】", "[demo]",
    "deploy smoke", "deploy verify", "smoke test",
    "自动验证", "验证部署", "部署验证", "demo 任务",
)


def _second_task_looks_real(title: str, description: str) -> Optional[str]:
    """校验第二条任务是否为 OpenClaw 按 SKILL.md 模板真实生成。

    返回 None 表示通过，返回字符串表示拒绝理由。"""
    title_norm = (title or "").strip()
    desc_norm = (description or "").strip()
    if len(title_norm) < 6:
        return "second_task.title 过短，请写出具体目标"
    if len(desc_norm) < SKILL_SECOND_TASK_MIN_DESCRIPTION_LEN:
        return (
            f"second_task.description 过短（至少 {SKILL_SECOND_TASK_MIN_DESCRIPTION_LEN} 字符），"
            "须按 SKILL.md 模板包含 Context / Deliverables / Acceptance criteria / Constraints / Time estimate 小节"
        )
    lowered_title = title_norm.lower()
    lowered_desc = desc_norm.lower()
    for bad in _SKILL_PLACEHOLDER_TOKENS:
        if bad.lower() in lowered_title or bad.lower() in lowered_desc:
            return (
                f"second_task 内容疑似模板/测试占位（命中关键词「{bad}」），"
                "请按对话真实场景生成内容，不要照抄模板或含 verify/test 等字样"
            )
    missing = [s for s in _SKILL_REQUIRED_SECTIONS if s.lower() not in lowered_desc]
    if missing:
        return (
            "second_task.description 缺少 SKILL.md 模板要求的小节："
            f"{'、'.join(missing)}"
        )
    return None


def _missing_skill_sections(description: str) -> List[str]:
    lowered = (description or "").strip().lower()
    return [s for s in _SKILL_REQUIRED_SECTIONS if s.lower() not in lowered]


def _send_register_welcome_inbox(db: Session, user: User, agent: Agent, next_steps: dict) -> None:
    """最低摩擦注册后：系统站内信欢迎 + 深链（复用 community 系统 Agent 模式）。"""
    try:
        _, _ = _get_or_create_clawjob_system_agent(db)
        sys_user = db.query(User).filter(User.username == CLAWJOB_SYSTEM_USERNAME).first()
        if not sys_user:
            return
        tasks_url = next_steps.get("tasks_hall_url") or ""
        community_url = next_steps.get("community_url") or ""
        quest_ids = next_steps.get("onboarding_task_ids") or []
        quest_line = (
            f"4. 新手 Quest 任务 ID：{', '.join(str(i) for i in quest_ids)}\n"
            if quest_ids
            else ""
        )
        body = (
            f"欢迎加入 ClawJob，{agent.name}！\n\n"
            f"你的 Agent ID：{agent.id}，注册赠点已到账。\n\n"
            f"下一步：\n"
            f"1. 浏览开放任务：{tasks_url}\n"
            f"2. 进入社区交流：{community_url}\n"
            f"3. 阅读 Skill 文档：{next_steps.get('skill_doc_url', '')}\n"
            f"{quest_line}\n"
            "接取任务：GET /tasks 后 POST /tasks/{{task_id}}/subscribe，Body 含 agent_id。"
        )
        db.add(
            InternalMessage(
                sender_user_id=int(sys_user.id),
                recipient_user_id=int(user.id),
                title="欢迎加入 ClawJob",
                content=body[:8000],
                related_task_id=None,
            )
        )
    except Exception:
        pass


def _resolve_agent_display_name(db: Session, raw_name: str) -> str:
    """Agent 展示名允许重复；若全局重名则追加短后缀以保证可读区分。"""
    base = (raw_name or "").strip() or "SkillAgent"
    base = base[:255]
    if not db.query(Agent).filter(Agent.name == base).first():
        return base
    suffix = secrets.token_hex(3)
    trimmed = base[:248] if len(base) > 248 else base
    return f"{trimmed}-{suffix}"


def _skill_register_validation_error(reason: str, *, missing_sections: Optional[List[str]] = None) -> HTTPException:
    """register-via-skill 校验失败：返回可操作的 JSON 提示。"""
    detail: dict = {
        "error": reason,
        "hint": (
            "按 skill.md 的 second_task 模板补全五小节（Context / Deliverables / "
            "Acceptance criteria / Constraints / Time estimate），全文至少 80 字符；"
            "或改用 POST /auth/register-agent-minimal 免 second_task 注册。"
        ),
        "alternative": "POST /auth/register-agent-minimal",
        "skill_doc_url": f"{os.getenv('CLAWJOB_APP_URL', 'https://app.clawjob.com.cn').rstrip('/')}/skill.md",
    }
    if missing_sections:
        detail["missing_sections"] = missing_sections
    return HTTPException(status_code=400, detail=detail)


def _register_minimal_next_steps(db: Session, agent_id: int) -> dict:
    """注册成功后给 Agent 的下一步指引（Growth v2/v4）。"""
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    steps = {
        "browse_tasks_url": f"{api_base}/tasks?status_filter=open&limit=20&sort=created_at_desc",
        "tasks_hall_url": f"{app_base}/#/tasks",
        "community_url": f"{app_base}/#/community",
        "join_url": f"{app_base}/#/join",
        "playbook_url": f"{app_base}/#/playbook",
        "skill_doc_url": f"{app_base}/skill.md",
        "earnings_summary_url": f"{api_base}/agents/{agent_id}/earnings-summary",
        "skill_packs_url": f"{api_base}/skills/packs",
        "agent_manifest_url": f"{api_base}/.well-known/clawjob-agent.json",
        "suggested_subscribe": {
            "method": "POST",
            "path": "/tasks/{task_id}/subscribe",
            "body": {"agent_id": agent_id},
            "hint": "Browse GET /tasks, pick an open task, then subscribe with your agent_id.",
        },
    }
    steps.update(onboarding_tasks_for_register(db, agent_id))
    return steps


def _register_response_message(*, referral_bound: bool) -> Optional[str]:
    if not referral_bound:
        return None
    invitee_bonus = _rf.invitee_bonus_points()
    referrer_bonus = _rf.referrer_bonus_points()
    return (
        f"已绑定邀请关系：你完成首个有奖任务后，将额外获得 {invitee_bonus} 积分；"
        f"邀请人可获得 {referrer_bonus} 积分返点。"
    )


def _bind_referral_safe(db: Session, user: User, raw_code: Optional[str]) -> bool:
    try:
        rel = _rf.bind_referral(db, invitee=user, raw_code=raw_code)
        return rel is not None
    except Exception:
        return False


def _create_skill_user_agent_handshake(
    db: Session,
    *,
    agent_name: str,
    description: str,
    agent_type: str,
    referral_code: Optional[str] = None,
) -> tuple:
    """创建 Skill 用户、Agent、注册赠点与已完成握手任务。调用方负责 commit。"""
    display_name = _resolve_agent_display_name(db, agent_name)
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
            name=display_name[:255],
            description=(description or "")[:2000] or "",
            agent_type=(agent_type or "general")[:64],
            owner_id=user.id,
            capabilities=[],
            config={},
        )
        db.add(agent)
        db.flush()
        db.add(CreditTransaction(
            user_id=user.id,
            amount=SKILL_REGISTER_BONUS_CREDITS,
            type="signup_bonus",
            ref_id=None,
            remark=f"通过 ClawJob Skill 注册赠送 {SKILL_REGISTER_BONUS_CREDITS} 点",
        ))
        referral_bound = _bind_referral_safe(db, user, referral_code)
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
            input_data={
                "skills": ["clawjob", "openclaw"],
                "source": "register_via_skill",
                "hidden_from_public": True,
            },
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
        return user, agent, handshake_task, referral_bound
    raise HTTPException(status_code=500, detail="生成唯一用户失败，请重试")


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
    referral_bound = False
    try:
        rel = _rf.bind_referral(db, invitee=user, raw_code=body.referral_code)
        referral_bound = rel is not None
    except Exception:
        referral_bound = False
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
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "referral_bound": referral_bound,
    }


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
        raise _skill_register_validation_error("second_task.title 不能为空")

    probe_expected = (os.getenv("CLAWJOB_INTERNAL_PROBE_TOKEN") or "").strip()
    is_internal_probe = bool(
        probe_expected
        and (body.internal_probe_token or "").strip() == probe_expected
    )
    if not is_internal_probe:
        reject = _second_task_looks_real(st_title, st_desc)
        if reject:
            missing = _missing_skill_sections(st_desc) if "缺少" in reject else None
            raise _skill_register_validation_error(reject, missing_sections=missing or None)
    else:
        # 内部探活任务只做最低长度检查，避免业务侧因部署而写模板正文。
        if len(st_desc) < 40:
            raise HTTPException(
                status_code=400, detail="internal probe description 过短（<40）"
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
    st_input: dict = {"source": "register_via_skill_second"}
    if skill_tags:
        st_input["skills"] = skill_tags
    if is_internal_probe:
        st_input["hidden_from_public"] = True
        st_input["internal_probe"] = True
    st_category = (st.category or "").strip()[:64] or None
    st_requirements = (st.requirements or "").strip() or None
    st_type = (st.task_type or "general").strip()[:64] or "general"
    st_priority = (st.priority or "medium").strip()[:32] or "medium"

    name = (body.agent_name or "").strip() or "SkillAgent"
    user, agent, handshake_task, referral_bound = _create_skill_user_agent_handshake(
        db,
        agent_name=name,
        description=body.description or "",
        agent_type=body.agent_type or "general",
        referral_code=body.referral_code,
    )

    if reward_points > 0:
        credits_now = getattr(user, "credits", 0) or 0
        if credits_now < reward_points:
            raise HTTPException(
                status_code=400,
                detail=f"信用点不足：当前 {credits_now}，second_task.reward_points 需要 {reward_points}",
            )

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
    _community.ensure_auto_topics_for_agent(db, agent, skill_tags, force=False)

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
                    "referral_bound": referral_bound,
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
    next_steps = _register_minimal_next_steps(db, agent.id)
    try:
        _send_register_welcome_inbox(db, user, agent, next_steps)
        db.commit()
    except Exception:
        db.rollback()
    reg_msg = _register_response_message(referral_bound=referral_bound)
    payload = {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "credits": user.credits,
        "signup_bonus_credits": SKILL_REGISTER_BONUS_CREDITS,
        "auto_task_reward_allocated": reward_points,
        "referral_bound": referral_bound,
        "auto_published_tasks": [
            {"id": handshake_task.id, "title": handshake_task.title, "status": handshake_task.status},
            {
                "id": second_task.id,
                "title": second_task.title,
                "status": second_task.status,
                "reward_points": second_task.reward_points,
            },
        ],
        "next_steps": next_steps,
        "onboarding_task_ids": next_steps.get("onboarding_task_ids") or [],
        "onboarding_tasks": next_steps.get("onboarding_tasks") or [],
    }
    if reg_msg:
        payload["message"] = reg_msg
    return payload


@router.post("/register-agent-minimal")
@limiter.limit("30/minute")
def register_agent_minimal(request: Request, body: RegisterAgentMinimalBody, db: Session = Depends(get_db)):
    """
    最低摩擦 Agent 注册：创建用户与 Agent，自动完成握手，无 second_task。
    适合 guest-token 发布后仅需接取任务、或快速 onboarding 的场景。
    """
    _ = request
    name = (body.agent_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="agent_name 不能为空")
    user, agent, handshake_task, referral_bound = _create_skill_user_agent_handshake(
        db,
        agent_name=name,
        description=body.description or "",
        agent_type=body.agent_type or "general",
        referral_code=body.referral_code,
    )
    db.commit()
    db.refresh(user)
    db.refresh(agent)
    next_steps = _register_minimal_next_steps(db, agent.id)
    try:
        _send_register_welcome_inbox(db, user, agent, next_steps)
        db.add(
            SystemLog(
                level="info",
                category="auth",
                message="user_registered_agent_minimal",
                user_id=user.id,
                extra={
                    "username": user.username,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "signup_bonus_credits": SKILL_REGISTER_BONUS_CREDITS,
                    "referral_bound": referral_bound,
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
    reg_msg = _register_response_message(referral_bound=referral_bound)
    payload = {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "credits": user.credits,
        "signup_bonus_credits": SKILL_REGISTER_BONUS_CREDITS,
        "referral_bound": referral_bound,
        "auto_published_tasks": [
            {"id": handshake_task.id, "title": handshake_task.title, "status": handshake_task.status},
        ],
        "next_steps": next_steps,
        "onboarding_task_ids": next_steps.get("onboarding_task_ids") or [],
        "onboarding_tasks": next_steps.get("onboarding_tasks") or [],
    }
    if reg_msg:
        payload["message"] = reg_msg
    return payload


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
        register_hint_zh = (
            "您当前为游客身份，仅可发布任务。要让 Agent 接取任务，"
            "请调用 POST /auth/register-agent-minimal（最快）或 /auth/register-via-skill。"
        )
        register_hint_en = (
            "You are using a guest token; you can publish tasks. "
            "To accept tasks, call POST /auth/register-agent-minimal (fastest) or /auth/register-via-skill."
        )
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
