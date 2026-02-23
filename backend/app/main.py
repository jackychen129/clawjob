"""
ClawJob - Backend API
任务发布与接取平台：用户注册 Agent，发布任务，订阅他人任务。
"""
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import httpx
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Database imports
from app.database.vector_db import VectorDB
from app.database.relational_db import (
    RelationalDB,
    get_db,
    Task,
    Agent,
    TaskSubscription,
    User,
    CreditTransaction,
    PlatformClearingAccount,
    PlatformCommissionRecord,
    UserCommissionRecord,
)
from app.database.cache_db import CacheDB

# Agent system imports
from app.agents.agent_manager import AgentManager
from app.agents.task_system import TaskSystem
from app.agents.memory_system import MemorySystem
from app.agents.tool_system import ToolSystem

# Security & routers
from app.security import get_current_user, limiter
from app.routers import auth
from app.routers import account


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应添加安全头（CSP、X-Frame-Options 等），满足线上安全要求。"""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # API 场景下 CSP 放宽，避免影响 /docs
        csp = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'"
        response.headers["Content-Security-Policy"] = csp
        return response


app = FastAPI(
    title="ClawJob API",
    description="任务发布与接取：注册 Agent、发布任务、订阅他人任务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize database systems
vector_db = VectorDB()
relational_db = RelationalDB()
cache_db = CacheDB()

# Initialize agent systems
agent_manager = AgentManager(vector_db, relational_db, cache_db)
task_system = TaskSystem(vector_db, relational_db, cache_db)
memory_system = MemorySystem(vector_db, cache_db)
tool_system = ToolSystem(relational_db, cache_db)

# Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.include_router(auth.router)
app.include_router(account.router)

# 限流：全局默认在 security.limiter 的 default_limits 中配置
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 安全头中间件（先添加，响应时最后执行）
app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration（生产环境通过 CORS_ORIGINS 限制来源，逗号分隔；空则同源）
_cors_origins = os.getenv("CORS_ORIGINS", "").strip()
_cors_origins_list = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _validate_production_config():
    """生产环境启动时校验必要安全配置。"""
    env = os.getenv("ENV", "").strip().lower()
    if env != "production":
        return
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret or secret == "clawjob-secret-key-change-in-production":
        raise RuntimeError(
            "生产环境必须设置 JWT_SECRET 且不可使用默认值。请在环境变量中配置 JWT_SECRET。"
        )
    cors = os.getenv("CORS_ORIGINS", "").strip()
    if not cors or cors == "*":
        raise RuntimeError(
            "生产环境必须设置 CORS_ORIGINS 为具体前端域名（逗号分隔），禁止使用 *。"
        )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "clawjob-backend",
        "databases": {
            "vector_db": await vector_db.health_check(),
            "relational_db": await relational_db.health_check(),
            "cache_db": await cache_db.health_check()
        },
        "agent_systems": {
            "agent_manager": "active",
            "task_system": "active", 
            "memory_system": "active",
            "tool_system": "active"
        }
    }

# Agent 注册（在 DB 中创建，用于接取任务）
class RegisterAgentBody(BaseModel):
    name: str
    description: str = ""
    agent_type: str = "general"


@app.post("/agents/register")
def register_agent(
    body: RegisterAgentBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """注册我的 Agent（需登录），用于接取/订阅他人任务"""
    uid = int(current_user["user_id"])
    agent = Agent(
        name=body.name,
        description=body.description or "",
        agent_type=body.agent_type or "general",
        owner_id=uid,
        capabilities=[],
        config={},
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"id": agent.id, "name": agent.name, "agent_type": agent.agent_type}


@app.get("/agents/mine")
def list_my_agents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我注册的 Agent 列表（需登录）"""
    uid = int(current_user["user_id"])
    agents = db.query(Agent).filter(Agent.owner_id == uid).order_by(Agent.id.desc()).all()
    return {
        "agents": [
            {"id": a.id, "name": a.name, "description": a.description or "", "agent_type": a.agent_type}
            for a in agents
        ]
    }


# Agent Management Endpoints (legacy)
@app.post("/agents")
async def create_agent(agent_config: dict, current_user: str = Depends(get_current_user)):
    """Create a new AI agent with specified capabilities"""
    return await agent_manager.create_agent(agent_config, current_user)

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str, current_user: str = Depends(get_current_user)):
    """Get agent details"""
    return await agent_manager.get_agent(agent_id, current_user)

@app.get("/agents")
async def list_agents(current_user: str = Depends(get_current_user)):
    """List all agents for current user"""
    return await agent_manager.list_agents(current_user)

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, current_user: str = Depends(get_current_user)):
    """Delete an agent"""
    return await agent_manager.delete_agent(agent_id, current_user)

# ---------- ClawJob 任务大厅（首页）----------
VERIFICATION_HOURS = 6  # 发布者验收截止时间（小时），超时自动完成
PLATFORM_COMMISSION_RATE = 0.01  # 任务成功发放奖励时，若发布方已配置佣金则按此比例计入发布者（可选功能）

class PublishTaskBody(BaseModel):
    title: str
    description: str = ""
    task_type: str = "general"
    priority: str = "medium"
    reward_points: int = 0  # 任务奖励点（发布时从账户扣减，验收通过或超时后发给接取者）
    completion_webhook_url: str = ""  # 有奖励点时必填：接取者提交完成时 POST 回调此 URL，供发布方验收


class SubscribeTaskBody(BaseModel):
    agent_id: int


class SubmitCompletionBody(BaseModel):
    result_summary: str = ""  # 完成结果摘要，会随 webhook 发给发布方
    evidence: dict = {}  # 可选证据/输出，会随 webhook 发给发布方


def _get_or_create_clearing_account(db: Session) -> PlatformClearingAccount:
    """获取或创建平台中转账户（单例，id=1）"""
    acc = db.query(PlatformClearingAccount).filter(PlatformClearingAccount.id == 1).first()
    if not acc:
        acc = PlatformClearingAccount(id=1, balance=0)
        db.add(acc)
        db.flush()
    return acc


def _pay_task_reward(task: Task, db: Session) -> bool:
    """发放任务奖励：接取者得奖励；若已配置佣金则按比例计入发布者佣金余额。已完成则返回 False。"""
    if task.status == "completed":
        return False
    reward_points = getattr(task, "reward_points", 0) or 0
    if reward_points > 0 and task.agent_id:
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if agent:
            receiver = db.query(User).filter(User.id == agent.owner_id).first()
            if receiver:
                commission = int(reward_points * PLATFORM_COMMISSION_RATE)
                amount_to_receiver = reward_points - commission
                receiver.credits = (getattr(receiver, "credits", 0) or 0) + amount_to_receiver
                remark = f"完成任务 #{task.id} 获得 {amount_to_receiver} 任务点"
                if commission > 0:
                    remark += f"（已配置佣金 {commission} 点）"
                tx = CreditTransaction(
                    user_id=agent.owner_id,
                    amount=amount_to_receiver,
                    type="task_reward",
                    ref_id=task.id,
                    remark=remark,
                )
                db.add(tx)
                # 已配置的佣金发放给任务发布者（用户）
                if commission > 0 and task.owner_id:
                    publisher = db.query(User).filter(User.id == task.owner_id).first()
                    if publisher:
                        publisher.commission_balance = (getattr(publisher, "commission_balance", 0) or 0) + commission
                        ucr = UserCommissionRecord(
                            user_id=task.owner_id,
                            amount=commission,
                            task_id=task.id,
                            remark=f"任务 #{task.id} 佣金",
                        )
                        db.add(ucr)
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    return True


def _maybe_auto_confirm(task: Task, db: Session) -> None:
    """若任务处于待验收且已过截止时间，自动验收并发奖。"""
    if task.status != "pending_verification" or not getattr(task, "verification_deadline_at", None):
        return
    deadline = task.verification_deadline_at
    if deadline and datetime.utcnow() >= deadline:
        _pay_task_reward(task, db)
        db.commit()


@app.get("/tasks")
def list_tasks_public(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    db: Session = Depends(get_db),
):
    """任务大厅：公开列出所有任务（无需登录）"""
    q = db.query(Task).order_by(Task.created_at.desc())
    if status_filter:
        q = q.filter(Task.status == status_filter)
    tasks = q.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        _maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "task_type": t.task_type or "general",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "agent_id": t.agent_id,
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "subscription_count": sub_count,
            "submitted_at": t.submitted_at.isoformat() if getattr(t, "submitted_at", None) else None,
            "verification_deadline_at": t.verification_deadline_at.isoformat() if getattr(t, "verification_deadline_at", None) else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"tasks": out, "total": len(out)}


@app.post("/tasks")
def publish_task(
    body: PublishTaskBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布任务（需登录）；若设置 reward_points 则从当前用户信用点扣减"""
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    reward_points = max(0, getattr(body, "reward_points", 0) or 0)
    webhook_url = (getattr(body, "completion_webhook_url", None) or "").strip()
    if reward_points > 0:
        if not webhook_url or not webhook_url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="有奖励点的任务必须填写完成回调 URL（completion_webhook_url），用于接取者提交完成时通知发布方验收",
            )
        credits = getattr(user, "credits", 0) or 0
        if credits < reward_points:
            raise HTTPException(
                status_code=400,
                detail=f"信用点不足：当前 {credits}，需要 {reward_points}",
            )
    task = Task(
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        priority=body.priority,
        status="open",
        owner_id=uid,
        agent_id=None,
        reward_points=reward_points,
        completion_webhook_url=webhook_url if webhook_url else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if reward_points > 0:
        user.credits = (getattr(user, "credits", 0) or 0) - reward_points
        tx = CreditTransaction(
            user_id=uid,
            amount=-reward_points,
            type="task_publish",
            ref_id=task.id,
            remark=f"发布任务 #{task.id} 扣除 {reward_points} 任务点",
        )
        db.add(tx)
        db.commit()
    return {"id": task.id, "title": task.title, "status": task.status, "reward_points": reward_points}


@app.post("/tasks/{task_id}/subscribe")
def subscribe_task(
    task_id: int,
    body: SubscribeTaskBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """订阅任务：用我的 Agent 接取该任务（需登录）"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    agent = db.query(Agent).filter(Agent.id == body.agent_id, Agent.owner_id == uid).first()
    if not agent:
        raise HTTPException(status_code=400, detail="Agent 不存在或不属于当前用户")
    existing = db.query(TaskSubscription).filter(
        TaskSubscription.task_id == task_id,
        TaskSubscription.agent_id == body.agent_id,
    ).first()
    if existing:
        return {"message": "已订阅过该任务", "subscription_id": existing.id}
    sub = TaskSubscription(task_id=task_id, agent_id=body.agent_id)
    db.add(sub)
    # 若任务尚未分配接取者，则当前订阅的 Agent 视为接取者
    if task.agent_id is None:
        task.agent_id = body.agent_id
    db.commit()
    db.refresh(sub)
    return {"message": "订阅成功", "subscription_id": sub.id}


@app.post("/tasks/{task_id}/submit-completion")
def submit_completion(
    task_id: int,
    body: SubmitCompletionBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """接取者提交完成：仅接取该任务的 Agent 所属用户可调用。会 POST 到发布者填写的 completion_webhook_url，任务进入待验收，6 小时内发布者不确认则自动完成并发奖。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task.agent_id:
        raise HTTPException(status_code=400, detail="任务尚未被接取")
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
    if not agent or agent.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅接取该任务的用户可提交完成")
    if task.status == "completed":
        return {"message": "任务已完成", "task_id": task_id}
    if task.status == "pending_verification":
        return {"message": "已提交验收，请等待发布者确认或 6 小时后自动完成", "task_id": task_id}
    webhook_url = getattr(task, "completion_webhook_url", None) or ""
    if not webhook_url:
        raise HTTPException(status_code=400, detail="该任务未配置完成回调，无法提交")
    payload = {
        "task_id": task_id,
        "title": task.title,
        "agent_id": task.agent_id,
        "agent_name": agent.name,
        "result_summary": body.result_summary or "",
        "evidence": body.evidence or {},
        "submitted_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(webhook_url, json=payload)
            if r.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"完成回调返回异常：{r.status_code}，发布方需验收通过后再在平台确认",
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"调用完成回调失败：{str(e)}")
    task.status = "pending_verification"
    task.submitted_at = datetime.utcnow()
    task.verification_deadline_at = datetime.utcnow() + timedelta(hours=VERIFICATION_HOURS)
    if body.result_summary or body.evidence:
        base = task.output_data if isinstance(task.output_data, dict) else {}
        task.output_data = {**(base or {}), "result_summary": body.result_summary or "", "evidence": body.evidence or {}}
    db.commit()
    return {
        "message": "已提交验收，发布者需在 6 小时内确认，否则将自动完成并发奖",
        "task_id": task_id,
        "verification_deadline_at": task.verification_deadline_at.isoformat() if task.verification_deadline_at else None,
    }


@app.post("/tasks/{task_id}/confirm")
def confirm_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布者验收通过：仅任务发布者可调用，发放奖励给接取者。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可验收")
    _maybe_auto_confirm(task, db)
    db.refresh(task)
    if task.status == "completed":
        return {"message": "任务已是完成状态（或已自动完成）", "task_id": task_id}
    reward_points = getattr(task, "reward_points", 0) or 0
    if task.status == "pending_verification":
        _pay_task_reward(task, db)
    elif task.status == "open" and reward_points == 0:
        task.status = "completed"
        task.completed_at = datetime.utcnow()
    else:
        raise HTTPException(status_code=400, detail="任务尚未进入待验收状态，请等待接取者提交完成")
    db.commit()
    commission = int(reward_points * PLATFORM_COMMISSION_RATE) if reward_points else 0
    amount_to_executor = reward_points - commission if reward_points else 0
    return {
        "message": "验收通过，奖励已发放" if reward_points else "任务已关闭",
        "task_id": task_id,
        "reward_paid": amount_to_executor,
        "reward_total": reward_points,
        "commission": commission,
    }


@app.post("/tasks/{task_id}/reject")
def reject_completion(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布者拒绝验收：任务回到可继续状态，接取者可重新提交完成。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可拒绝")
    if task.status != "pending_verification":
        raise HTTPException(status_code=400, detail="仅待验收任务可拒绝")
    task.status = "open"
    task.submitted_at = None
    task.verification_deadline_at = None
    db.commit()
    return {"message": "已拒绝，接取者可重新提交完成", "task_id": task_id}


@app.get("/tasks/{task_id}")
async def get_task_by_id(task_id: int, db: Session = Depends(get_db)):
    """获取单条任务详情（公开）；若处于待验收且已过 6 小时则自动完成。"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _maybe_auto_confirm(task, db)
    db.refresh(task)
    owner = db.query(User).filter(User.id == task.owner_id).first()
    subs = db.query(TaskSubscription).filter(TaskSubscription.task_id == task_id).all()
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "status": task.status,
        "priority": task.priority,
        "task_type": task.task_type,
        "owner_id": task.owner_id,
        "publisher_name": owner.username if owner else "",
        "agent_id": task.agent_id,
        "reward_points": getattr(task, "reward_points", 0) or 0,
        "subscription_count": len(subs),
        "submitted_at": task.submitted_at.isoformat() if getattr(task, "submitted_at", None) else None,
        "verification_deadline_at": task.verification_deadline_at.isoformat() if getattr(task, "verification_deadline_at", None) else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@app.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, current_user: str = Depends(get_current_user)):
    """Execute a task using available agents"""
    return await task_system.execute_task(task_id, current_user)


# ---------- 平台中转账户（手续费/佣金，关联支付宝）----------
PLATFORM_ADMIN_KEY = os.getenv("PLATFORM_ADMIN_KEY", "").strip()


def _require_platform_admin(x_platform_admin_key: str = Header(None, alias="X-Platform-Admin-Key")):
    """平台管理中转账户：请求头 X-Platform-Admin-Key 需与环境变量 PLATFORM_ADMIN_KEY 一致"""
    if not PLATFORM_ADMIN_KEY:
        raise HTTPException(status_code=503, detail="未配置 PLATFORM_ADMIN_KEY，无法管理中转账户")
    if x_platform_admin_key != PLATFORM_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="需要平台管理员密钥")


class ClearingAccountUpdateBody(BaseModel):
    alipay_account: str = None  # 支付宝账号（建议脱敏，如 platform***@alipay.com）
    alipay_name: str = None    # 支付宝实名（可选）


@app.get("/platform/clearing-account")
def get_clearing_account(
    db: Session = Depends(get_db),
    _admin=Depends(_require_platform_admin),
):
    """查询平台中转账户：余额与支付宝信息（需管理员密钥）"""
    acc = db.query(PlatformClearingAccount).filter(PlatformClearingAccount.id == 1).first()
    if not acc:
        acc = _get_or_create_clearing_account(db)
        db.commit()
    return {
        "balance": acc.balance or 0,
        "alipay_account": acc.alipay_account or "",
        "alipay_name": acc.alipay_name or "",
    }


@app.patch("/platform/clearing-account")
def update_clearing_account(
    body: ClearingAccountUpdateBody,
    db: Session = Depends(get_db),
    _admin=Depends(_require_platform_admin),
):
    """设置中转账户关联支付宝（需管理员密钥或超级用户）"""
    acc = _get_or_create_clearing_account(db)
    if body.alipay_account is not None:
        acc.alipay_account = body.alipay_account.strip() or None
    if body.alipay_name is not None:
        acc.alipay_name = body.alipay_name.strip() or None
    db.commit()
    db.refresh(acc)
    return {"balance": acc.balance or 0, "alipay_account": acc.alipay_account or "", "alipay_name": acc.alipay_name or ""}


@app.get("/platform/clearing-account/records")
def list_clearing_commission_records(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin=Depends(_require_platform_admin),
):
    """平台佣金流水（需管理员密钥）"""
    acc = db.query(PlatformClearingAccount).filter(PlatformClearingAccount.id == 1).first()
    if not acc:
        return {"records": [], "total": 0}
    rows = (
        db.query(PlatformCommissionRecord)
        .filter(PlatformCommissionRecord.clearing_account_id == acc.id)
        .order_by(PlatformCommissionRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "records": [
            {"id": r.id, "amount": r.amount, "task_id": r.task_id, "remark": r.remark or "", "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in rows
        ],
        "total": len(rows),
    }


# Memory System Endpoints
@app.post("/memory")
async def store_memory(memory_data: dict, current_user: str = Depends(get_current_user)):
    """Store memory in vector database"""
    return await memory_system.store_memory(memory_data, current_user)

@app.get("/memory/search")
async def search_memory(query: str, current_user: str = Depends(get_current_user)):
    """Search memory using semantic search"""
    return await memory_system.search_memory(query, current_user)

@app.get("/memory/{memory_id}")
async def get_memory(memory_id: str, current_user: str = Depends(get_current_user)):
    """Retrieve specific memory"""
    return await memory_system.get_memory(memory_id, current_user)

# Tool System Endpoints
@app.get("/tools")
async def list_tools(current_user: str = Depends(get_current_user)):
    """List available tools for agents"""
    return await tool_system.list_tools(current_user)

@app.post("/tools")
async def create_tool(tool_config: dict, current_user: str = Depends(get_current_user)):
    """Create a new tool for agents to use"""
    return await tool_system.create_tool(tool_config, current_user)

@app.post("/agents/{agent_id}/use-tool")
async def use_tool(agent_id: str, tool_request: dict, current_user: str = Depends(get_current_user)):
    """Allow agent to use a specific tool"""
    return await tool_system.use_tool(agent_id, tool_request, current_user)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)