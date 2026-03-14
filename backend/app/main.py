"""
ClawJob - Backend API
任务发布与接取平台：用户注册 Agent，发布任务，订阅他人任务。
"""
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Any
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
    init_db,
    engine as db_engine,
    Task,
    Agent,
    TaskSubscription,
    TaskComment,
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


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """启动时创建/更新数据库表，并校验生产环境配置。"""
    try:
        init_db()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning("init_db: %s", e)
    env = os.getenv("ENV", "").strip().lower()
    if env == "production":
        secret = os.getenv("JWT_SECRET", "").strip()
        if not secret or secret == "clawjob-secret-key-change-in-production":
            raise RuntimeError("生产环境必须设置 JWT_SECRET 且不可使用默认值。")
        cors = os.getenv("CORS_ORIGINS", "").strip()
        if not cors or cors == "*":
            raise RuntimeError("生产环境必须设置 CORS_ORIGINS 为具体前端域名，禁止使用 *。")
    yield
    # shutdown 暂无逻辑


app = FastAPI(
    title="ClawJob API",
    description="任务发布与接取：注册 Agent、发布任务、订阅他人任务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
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


@app.get("/stats")
def get_public_stats(db: Session = Depends(get_db)):
    """公开统计：任务总数、开放数、已完成数、活跃 Agent、累计发放报酬（供首页/官网 Counters 与 Dashboard）。"""
    tasks_count = db.query(Task).count()
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0
    agents_count = db.query(Agent).count()
    agents_active = db.query(Agent).filter(Agent.is_active == True).count()
    agents_with_completions = db.query(Task.agent_id).filter(
        Task.status == "completed", Task.agent_id.isnot(None)
    ).distinct().count()
    return {
        "tasks_count": tasks_count,
        "tasks_open": tasks_open,
        "agents_count": agents_count,
        "tasks_total": tasks_count,
        "tasks_completed": tasks_completed,
        "rewards_paid": int(rewards_paid),
        "agents_active": agents_active,
        "agents_with_completions": agents_with_completions,
    }


@app.get("/activity")
def get_activity(limit: int = 50, db: Session = Depends(get_db)):
    """实时动态流：最近任务发布、任务完成、Agent 注册。用于 Dashboard Live Feed。"""
    events = []
    # 最近完成的任务（带 Agent 名、奖励）
    completed = (
        db.query(Task, Agent, User)
        .outerjoin(Agent, Task.agent_id == Agent.id)
        .join(User, Task.owner_id == User.id)
        .filter(Task.status == "completed")
        .order_by(Task.completed_at.desc().nullslast(), Task.updated_at.desc())
        .limit(limit)
    ).all()
    for t, a, owner in completed:
        at = (t.completed_at or t.updated_at or t.created_at) or datetime.utcnow()
        events.append({
            "type": "task_completed",
            "at": at.isoformat() if hasattr(at, "isoformat") else str(at),
            "task_id": t.id,
            "task_title": (t.title or "")[:80],
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "agent_name": a.name if a else None,
            "publisher_name": owner.username if owner else None,
        })
    # 最近发布的任务（open）
    created = (
        db.query(Task, User)
        .join(User, Task.owner_id == User.id)
        .filter(Task.status == "open")
        .order_by(Task.created_at.desc())
        .limit(limit)
    ).all()
    for t, owner in created:
        events.append({
            "type": "task_created",
            "at": (t.created_at or datetime.utcnow()).isoformat(),
            "task_id": t.id,
            "task_title": (t.title or "")[:80],
            "publisher_name": owner.username if owner else None,
        })
    # 最近注册的 Agent
    agents = db.query(Agent, User).join(User, Agent.owner_id == User.id).order_by(Agent.created_at.desc()).limit(limit).all()
    for a, owner in agents:
        events.append({
            "type": "agent_registered",
            "at": (a.created_at or datetime.utcnow()).isoformat(),
            "agent_id": a.id,
            "agent_name": a.name,
            "owner_name": owner.username if owner else None,
        })
    events.sort(key=lambda e: e["at"], reverse=True)
    return {"events": events[:limit]}


@app.get("/leaderboard")
def get_leaderboard(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Agent 声誉排行榜：Earned、完成任务数、成功率。shadow=1 时仅返回新星（注册不久、任务数少但成功率高的 Agent）。"""
    # 每个 Agent 的完成数、总赚取、参与任务数（用于成功率）
    from sqlalchemy import case
    completed_subq = (
        db.query(
            Task.agent_id,
            func.count(Task.id).label("completed_count"),
            func.coalesce(func.sum(Task.reward_points), 0).label("earned"),
        )
        .filter(Task.status == "completed", Task.agent_id.isnot(None))
        .group_by(Task.agent_id)
    ).subquery()
    total_subq = (
        db.query(Task.agent_id, func.count(Task.id).label("total_count"))
        .filter(Task.agent_id.isnot(None))
        .group_by(Task.agent_id)
    ).subquery()
    q = (
        db.query(
            Agent,
            User,
            func.coalesce(completed_subq.c.completed_count, 0).label("completed_count"),
            func.coalesce(completed_subq.c.earned, 0).label("earned"),
            func.coalesce(total_subq.c.total_count, 0).label("total_count"),
        )
        .join(User, Agent.owner_id == User.id)
        .outerjoin(completed_subq, Agent.id == completed_subq.c.agent_id)
        .outerjoin(total_subq, Agent.id == total_subq.c.agent_id)
        .filter(Agent.is_active == True, User.is_active == True)
    )
    rows = q.order_by(completed_subq.c.earned.desc().nullslast(), Agent.id.desc()).offset(skip).limit(limit).all()
    out = []
    for i, (a, owner, completed_count, earned, total_count) in enumerate(rows):
        total_count = total_count or 0
        completed_count = completed_count or 0
        success_rate = (completed_count / total_count * 100) if total_count else 0
        out.append({
            "rank": skip + i + 1,
            "agent_id": a.id,
            "agent_name": a.name,
            "owner_name": owner.username if owner else "",
            "earned": int(earned),
            "tasks_completed": int(completed_count),
            "tasks_total": int(total_count),
            "success_rate": round(success_rate, 1),
            "certified": False,  # 预留：Playbook 验证后为 True
        })
    return {"items": out, "total": len(out)}


# OpenClaw/Clawl 对齐：capability 项 { id?, name, category? }
class CapabilityItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: Optional[str] = None


# Agent 注册（在 DB 中创建，用于接取任务；参数对齐 OpenClaw agent 属性）
class RegisterAgentBody(BaseModel):
    name: str
    description: str = ""
    agent_type: str = "general"  # 主类型，与 OpenClaw type 首项对应
    types: Optional[List[str]] = None  # OpenClaw 多类型，如 ["assistant"], ["developer","security"]
    capabilities: Optional[List[CapabilityItem]] = None  # OpenClaw capabilities: [{ id, name, category }]
    status: Optional[str] = "active"  # active | inactive
    category: Optional[str] = None  # 注册来源：skill | mcp | web | api（MCP/Skill 调用时自动带，免填）
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    webhook_url: Optional[str] = None  # 存活探测 GET + 接收消息 POST 的 URL


def _ensure_agents_category_column() -> None:
    """确保 agents 表存在 category 列（线上可能为旧库，init_db 未执行到或执行失败）。"""
    try:
        with db_engine.connect() as conn:
            if db_engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS category VARCHAR(32)"))
            else:
                conn.execute(text("ALTER TABLE agents ADD COLUMN category VARCHAR(32)"))
            conn.commit()
    except Exception:
        pass


def _norm_capabilities(caps: Optional[List[Any]]) -> list:
    if not caps:
        return []
    out = []
    for c in caps:
        if isinstance(c, dict):
            out.append({"id": c.get("id"), "name": c.get("name") or "", "category": c.get("category")})
        elif hasattr(c, "name"):
            out.append({"id": getattr(c, "id", None), "name": c.name, "category": getattr(c, "category", None)})
        else:
            continue
    return out


@app.post("/agents/register")
def register_agent(
    body: RegisterAgentBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """注册我的 Agent（需登录），用于接取/订阅他人任务。参数对齐 OpenClaw/Clawl agent。"""
    _ensure_agents_category_column()
    uid = int(current_user["user_id"])
    primary_type = (body.agent_type or "general").strip() or "general"
    if body.types and len(body.types) > 0:
        primary_type = (body.types[0] or primary_type).strip() or primary_type
    capabilities = _norm_capabilities(body.capabilities) if body.capabilities else []
    config = {}
    if body.avatar_url and body.avatar_url.strip():
        config["avatar_url"] = body.avatar_url.strip()
    if body.profile_url and body.profile_url.strip():
        config["profile_url"] = body.profile_url.strip()
    if body.webhook_url and body.webhook_url.strip():
        config["webhook_url"] = body.webhook_url.strip()
    is_active = (body.status or "active").strip().lower() != "inactive"
    category = (body.category or "api").strip().lower() or "api"
    if category not in ("skill", "mcp", "web", "api"):
        category = "api"
    agent = Agent(
        name=body.name.strip(),
        description=(body.description or "").strip(),
        agent_type=primary_type,
        category=category,
        owner_id=uid,
        capabilities=capabilities,
        config=config,
        is_active=is_active,
    )
    db.add(agent)
    try:
        db.commit()
        db.refresh(agent)
    except Exception as e:
        db.rollback()
        err_msg = str(e).lower()
        # 线上若 agents 表尚无 category 列则插入会报错，补列后重试
        if "category" in err_msg or "does not exist" in err_msg or "column" in err_msg:
            _ensure_agents_category_column()
            agent_retry = Agent(
                name=body.name.strip(),
                description=(body.description or "").strip(),
                agent_type=primary_type,
                category=category,
                owner_id=uid,
                capabilities=capabilities,
                config=config,
                is_active=is_active,
            )
            db.add(agent_retry)
            db.commit()
            db.refresh(agent_retry)
            agent = agent_retry
        else:
            raise
    return {
        "id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "category": getattr(agent, "category", None) or "api",
        "capabilities": agent.capabilities or [],
        "status": "active" if agent.is_active else "inactive",
    }


@app.get("/agents/mine")
def list_my_agents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我注册的 Agent 列表（需登录），按积分（完成任务获得）降序。线上容错：查询失败时补列并重试或返回空列表。"""
    _ensure_agents_category_column()
    uid = int(current_user["user_id"])

    def _build_agent_item(a: Agent, points: int = 0) -> dict:
        return {
            "id": a.id,
            "name": a.name,
            "description": a.description or "",
            "agent_type": a.agent_type or "general",
            "category": getattr(a, "category", None) or "api",
            "capabilities": a.capabilities or [],
            "status": "active" if a.is_active else "inactive",
            "config": a.config or {},
            "points": int(points),
        }

    try:
        points_subq = (
            db.query(Task.agent_id, func.coalesce(func.sum(Task.reward_points), 0).label("points"))
            .filter(Task.status == "completed", Task.agent_id.isnot(None))
            .group_by(Task.agent_id)
            .subquery()
        )
        rows = (
            db.query(Agent, func.coalesce(points_subq.c.points, 0).label("points"))
            .outerjoin(points_subq, Agent.id == points_subq.c.agent_id)
            .filter(Agent.owner_id == uid)
            .order_by(points_subq.c.points.desc().nullslast(), Agent.id.desc())
            .all()
        )
        return {"agents": [_build_agent_item(a, points) for a, points in rows]}
    except Exception as e:
        db.rollback()
        err_msg = str(e).lower()
        if "column" in err_msg or "does not exist" in err_msg or "category" in err_msg:
            _ensure_agents_category_column()
        try:
            agents = db.query(Agent).filter(Agent.owner_id == uid).order_by(Agent.id.desc()).all()
            return {"agents": [_build_agent_item(a, 0) for a in agents]}
        except Exception:
            db.rollback()
            return {"agents": []}


def _get_my_agent(agent_id: int, db: Session, user_id: int) -> Optional[Agent]:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.owner_id != user_id:
        return None
    return agent


@app.get("/agents/{agent_id}/ping")
def agent_ping(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """探测 Agent 是否存活：对配置的 webhook_url 发 GET 请求，仅 Agent 所有者可调用。"""
    uid = int(current_user["user_id"])
    agent = _get_my_agent(agent_id, db, uid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or not yours")
    config = agent.config or {}
    webhook_url = (config.get("webhook_url") or "").strip()
    if not webhook_url:
        return {"alive": False, "reason": "no_webhook", "message": "未配置 Webhook URL"}
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(webhook_url)
            return {"alive": 200 <= r.status_code < 400, "status_code": r.status_code}
    except Exception as e:
        return {"alive": False, "reason": "request_failed", "message": str(e)}


class SendMessageBody(BaseModel):
    content: str


@app.post("/agents/{agent_id}/send-message")
def agent_send_message(
    agent_id: int,
    body: SendMessageBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """向 Agent 发送消息：POST 到 webhook_url，仅 Agent 所有者可调用。"""
    uid = int(current_user["user_id"])
    agent = _get_my_agent(agent_id, db, uid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or not yours")
    config = agent.config or {}
    webhook_url = (config.get("webhook_url") or "").strip()
    if not webhook_url:
        raise HTTPException(status_code=400, detail="未配置 Webhook URL，无法发送消息")
    try:
        payload = {"type": "message", "content": (body.content or "").strip(), "agent_id": agent_id}
        with httpx.Client(timeout=10.0) as client:
            r = client.post(webhook_url, json=payload)
            return {"sent": 200 <= r.status_code < 400, "status_code": r.status_code, "response": r.text[:500] if r.text else None}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"发送失败: {str(e)}")


@app.get("/candidates")
def list_candidates(
    skip: int = 0,
    limit: int = 100,
    sort: str = "points",  # points | recent（最近注册优先）
    db: Session = Depends(get_db),
):
    """候选者列表（公开）：已注册的 Agent 及所属用户。sort=points 按积分降序，sort=recent 按注册时间倒序。"""
    points_subq = (
        db.query(Task.agent_id, func.coalesce(func.sum(Task.reward_points), 0).label("points"))
        .filter(Task.status == "completed", Task.agent_id.isnot(None))
        .group_by(Task.agent_id)
        .subquery()
    )
    q = (
        db.query(Agent, User, func.coalesce(points_subq.c.points, 0).label("points"))
        .join(User, Agent.owner_id == User.id)
        .outerjoin(points_subq, Agent.id == points_subq.c.agent_id)
        .filter(Agent.is_active == True, User.is_active == True)
    )
    if (sort or "").strip().lower() == "recent":
        q = q.order_by(Agent.id.desc())
    else:
        q = q.order_by(points_subq.c.points.desc().nullslast(), Agent.id.desc())
    rows = q.offset(skip).limit(limit).all()
    out = []
    for a, owner, points in rows:
        cfg = a.config or {}
        out.append({
            "id": a.id,
            "type": "agent",
            "name": a.name,
            "description": (a.description or "")[:300],
            "agent_type": a.agent_type or "general",
            "capabilities": a.capabilities or [],
            "status": "active" if a.is_active else "inactive",
            "avatar_url": cfg.get("avatar_url"),
            "profile_url": cfg.get("profile_url"),
            "owner_id": a.owner_id,
            "owner_name": owner.username if owner else "",
            "points": int(points),
        })
    return {"candidates": out, "total": len(out)}


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

# 前端地址，用于 Discord 推送中的任务链接
_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


class PublishTaskBody(BaseModel):
    title: str
    description: str = ""
    task_type: str = "general"
    priority: str = "medium"
    reward_points: int = 0  # 任务奖励点（发布时从账户扣减，验收通过或超时后发给接取者）
    completion_webhook_url: str = ""  # 有奖励点时必填：接取者提交完成时 POST 回调此 URL，供发布方验收
    invited_agent_ids: list = []  # 可选：仅这些 Agent 可接取；空表示对所有人开放
    creator_agent_id: Optional[int] = None  # 可选：由某 Agent 代发（须为当前用户的 Agent）
    # 任务分类与详情
    category: str = ""  # 任务分类：development, design, research, writing, data, other
    requirements: str = ""  # 详细要求说明
    # 任务可选属性（地点、时长、技能等）
    location: str = ""  # 地点要求，如 "远程"、"北京"
    duration_estimate: str = ""  # 预计时长，如 "~1h"、"~3h"
    skills: list = []  # 所需技能标签，如 ["数据分析", "Python"]
    discord_webhook_url: str = ""  # 可选：将任务推送到指定 Discord 频道，便于具备 Skill 的 Agent 发现并接取


def _push_task_to_discord(task: Task, webhook_url: str, frontend_url: str) -> None:
    """将任务信息推送到 Discord 频道（Webhook），便于 Agent 通过 Skill 发现并接取。"""
    if not webhook_url or not webhook_url.strip().startswith(("http://", "https://")):
        return
    task_link = f"{frontend_url}/tasks"
    if getattr(task, "id", None):
        task_link = f"{frontend_url}/tasks?taskId={task.id}"
    desc = (task.description or "").strip() or "无描述"
    if len(desc) > 150:
        desc = desc[:147] + "..."
    reward = getattr(task, "reward_points", 0) or 0
    category = (getattr(task, "category", None) or "").strip() or "—"
    extra = getattr(task, "input_data", None) or {}
    location = (extra.get("location") or "").strip() or "—"
    skills = extra.get("skills") or []
    skills_str = ", ".join(str(s) for s in skills[:5]) if skills else "—"
    fields = [
        {"name": "奖励点", "value": str(reward), "inline": True},
        {"name": "分类", "value": category, "inline": True},
        {"name": "地点", "value": location, "inline": True},
        {"name": "技能", "value": skills_str[:100], "inline": False},
        {"name": "接取方式", "value": "通过 ClawJob Skill 或打开任务大厅接取", "inline": False},
    ]
    payload = {
        "embeds": [
            {
                "title": (task.title or "新任务")[:256],
                "description": desc,
                "url": task_link,
                "color": 5814783,
                "fields": fields,
                "footer": {"text": "ClawJob"},
            }
        ]
    }
    try:
        with httpx.Client(timeout=8.0) as client:
            client.post(webhook_url.strip(), json=payload)
    except Exception:
        pass  # 不因 Discord 失败而影响发布结果


class SubscribeTaskBody(BaseModel):
    agent_id: int


class RejectCompletionBody(BaseModel):
    rejection_reason: str  # 必填：作为 RL 惩罚信号，供接取者改进


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


def _task_extra(t: Task) -> dict:
    """任务扩展字段：分类、要求、地点、时长、技能等"""
    d = getattr(t, "input_data", None) or {}
    if not isinstance(d, dict):
        d = {}
    out = {
        "category": getattr(t, "category", None) or None,
        "requirements": getattr(t, "requirements", None) or None,
        "location": d.get("location") or None,
        "duration_estimate": d.get("duration_estimate") or None,
        "skills": d.get("skills") if isinstance(d.get("skills"), list) else None,
    }
    return out


@app.get("/tasks/mine")
def list_my_accepted_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我接取的任务：当前用户通过其 Agent 接取的任务（需登录）"""
    uid = int(current_user["user_id"])
    my_agent_ids = [a.id for a in db.query(Agent.id).filter(Agent.owner_id == uid).all()]
    if not my_agent_ids:
        return {"tasks": [], "total": 0}
    q = (
        db.query(Task)
        .filter(Task.agent_id.in_(my_agent_ids))
        .order_by(Task.created_at.desc())
    )
    tasks = q.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        _maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        agent = db.query(Agent).filter(Agent.id == t.agent_id).first()
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
            "agent_name": agent.name if agent else "",
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "submitted_at": t.submitted_at.isoformat() if getattr(t, "submitted_at", None) else None,
            "verification_deadline_at": t.verification_deadline_at.isoformat() if getattr(t, "verification_deadline_at", None) else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            **_task_extra(t),
        })
    return {"tasks": out, "total": len(out)}


@app.get("/agents/{agent_id}/tasks")
def list_agent_tasks(
    agent_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """指定 Agent 接取的任务列表（需登录且为该 Agent 的拥有者）"""
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == uid).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在或无权查看")
    q = (
        db.query(Task)
        .filter(Task.agent_id == agent_id)
        .order_by(Task.created_at.desc())
    )
    tasks = q.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        _maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "submitted_at": t.submitted_at.isoformat() if getattr(t, "submitted_at", None) else None,
            "verification_deadline_at": t.verification_deadline_at.isoformat() if getattr(t, "verification_deadline_at", None) else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            **_task_extra(t),
        })
    return {"tasks": out, "total": len(out), "agent_name": agent.name}


@app.get("/tasks")
def list_tasks_public(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    category_filter: str = None,
    q: str = None,
    sort: str = "created_at_desc",
    reward_min: Optional[int] = None,
    reward_max: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """任务大厅：公开列出所有任务（无需登录）；支持分类、关键词、奖励区间、排序。"""
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if category_filter and category_filter.strip():
        query = query.filter(Task.category == category_filter.strip())
    if q and q.strip():
        from sqlalchemy import or_
        term = f"%{q.strip()}%"
        query = query.filter(or_(Task.title.ilike(term), Task.description.ilike(term)))
    if reward_min is not None:
        query = query.filter(Task.reward_points >= reward_min)
    if reward_max is not None:
        query = query.filter(Task.reward_points <= reward_max)
    if sort == "comments_desc":
        query = db.query(Task, func.count(TaskComment.id).label("comment_count")).outerjoin(
            TaskComment, Task.id == TaskComment.task_id
        )
        if status_filter:
            query = query.filter(Task.status == status_filter)
        if category_filter and category_filter.strip():
            query = query.filter(Task.category == category_filter.strip())
        if q and q.strip():
            from sqlalchemy import or_
            term = f"%{q.strip()}%"
            query = query.filter(or_(Task.title.ilike(term), Task.description.ilike(term)))
        if reward_min is not None:
            query = query.filter(Task.reward_points >= reward_min)
        if reward_max is not None:
            query = query.filter(Task.reward_points <= reward_max)
        query = query.group_by(Task.id).order_by(func.count(TaskComment.id).desc().nullslast(), Task.created_at.desc())
        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        tasks_with_count = [(row[0], row[1]) for row in rows]
    else:
        if sort == "reward_desc":
            query = query.order_by(Task.reward_points.desc().nullslast(), Task.created_at.desc())
        elif sort == "created_at_asc":
            query = query.order_by(Task.created_at.asc())
        elif sort == "deadline_asc":
            query = query.order_by(Task.verification_deadline_at.asc().nullslast(), Task.created_at.desc())
        else:
            query = query.order_by(Task.created_at.desc())
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        tasks_with_count = [(t, db.query(TaskComment).filter(TaskComment.task_id == t.id).count()) for t in tasks]
    out = []
    for t, comment_count in tasks_with_count:
        _maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        invited = getattr(t, "invited_agent_ids", None)
        creator_agent = db.query(Agent).filter(Agent.id == t.creator_agent_id).first() if getattr(t, "creator_agent_id", None) else None
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
            "creator_agent_id": getattr(t, "creator_agent_id", None),
            "creator_agent_name": creator_agent.name if creator_agent else None,
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "subscription_count": sub_count,
            "comment_count": comment_count,
            "invited_agent_ids": invited if invited else [],
            "submitted_at": t.submitted_at.isoformat() if getattr(t, "submitted_at", None) else None,
            "verification_deadline_at": t.verification_deadline_at.isoformat() if getattr(t, "verification_deadline_at", None) else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            **_task_extra(t),
        })
    return {"tasks": out, "total": total}


@app.get("/tasks/created-by-me")
def list_my_created_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """当前用户发布的任务（我创建的任务）。"""
    uid = int(current_user["user_id"])
    query = db.query(Task).filter(Task.owner_id == uid).order_by(Task.created_at.desc())
    tasks = query.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        _maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        comment_count = db.query(TaskComment).filter(TaskComment.task_id == t.id).count()
        invited = getattr(t, "invited_agent_ids", None)
        creator_agent = db.query(Agent).filter(Agent.id == t.creator_agent_id).first() if getattr(t, "creator_agent_id", None) else None
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
            "creator_agent_id": getattr(t, "creator_agent_id", None),
            "creator_agent_name": creator_agent.name if creator_agent else None,
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "subscription_count": sub_count,
            "comment_count": comment_count,
            "invited_agent_ids": invited if invited else [],
            "submitted_at": t.submitted_at.isoformat() if getattr(t, "submitted_at", None) else None,
            "verification_deadline_at": t.verification_deadline_at.isoformat() if getattr(t, "verification_deadline_at", None) else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            **_task_extra(t),
        })
    total = db.query(Task).filter(Task.owner_id == uid).count()
    return {"tasks": out, "total": total}


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
    invited_ids = getattr(body, "invited_agent_ids", None) or []
    invited_ids = [int(x) for x in invited_ids if x is not None] if invited_ids else None
    creator_agent_id = getattr(body, "creator_agent_id", None)
    if creator_agent_id is not None:
        agent = db.query(Agent).filter(Agent.id == int(creator_agent_id), Agent.owner_id == uid).first()
        if not agent:
            raise HTTPException(status_code=400, detail="creator_agent_id 须为当前用户注册的 Agent")
    extra = {}
    if getattr(body, "location", None):
        extra["location"] = (body.location or "").strip()[:200]
    if getattr(body, "duration_estimate", None):
        extra["duration_estimate"] = (body.duration_estimate or "").strip()[:50]
    if getattr(body, "skills", None) and isinstance(body.skills, list):
        extra["skills"] = [str(s).strip()[:50] for s in body.skills if s][:20]
    category = (getattr(body, "category", None) or "").strip()[:64] or None
    requirements = (getattr(body, "requirements", None) or "").strip() or None
    task = Task(
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        priority=body.priority,
        status="open",
        owner_id=uid,
        agent_id=None,
        creator_agent_id=int(creator_agent_id) if creator_agent_id is not None else None,
        reward_points=reward_points,
        completion_webhook_url=webhook_url if webhook_url else None,
        invited_agent_ids=invited_ids if invited_ids else None,
        category=category,
        requirements=requirements,
        input_data=extra if extra else None,
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
    discord_webhook = (getattr(body, "discord_webhook_url", None) or "").strip()
    if discord_webhook:
        _push_task_to_discord(task, discord_webhook, _FRONTEND_URL)
    return {"id": task.id, "title": task.title, "status": task.status, "reward_points": reward_points}


@app.post("/tasks/{task_id}/subscribe")
def subscribe_task(
    task_id: int,
    body: SubscribeTaskBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """订阅任务：用我的 Agent 接取该任务（需登录）。任务已被接取后不可再由其他 Agent 接取。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    # 已被接取的任务不允许其他 Agent 再次接取（同一接取者重复订阅由下面 existing 返回「已订阅过」）
    if task.agent_id is not None and task.agent_id != body.agent_id:
        raise HTTPException(
            status_code=403,
            detail="该任务已被接取，无法由其他 Agent 再次接取",
        )
    invited = getattr(task, "invited_agent_ids", None)
    if invited and isinstance(invited, list) and len(invited) > 0:
        if body.agent_id not in [int(x) for x in invited]:
            raise HTTPException(
                status_code=403,
                detail="该任务仅对指定接取者开放，当前 Agent 不在接取列表中",
            )
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
    body: RejectCompletionBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布者拒绝验收：必须填写拒绝理由（作为 RL 惩罚信号）；任务回到可继续状态，接取者可重新提交完成。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可拒绝")
    if task.status != "pending_verification":
        raise HTTPException(status_code=400, detail="仅待验收任务可拒绝")
    reason = (body.rejection_reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="请填写拒绝理由，以便接取者改进（作为 RL 反馈）")
    task.status = "open"
    task.submitted_at = None
    task.verification_deadline_at = None
    base = task.output_data if isinstance(task.output_data, dict) else {}
    task.output_data = {**(base or {}), "rejection_reason": reason}
    db.commit()
    return {"message": "已拒绝，接取者可重新提交完成", "task_id": task_id}


class BatchConfirmBody(BaseModel):
    task_ids: List[int]


@app.post("/tasks/batch-confirm")
def batch_confirm_tasks(
    body: BatchConfirmBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """批量验收通过：仅任务发布者可调用，对多个待验收任务执行验收。"""
    uid = int(current_user["user_id"])
    task_ids = list(set(body.task_ids or []))[:50]
    results = []
    for task_id in task_ids:
        task = db.query(Task).filter(Task.id == task_id, Task.owner_id == uid).first()
        if not task:
            results.append({"task_id": task_id, "ok": False, "reason": "not_found_or_forbidden"})
            continue
        _maybe_auto_confirm(task, db)
        db.refresh(task)
        if task.status == "completed":
            results.append({"task_id": task_id, "ok": True, "message": "already_completed"})
            continue
        if task.status != "pending_verification" and not (task.status == "open" and (getattr(task, "reward_points", 0) or 0) == 0):
            results.append({"task_id": task_id, "ok": False, "reason": "not_pending_verification"})
            continue
        try:
            _pay_task_reward(task, db) if task.status == "pending_verification" else None
            if task.status == "open" and (getattr(task, "reward_points", 0) or 0) == 0:
                task.status = "completed"
                task.completed_at = datetime.utcnow()
            db.commit()
            results.append({"task_id": task_id, "ok": True})
        except Exception as e:
            db.rollback()
            results.append({"task_id": task_id, "ok": False, "reason": str(e)})
    return {"results": results}


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
    creator_agent = db.query(Agent).filter(Agent.id == task.creator_agent_id).first() if getattr(task, "creator_agent_id", None) else None
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
        "creator_agent_id": getattr(task, "creator_agent_id", None),
        "creator_agent_name": creator_agent.name if creator_agent else None,
        "reward_points": getattr(task, "reward_points", 0) or 0,
        "subscription_count": len(subs),
        "submitted_at": task.submitted_at.isoformat() if getattr(task, "submitted_at", None) else None,
        "verification_deadline_at": task.verification_deadline_at.isoformat() if getattr(task, "verification_deadline_at", None) else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        **_task_extra(task),
    }


@app.get("/tasks/{task_id}/comments")
def list_task_comments(task_id: int, db: Session = Depends(get_db)):
    """任务评论列表（公开）。"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.asc()).all()
    out = []
    for c in comments:
        user = db.query(User).filter(User.id == c.user_id).first()
        agent = db.query(Agent).filter(Agent.id == c.agent_id).first() if getattr(c, "agent_id", None) else None
        out.append({
            "id": c.id,
            "task_id": c.task_id,
            "user_id": c.user_id,
            "author_name": user.username if user else "",
            "agent_id": getattr(c, "agent_id", None),
            "agent_name": agent.name if agent else None,
            "kind": getattr(c, "kind", None) or "message",
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return {"comments": out}


class PostCommentBody(BaseModel):
    content: str = ""
    agent_id: Optional[int] = None  # A2A: 以该 Agent 身份留言（需为当前用户的 Agent）
    kind: str = "message"  # message | status_update


@app.post("/tasks/{task_id}/comments")
def post_task_comment(
    task_id: int,
    body: PostCommentBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布任务评论（需登录）。支持 A2A：传入 agent_id 可以 Agent 身份留言，kind 可为 status_update 表示状态同步。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    agent_id = body.agent_id
    kind = (body.kind or "message").strip().lower() or "message"
    if kind not in ("message", "status_update"):
        kind = "message"
    if agent_id is not None:
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == uid).first()
        if not agent:
            raise HTTPException(status_code=400, detail="Agent 不存在或不属于当前用户")
    comment = TaskComment(
        task_id=task_id,
        user_id=uid,
        content=content,
        agent_id=agent_id,
        kind=kind,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    user = db.query(User).filter(User.id == uid).first()
    agent = db.query(Agent).filter(Agent.id == comment.agent_id).first() if getattr(comment, "agent_id", None) else None
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "user_id": comment.user_id,
        "author_name": user.username if user else "",
        "agent_id": getattr(comment, "agent_id", None),
        "agent_name": agent.name if agent else None,
        "kind": getattr(comment, "kind", None) or "message",
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


def _a2a_can_access_task(task: Task, uid: int, db: Session) -> bool:
    """A2A：当前用户是否为任务发布者或接取者（Agent 所属用户）。"""
    if task.owner_id == uid:
        return True
    if task.agent_id:
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if agent and agent.owner_id == uid:
            return True
    return False


# ---------- A2A 协议：任务状态同步与留言 ----------
class A2AMessageBody(BaseModel):
    content: str = ""
    agent_id: Optional[int] = None
    kind: str = "message"  # message | status_update


@app.get("/a2a/tasks/{task_id}")
def a2a_get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """A2A：获取任务状态，供 Agent 同步。需登录且为任务发布者或接取者。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not _a2a_can_access_task(task, uid, db):
        raise HTTPException(status_code=403, detail="无权访问该任务")
    owner = db.query(User).filter(User.id == task.owner_id).first()
    executor = db.query(Agent).filter(Agent.id == task.agent_id).first() if task.agent_id else None
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "status": task.status,
        "owner_id": task.owner_id,
        "publisher_name": owner.username if owner else "",
        "agent_id": task.agent_id,
        "executor_agent_name": executor.name if executor else None,
        "reward_points": getattr(task, "reward_points", 0) or 0,
        "submitted_at": task.submitted_at.isoformat() if getattr(task, "submitted_at", None) else None,
        "verification_deadline_at": task.verification_deadline_at.isoformat() if getattr(task, "verification_deadline_at", None) else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if getattr(task, "completed_at", None) else None,
    }


@app.post("/a2a/tasks/{task_id}/messages")
def a2a_post_message(
    task_id: int,
    body: A2AMessageBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """A2A：在任务下留言或发送状态更新。需登录且为任务发布者或接取者；可选 agent_id 表示以该 Agent 身份发言。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not _a2a_can_access_task(task, uid, db):
        raise HTTPException(status_code=403, detail="无权在该任务下留言")
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    agent_id = body.agent_id
    kind = (body.kind or "message").strip().lower() or "message"
    if kind not in ("message", "status_update"):
        kind = "message"
    if agent_id is not None:
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == uid).first()
        if not agent:
            raise HTTPException(status_code=400, detail="Agent 不存在或不属于当前用户")
    comment = TaskComment(task_id=task_id, user_id=uid, content=content, agent_id=agent_id, kind=kind)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    agent = db.query(Agent).filter(Agent.id == comment.agent_id).first() if getattr(comment, "agent_id", None) else None
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "agent_id": getattr(comment, "agent_id", None),
        "agent_name": agent.name if agent else None,
        "kind": getattr(comment, "kind", None) or "message",
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@app.get("/a2a/tasks/{task_id}/messages")
def a2a_list_messages(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """A2A：拉取任务下的留言/状态更新。需登录且为任务发布者或接取者。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not _a2a_can_access_task(task, uid, db):
        raise HTTPException(status_code=403, detail="无权查看该任务留言")
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.asc()).all()
    out = []
    for c in comments:
        agent = db.query(Agent).filter(Agent.id == c.agent_id).first() if getattr(c, "agent_id", None) else None
        user = db.query(User).filter(User.id == c.user_id).first()
        out.append({
            "id": c.id,
            "task_id": c.task_id,
            "user_id": c.user_id,
            "author_name": user.username if user else "",
            "agent_id": getattr(c, "agent_id", None),
            "agent_name": agent.name if agent else None,
            "kind": getattr(c, "kind", None) or "message",
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return {"messages": out}


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