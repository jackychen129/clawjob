"""
ClawJob - Backend API
任务发布与接取平台：用户注册 Agent，发布任务，订阅他人任务。
"""
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Any
import os
import time
import uuid
import httpx
import asyncio
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
    SessionLocal,
    Task,
    Agent,
    PublishedAgentTemplate,
    PublishedSkill,
    TaskSubscription,
    TaskComment,
    User,
    SystemLog,
    CreditTransaction,
    PlatformClearingAccount,
    PlatformCommissionRecord,
    UserCommissionRecord,
)
from app.database.cache_db import CacheDB
from app.utils.datetime_iso import iso_utc
from app.services.escrow_tasks import (
    get_escrow,
    build_escrow_plan,
    save_escrow_to_task,
    apply_escrow_milestone_confirm,
)

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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录每次 API 请求到 system_logs 表，便于监控与审计。"""
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        path = request.scope.get("path") or ""
        method = request.method or ""
        status = response.status_code
        level = "error" if status >= 500 else ("warning" if status >= 400 else "info")
        try:
            db = SessionLocal()
            try:
                log = SystemLog(
                    level=level,
                    category="request",
                    message=f"{method} {path} {status} {duration_ms:.0f}ms",
                    path=path[:512] if path else None,
                    method=method[:16] if method else None,
                    status_code=status,
                    extra={"duration_ms": round(duration_ms, 2), "request_id": rid},
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception:
            pass
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
# 管理后台：指标与日志（仅 is_superuser 可访问）
from app.routers import admin as admin_router_module
from app.database.relational_db import get_db as _get_db
_admin_super_dep = admin_router_module.get_superuser_dep(get_current_user, _get_db)
app.include_router(admin_router_module.router, prefix="/admin", dependencies=[Depends(_admin_super_dep)])

# 限流：全局默认在 security.limiter 的 default_limits 中配置
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 安全头中间件（先添加，响应时最后执行）
app.add_middleware(SecurityHeadersMiddleware)
# 请求审计日志（记录到 system_logs）
app.add_middleware(RequestLoggingMiddleware)

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
            "at": iso_utc(at) or str(at),
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
            "at": iso_utc(t.created_at or datetime.utcnow()),
            "task_id": t.id,
            "task_title": (t.title or "")[:80],
            "publisher_name": owner.username if owner else None,
        })
    # 最近注册的 Agent
    agents = db.query(Agent, User).join(User, Agent.owner_id == User.id).order_by(Agent.created_at.desc()).limit(limit).all()
    for a, owner in agents:
        events.append({
            "type": "agent_registered",
            "at": iso_utc(a.created_at or datetime.utcnow()),
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
            "owner_name": _owner_display_name(owner.username if owner else None),
            "earned": int(earned),
            "tasks_completed": int(completed_count),
            "tasks_total": int(total_count),
            "success_rate": round(success_rate, 1),
            "certified": False,  # 预留：Playbook 验证后为 True
        })
    return {"items": out, "total": len(out)}


def _task_skills_for_xp(t: Task) -> List[str]:
    d = getattr(t, "input_data", None) or {}
    out: List[str] = []
    if isinstance(d, dict):
        skills = d.get("skills")
        if isinstance(skills, list):
            out.extend([str(s).strip() for s in skills if str(s).strip()])
    if not out and getattr(t, "category", None):
        out.append(str(getattr(t, "category")).strip())
    return list(dict.fromkeys(out))


def _level_from_xp(xp: int) -> dict:
    # 线性递增阈值：L1=100, L2=120, L3=140 ...
    level = 1
    remain = max(0, int(xp or 0))
    need = 100
    while remain >= need:
        remain -= need
        level += 1
        need = 100 + (level - 1) * 20
    progress = (remain / need) if need > 0 else 0
    return {"level": level, "xp_current": int(remain), "xp_next": int(need), "progress": round(progress, 4)}


def _agent_skill_xp_map(db: Session, agent_id: int) -> dict:
    tasks = db.query(Task).filter(Task.agent_id == agent_id, Task.status == "completed").all()
    xp_map: dict = {}
    for t in tasks:
        reward = int(getattr(t, "reward_points", 0) or 0)
        base_xp = max(10, min(80, reward // 2 if reward > 0 else 10))
        for s in _task_skills_for_xp(t):
            xp_map[s] = int(xp_map.get(s, 0) or 0) + base_xp
    return xp_map


@app.get("/agents/{agent_id}/skills")
def get_agent_skills(agent_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    if agent.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅 Agent 拥有者可查看技能进度")
    xp_map = _agent_skill_xp_map(db, agent_id)
    items = []
    for name, xp in sorted(xp_map.items(), key=lambda kv: (-kv[1], kv[0])):
        lv = _level_from_xp(int(xp))
        items.append({"name": name, "xp": int(xp), **lv})
    return {"agent_id": agent_id, "items": items}


@app.get("/account/skill-tree")
def get_my_skill_tree(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = int(current_user["user_id"])
    my_agents = db.query(Agent).filter(Agent.owner_id == uid).all()
    total: dict = {}
    for a in my_agents:
        xp_map = _agent_skill_xp_map(db, a.id)
        for k, v in xp_map.items():
            total[k] = int(total.get(k, 0) or 0) + int(v or 0)
    nodes = []
    for name, xp in sorted(total.items(), key=lambda kv: (-kv[1], kv[0])):
        lv = _level_from_xp(int(xp))
        nodes.append({"name": name, "xp": int(xp), **lv})
    return {"nodes": nodes[:24], "total_skills": len(nodes)}


@app.get("/stats/roi-series")
def get_roi_series(days: int = 14, db: Session = Depends(get_db)):
    # 收益时序（K 线简化版）：按天统计已完成任务总奖励与完成数
    d = max(7, min(90, int(days or 14)))
    start = datetime.utcnow() - timedelta(days=d - 1)
    tasks = db.query(Task).filter(Task.status == "completed", Task.completed_at.isnot(None), Task.completed_at >= start).all()
    bucket = {}
    for t in tasks:
        key = (t.completed_at or datetime.utcnow()).strftime("%Y-%m-%d")
        obj = bucket.get(key) or {"date": key, "rewards": 0, "tasks": 0}
        obj["rewards"] += int(getattr(t, "reward_points", 0) or 0)
        obj["tasks"] += 1
        bucket[key] = obj
    out = []
    for i in range(d):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        out.append(bucket.get(day) or {"date": day, "rewards": 0, "tasks": 0})
    return {"series": out, "days": d}


def _count_completed_tasks_for_agent(db: Session, agent_id: int) -> int:
    return db.query(Task).filter(Task.agent_id == agent_id, Task.status == "completed").count()


def _get_agent_ids_by_skill_token(db: Session, uid: Optional[int] = None, skill_token: str = "") -> List[int]:
    """根据 config.skill_bound_token 找到对应 Agent id。

    注：为兼容不同数据库 JSON 查询能力，这里使用 Python 方式筛选。
    """
    if not skill_token:
        return []
    q = db.query(Agent)
    if uid is not None:
        q = q.filter(Agent.owner_id == uid)
    agents = q.all()
    out: List[int] = []
    for a in agents:
        cfg = a.config or {}
        if cfg.get("skill_bound_token") == skill_token:
            out.append(a.id)
    return out


def _count_completed_tasks_for_skill_token(db: Session, skill_token: str) -> int:
    agent_ids = _get_agent_ids_by_skill_token(db, None, skill_token)
    if not agent_ids:
        return 0
    return db.query(Task).filter(Task.agent_id.in_(agent_ids), Task.status == "completed").count()


@app.get("/agent-templates")
def get_agent_templates(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    verified_only: bool = False,
    agent_type: Optional[str] = None,
    sort: str = "created_desc",  # created_desc | tasks_desc
):
    """Agent 模板 / Skill 市场：可下载的 Agent 模板与 Skill 列表（含平台 verify、完成任务数）。"""
    q = db.query(PublishedAgentTemplate).join(Agent)
    if verified_only:
        q = q.filter(PublishedAgentTemplate.verified.is_(True))
    if agent_type and agent_type.strip():
        q = q.filter(Agent.agent_type == agent_type.strip())
    if sort == "tasks_desc":
        rows = q.all()
        scored = [(t, _count_completed_tasks_for_agent(db, t.agent_id)) for t in rows]
        scored.sort(key=lambda x: (-x[1], -x[0].id))
        rows = [x[0] for x in scored]
    else:
        rows = q.order_by(PublishedAgentTemplate.created_at.desc()).all()
    total = len(rows)
    rows = rows[skip : skip + limit]
    items = []
    for t in rows:
        tasks_completed = _count_completed_tasks_for_agent(db, t.agent_id)
        owner = db.query(User).filter(User.id == t.agent.owner_id).first() if t.agent else None
        items.append({
            "id": t.id,
            "name": t.name,
            "description": t.description or "",
            "verified": t.verified,
            "version_tag": t.version_tag or "v1",
            "tasks_completed": tasks_completed,
            "agent_type": t.agent.agent_type if t.agent else None,
            "publisher_username": owner.username if owner else "",
            "publisher_user_id": t.agent.owner_id if t.agent else None,
            "download_agent_url": t.download_agent_url,
            "download_skill_url": t.download_skill_url,
            "created_at": iso_utc(t.created_at) if getattr(t, "created_at", None) else None,
        })
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@app.get("/agent-templates/stats")
def get_agent_templates_stats(db: Session = Depends(get_db)):
    """Agent 模板市场统计：模板数、已验证数、累计完成任务数。"""
    template_count = db.query(PublishedAgentTemplate).count()
    verified_count = db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.verified.is_(True)).count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    return {
        "template_count": template_count,
        "verified_count": verified_count,
        "tasks_completed": tasks_completed,
    }


class PublishAgentTemplateBody(BaseModel):
    """发布 Agent 为市场模板"""
    agent_id: int
    name: str
    description: str = ""
    version_tag: str = "v1"
    download_agent_url: Optional[str] = None
    download_skill_url: Optional[str] = None


@app.post("/agent-templates")
def publish_agent_template(
    body: PublishAgentTemplateBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """将本人名下、至少完成过 1 个任务的 Agent 发布为市场模板（一 Agent 仅可发布一条）。"""
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == body.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != uid:
        raise HTTPException(status_code=403, detail="Only the owner can publish this agent")
    completed = _count_completed_tasks_for_agent(db, agent.id)
    if completed < 1:
        raise HTTPException(status_code=400, detail="Agent must have at least one completed task to publish")
    existing = db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.agent_id == agent.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="This agent is already published as a template")
    name = (body.name or agent.name or "").strip() or agent.name
    version_tag = ((body.version_tag or "v1").strip() or "v1")[:64]
    template = PublishedAgentTemplate(
        agent_id=agent.id,
        name=name,
        description=(body.description or "").strip() or None,
        version_tag=version_tag,
        download_agent_url=(body.download_agent_url or "").strip() or None,
        download_skill_url=(body.download_skill_url or "").strip() or None,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    tasks_completed = _count_completed_tasks_for_agent(db, agent.id)
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description or "",
        "verified": template.verified,
        "version_tag": template.version_tag or "v1",
        "tasks_completed": tasks_completed,
        "agent_type": agent.agent_type,
        "download_agent_url": template.download_agent_url,
        "download_skill_url": template.download_skill_url,
    }

@app.delete("/agent-templates/{template_id}")
def delete_agent_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    me = db.query(User).filter(User.id == uid).first()
    tpl = db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    owner_id = tpl.agent.owner_id if tpl.agent else None
    if owner_id != uid and not (me and bool(getattr(me, "is_superuser", False))):
        raise HTTPException(status_code=403, detail="Only publisher/admin can delete template")
    db.delete(tpl)
    db.commit()
    return {"ok": True, "id": template_id}


class PublishSkillBody(BaseModel):
    """通过 Skill 发布到平台：生成/更新技能市场条目。"""
    # skill_token：用于与 Agent.config.skill_bound_token 对齐。
    # 若不传，则尝试从当前用户拥有的 Agent 中推导（必须恰好只有一个 token）。
    skill_token: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    version_tag: Optional[str] = "v1"
    download_skill_url: Optional[str] = None


def _publisher_for_skill_token(db: Session, skill_token: str) -> tuple:
    """返回 (publisher_username, publisher_user_id)。"""
    agents = db.query(Agent).all()
    for a in agents:
        cfg = a.config or {}
        if (cfg.get("skill_bound_token") or "").strip() == skill_token:
            u = db.query(User).filter(User.id == a.owner_id).first()
            return (u.username if u else "", a.owner_id)
    return ("", None)


@app.get("/skills")
def get_skills(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    verified_only: bool = False,
    sort: str = "created_desc",
):
    """Skill 市场：列出已发布 Skill，并给出完成任务数（用于 verify 展示）。"""
    q = db.query(PublishedSkill)
    if verified_only:
        q = q.filter(PublishedSkill.verified.is_(True))
    if sort == "tasks_desc":
        rows = q.all()
        scored = [(s, _count_completed_tasks_for_skill_token(db, s.skill_token)) for s in rows]
        scored.sort(key=lambda x: (-x[1], -x[0].id))
        rows = [x[0] for x in scored]
    else:
        rows = q.order_by(PublishedSkill.created_at.desc()).all()
    total = len(rows)
    rows = rows[skip : skip + limit]
    out = []
    for s in rows:
        tasks_completed = _count_completed_tasks_for_skill_token(db, s.skill_token)
        pub_name, pub_uid = _publisher_for_skill_token(db, s.skill_token)
        out.append({
            "id": s.id,
            "skill_token": s.skill_token,
            "name": s.name,
            "description": s.description or "",
            "verified": bool(s.verified),
            "version_tag": s.version_tag or "v1",
            "tasks_completed": int(tasks_completed),
            "download_skill_url": s.download_skill_url,
            "publisher_username": pub_name,
            "publisher_user_id": pub_uid,
            "created_at": iso_utc(s.created_at) if getattr(s, "created_at", None) else None,
        })
    return {"items": out, "total": total, "skip": skip, "limit": limit}


@app.get("/skills/stats")
def get_skills_stats(db: Session = Depends(get_db)):
    """Skill 市场统计：模板数、已验证数、累计完成任务数（基于 token 推导）。"""
    skills = db.query(PublishedSkill).all()
    skill_count = len(skills)
    verified_count = sum(1 for s in skills if bool(s.verified))
    tasks_completed_total = 0
    for s in skills:
        tasks_completed_total += _count_completed_tasks_for_skill_token(db, s.skill_token)
    return {
        "skill_count": skill_count,
        "verified_count": verified_count,
        "tasks_completed": tasks_completed_total,
    }


@app.post("/skills/publish")
def publish_skill(
    body: PublishSkillBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Skill 分享：让具备 Skill 的 OpenClaw 直接发布自己的 Skill 到平台。

    验证逻辑（简化）：
    - 必须能在当前用户名下找到至少一个 Agent，其 config.skill_bound_token 与 skill_token 对齐；
    - verified 默认为根据任务完成数推导：tasks_completed > 0 => True，否则 False。
    """
    uid = int(current_user["user_id"])
    skill_token = (body.skill_token or "").strip() if body.skill_token else ""

    # 不传 skill_token：尝试从用户拥有的 Agent 推导
    if not skill_token:
        tokens = set()
        my_agents = db.query(Agent).filter(Agent.owner_id == uid).all()
        for a in my_agents:
            cfg = a.config or {}
            tok = (cfg.get("skill_bound_token") or "").strip() if cfg else ""
            if tok:
                tokens.add(tok)
        tokens_list = sorted(list(tokens))
        if len(tokens_list) == 1:
            skill_token = tokens_list[0]
        elif len(tokens_list) == 0:
            raise HTTPException(status_code=400, detail="skill_token 未提供，且当前用户下没有可用的 skill_bound_token")
        else:
            raise HTTPException(status_code=400, detail="skill_token 未提供，当前用户下存在多个 skill_bound_token，请显式传入 skill_token")

    # 当前用户名下必须存在至少一个匹配 skill_token 的 Agent
    agent_ids = _get_agent_ids_by_skill_token(db, uid=uid, skill_token=skill_token)
    if not agent_ids:
        raise HTTPException(status_code=403, detail="当前用户下未找到与该 skill_token 对齐的 Agent（请在注册 Agent 时设置 skill_bound_token）")

    tasks_completed = _count_completed_tasks_for_skill_token(db, skill_token)
    verified = tasks_completed > 0

    name = (body.name or "").strip() or f"Skill {skill_token[:8]}"
    description = (body.description or "").strip() if body.description else None
    version_tag = ((body.version_tag or "v1").strip() if body.version_tag else "v1")[:64] or "v1"
    download_skill_url = (body.download_skill_url or "").strip() if body.download_skill_url else None

    existing = db.query(PublishedSkill).filter(PublishedSkill.skill_token == skill_token).first()
    if existing:
        existing.name = name
        existing.description = description
        existing.download_skill_url = download_skill_url
        existing.version_tag = version_tag
        existing.verified = bool(verified)
        db.commit()
        db.refresh(existing)
        skill_id = existing.id
    else:
        row = PublishedSkill(
            skill_token=skill_token,
            name=name,
            description=description,
            verified=bool(verified),
            version_tag=version_tag,
            download_skill_url=download_skill_url,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        skill_id = row.id

    return {
        "id": skill_id,
        "skill_token": skill_token,
        "name": name,
        "description": description or "",
        "verified": bool(verified),
        "version_tag": version_tag,
        "tasks_completed": int(tasks_completed),
        "download_skill_url": download_skill_url,
    }


@app.delete("/skills/{skill_id}")
def delete_skill_publish(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    me = db.query(User).filter(User.id == uid).first()
    row = db.query(PublishedSkill).filter(PublishedSkill.id == skill_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Skill publish not found")
    owns_token = bool(_get_agent_ids_by_skill_token(db, uid=uid, skill_token=row.skill_token))
    if (not owns_token) and not (me and bool(getattr(me, "is_superuser", False))):
        raise HTTPException(status_code=403, detail="Only publisher/admin can delete skill publish")
    db.delete(row)
    db.commit()
    return {"ok": True, "id": skill_id}

# OpenClaw/Clawl 对齐：capability 项 { id?, name, category? }
class CapabilityItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: Optional[str] = None


# Agent 注册（在 DB 中创建，用于接取任务；参数对齐 OpenClaw agent 属性）
class RegisterAgentBody(BaseModel):
    name: str
    description: str = ""
    token: Optional[str] = None  # 可选：Agent 调用 API 时使用的 token，关联到本账户下该 Agent
    skill_bound_token: Optional[str] = None  # 可选：Skill 绑定 Token，供 OpenClaw Skill 等以该 Agent 身份调用
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
    """注册我的 Agent（需登录），用于接取/订阅他人任务。调用方须提供：当前使用的 token（请求头 Authorization: Bearer <token>）与 Agent 名称（Body 的 name）。参数对齐 OpenClaw/Clawl agent。"""
    _ensure_agents_category_column()
    uid = int(current_user["user_id"])
    primary_type = (body.agent_type or "general").strip() or "general"
    if body.types and len(body.types) > 0:
        primary_type = (body.types[0] or primary_type).strip() or primary_type
    capabilities = _norm_capabilities(body.capabilities) if body.capabilities else []
    config = {}
    if body.token and body.token.strip():
        config["agent_token"] = body.token.strip()
    if getattr(body, "skill_bound_token", None) and str(body.skill_bound_token).strip():
        config["skill_bound_token"] = str(body.skill_bound_token).strip()
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
        try:
            db.add(SystemLog(
                level="info",
                category="agent",
                message="agent_registered",
                user_id=uid,
                extra={"agent_id": agent.id, "agent_name": agent.name, "category": category},
            ))
            db.commit()
        except Exception:
            db.rollback()
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
            try:
                db.add(SystemLog(
                    level="info",
                    category="agent",
                    message="agent_registered",
                    user_id=uid,
                    extra={"agent_id": agent.id, "agent_name": agent.name, "category": category, "note": "retry_after_schema_fix"},
                ))
                db.commit()
            except Exception:
                db.rollback()
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

    def _build_agent_item(a: Agent, points: int = 0, published_template_id: Optional[int] = None, completed_task_count: int = 0) -> dict:
        cfg = a.config or {}
        return {
            "id": a.id,
            "name": a.name,
            "description": a.description or "",
            "agent_type": a.agent_type or "general",
            "category": getattr(a, "category", None) or "api",
            "capabilities": a.capabilities or [],
            "status": "active" if a.is_active else "inactive",
            "config": cfg,
            "has_skill_token": bool(cfg.get("skill_bound_token")),
            "points": int(points),
            "published_template_id": published_template_id,
            "completed_task_count": completed_task_count,
        }

    try:
        points_subq = (
            db.query(Task.agent_id, func.coalesce(func.sum(Task.reward_points), 0).label("points"))
            .filter(Task.status == "completed", Task.agent_id.isnot(None))
            .group_by(Task.agent_id)
            .subquery()
        )
        completed_subq = (
            db.query(Task.agent_id, func.count(Task.id).label("completed_count"))
            .filter(Task.status == "completed", Task.agent_id.isnot(None))
            .group_by(Task.agent_id)
            .subquery()
        )
        agent_ids = [r[0] for r in db.query(Agent.id).filter(Agent.owner_id == uid).all()]
        published_by_agent = {t.agent_id: t.id for t in db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.agent_id.in_(agent_ids)).all()} if agent_ids else {}
        rows = (
            db.query(Agent, func.coalesce(points_subq.c.points, 0).label("points"), func.coalesce(completed_subq.c.completed_count, 0).label("completed_count"))
            .outerjoin(points_subq, Agent.id == points_subq.c.agent_id)
            .outerjoin(completed_subq, Agent.id == completed_subq.c.agent_id)
            .filter(Agent.owner_id == uid)
            .order_by(points_subq.c.points.desc().nullslast(), Agent.id.desc())
            .all()
        )
        return {"agents": [_build_agent_item(a, points, published_by_agent.get(a.id), int(completed_count)) for a, points, completed_count in rows]}
    except Exception as e:
        db.rollback()
        err_msg = str(e).lower()
        if "column" in err_msg or "does not exist" in err_msg or "category" in err_msg:
            _ensure_agents_category_column()
        try:
            agents = db.query(Agent).filter(Agent.owner_id == uid).order_by(Agent.id.desc()).all()
            aid_list = [a.id for a in agents]
            pub = {t.agent_id: t.id for t in db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.agent_id.in_(aid_list)).all()} if aid_list else {}
            completed_map = {r[0]: r[1] for r in db.query(Task.agent_id, func.count(Task.id)).filter(Task.status == "completed", Task.agent_id.in_(aid_list)).group_by(Task.agent_id).all()} if aid_list else {}
            return {"agents": [_build_agent_item(a, 0, pub.get(a.id), completed_map.get(a.id, 0)) for a in agents]}
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
    """候选者列表（公开）：已注册的 Agent、所属用户（游客显示「待注册」）、具备的 Skill（capabilities）、发布任务数。"""
    points_subq = (
        db.query(Task.agent_id, func.coalesce(func.sum(Task.reward_points), 0).label("points"))
        .filter(Task.status == "completed", Task.agent_id.isnot(None))
        .group_by(Task.agent_id)
        .subquery()
    )
    published_subq = (
        db.query(Task.creator_agent_id, func.count(Task.id).label("published_count"))
        .filter(Task.creator_agent_id.isnot(None))
        .group_by(Task.creator_agent_id)
        .subquery()
    )
    q = (
        db.query(Agent, User, func.coalesce(points_subq.c.points, 0).label("points"), func.coalesce(published_subq.c.published_count, 0).label("published_count"))
        .join(User, Agent.owner_id == User.id)
        .outerjoin(points_subq, Agent.id == points_subq.c.agent_id)
        .outerjoin(published_subq, Agent.id == published_subq.c.creator_agent_id)
        .filter(Agent.is_active == True, User.is_active == True)
    )
    if (sort or "").strip().lower() == "recent":
        q = q.order_by(Agent.id.desc())
    else:
        q = q.order_by(points_subq.c.points.desc().nullslast(), Agent.id.desc())
    rows = q.offset(skip).limit(limit).all()
    out = []
    for row in rows:
        a, owner, points, published_count = row
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
            "owner_name": _owner_display_name(owner.username if owner else None),
            "points": int(points),
            "published_count": int(published_count),
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


class EscrowMilestoneIn(BaseModel):
    """托管里程碑：title + weight + acceptance_criteria（weight 之和须为 1）"""

    title: str
    weight: float
    acceptance_criteria: str = ""


class PublishTaskBody(BaseModel):
    title: str
    description: str = ""
    task_type: str = "general"
    priority: str = "medium"
    reward_points: int = 0  # 任务奖励点（发布时从账户扣减，验收通过或超时后发给接取者）
    completion_webhook_url: str = ""  # 有奖励点时必填：接取者提交完成时 POST 回调此 URL，供发布方验收
    invited_agent_ids: list = []  # 可选：仅这些 Agent 可接取；空表示对所有人开放
    creator_agent_id: Optional[int] = None  # 可选：由某 Agent 代发（须为当前用户的 Agent）
    # 托管（Escrow）MVP：多里程碑；至少 2 项且权重和为 1，与 6 小时自动验收按里程碑生效
    escrow_milestones: List[EscrowMilestoneIn] = []
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


class EscrowDisputeBody(BaseModel):
    reason: str
    evidence: dict = {}


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


CLAWJOB_SYSTEM_USERNAME = "clawjob_system"
CLAWJOB_SYSTEM_AGENT_NAME = "clawjob-agent"


def _owner_display_name(username: Optional[str]) -> str:
    """拥有者展示名：游客账号显示「待注册」，否则显示用户名。"""
    if not username or (isinstance(username, str) and username.startswith("guest_")):
        return "待注册"
    return username


def _get_or_create_clawjob_system_agent(db: Session):
    """获取或创建平台引导用系统 Agent（clawjob-agent），用于用户通过 Skill 发布的第一个任务自动接取并完成。返回 (User, Agent)。"""
    user = db.query(User).filter(User.username == CLAWJOB_SYSTEM_USERNAME).first()
    if not user:
        user = User(
            username=CLAWJOB_SYSTEM_USERNAME,
            email="system@clawjob.local",
            hashed_password="",
        )
        db.add(user)
        db.flush()
    _ensure_agents_category_column()
    agent = db.query(Agent).filter(
        Agent.owner_id == user.id,
        Agent.name == CLAWJOB_SYSTEM_AGENT_NAME,
    ).first()
    if not agent:
        agent = Agent(
            name=CLAWJOB_SYSTEM_AGENT_NAME,
            description="平台引导 Agent：用户通过 Skill 发布的第一个任务将由此 Agent 自动接取并完成。",
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
    if not (deadline and datetime.utcnow() >= deadline):
        return
    esc = get_escrow(task)
    if esc and esc.get("disputed"):
        return
    if esc:
        apply_escrow_milestone_confirm(task, db, auto=True)
        db.commit()
        return
    _pay_task_reward(task, db)
    db.commit()


def _task_extra(t: Task) -> dict:
    """任务扩展字段：分类、要求、地点、时长、技能等"""
    d = getattr(t, "input_data", None) or {}
    if not isinstance(d, dict):
        d = {}
    esc = get_escrow(t)
    out = {
        "category": getattr(t, "category", None) or None,
        "requirements": getattr(t, "requirements", None) or None,
        "location": d.get("location") or None,
        "duration_estimate": d.get("duration_estimate") or None,
        "skills": d.get("skills") if isinstance(d.get("skills"), list) else None,
    }
    if esc:
        ms = esc.get("milestones") or []
        idx = int(esc.get("current_index", 0) or 0)
        out["escrow"] = {
            "enabled": True,
            "milestone_count": len(ms),
            "current_index": idx,
            "released_points": int(esc.get("released_points", 0) or 0),
            "disputed": bool(esc.get("disputed")),
            "milestones_preview": [
                {
                    "title": m.get("title"),
                    "points": m.get("points"),
                    "acceptance_criteria": m.get("acceptance_criteria"),
                }
                for m in ms[:20]
            ],
            "dispute_reason": (esc.get("dispute_reason") or None),
            "dispute_evidence": esc.get("dispute_evidence") or None,
            "admin_resolve_note": (esc.get("admin_resolve_note") or None),
        }
    else:
        out["escrow"] = {"enabled": False}
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
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
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
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **_task_extra(t),
        })
    return {"tasks": out, "total": len(out), "agent_name": agent.name}


@app.get("/tasks")
def list_tasks_public(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    category_filter: str = None,
    creator_agent_id: Optional[int] = None,
    q: str = None,
    sort: str = "created_at_desc",
    reward_min: Optional[int] = None,
    reward_max: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """任务大厅：公开列出所有任务（无需登录）；支持分类、关键词、奖励区间、排序；creator_agent_id 可筛选某 Agent 发布的任务。"""
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if category_filter and category_filter.strip():
        query = query.filter(Task.category == category_filter.strip())
    if creator_agent_id is not None:
        query = query.filter(Task.creator_agent_id == creator_agent_id)
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
        if creator_agent_id is not None:
            query = query.filter(Task.creator_agent_id == creator_agent_id)
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
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **_task_extra(t),
        })
    return JSONResponse(
        content={"tasks": out, "total": total},
        headers={"Cache-Control": "no-store, max-age=0"},
    )


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
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
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
    # 托管里程碑计划
    em = getattr(body, "escrow_milestones", None) or []
    if em:
        try:
            plan = build_escrow_plan(
                [{"title": x.title, "weight": x.weight, "acceptance_criteria": getattr(x, "acceptance_criteria", "")} for x in em],
                reward_points,
            )
            extra["escrow"] = plan
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
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
    try:
        db.add(SystemLog(
            level="info",
            category="task",
            message="task_published",
            user_id=uid,
            extra={"task_id": task.id, "reward_points": reward_points, "category": category},
        ))
        db.commit()
    except Exception:
        db.rollback()
    # 用户通过 Skill/API 发布的第一个任务：由 clawjob-agent 自动接取并完成（可配置）
    auto_complete_enabled = os.getenv("AUTO_COMPLETE_FIRST_TASK", "").strip().lower() in ("1", "true", "yes", "on")
    # 生产环境默认开启，pytest 下自动关闭，避免影响订阅/验收等回归用例
    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
    if os.getenv("ENV", "").strip().lower() == "production":
        auto_complete_enabled = True
    first_task_count = db.query(Task).filter(Task.owner_id == uid).count()
    if first_task_count == 1 and auto_complete_enabled and not is_pytest and not get_escrow(task):
        try:
            _, clawjob_agent = _get_or_create_clawjob_system_agent(db)
            sub = TaskSubscription(task_id=task.id, agent_id=clawjob_agent.id)
            db.add(sub)
            task.agent_id = clawjob_agent.id
            task.status = "completed"
            task.submitted_at = datetime.utcnow()
            task.completed_at = datetime.utcnow()
            base = task.output_data if isinstance(task.output_data, dict) else {}
            task.output_data = {
                **base,
                "result_summary": "首个任务由 ClawJob 引导 Agent 自动完成，便于体验流程。",
                "auto_completed_by": CLAWJOB_SYSTEM_AGENT_NAME,
            }
            db.commit()
            db.refresh(task)
            if reward_points > 0:
                _pay_task_reward(task, db)
                db.commit()
        except Exception:
            db.rollback()
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
    if get_escrow(task) and task.status == "open":
        task.status = "in_progress"
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
    escrow = get_escrow(task)
    if escrow and escrow.get("disputed"):
        raise HTTPException(status_code=400, detail="任务处于争议中，请等待处理后再提交")
    if task.status == "pending_verification":
        return {"message": "已提交验收，请等待发布者确认或 6 小时后自动完成", "task_id": task_id}
    if escrow and task.status not in ("open", "in_progress"):
        raise HTTPException(status_code=400, detail="当前任务状态不可提交里程碑交付")
    webhook_url = getattr(task, "completion_webhook_url", None) or ""
    reward_points = getattr(task, "reward_points", 0) or 0
    if reward_points > 0 and not webhook_url:
        raise HTTPException(status_code=400, detail="该任务设置了奖励点，未配置完成回调，无法提交")
    payload = None
    if webhook_url:
        payload = {
            "task_id": task_id,
            "title": task.title,
            "agent_id": task.agent_id,
            "agent_name": agent.name,
            "result_summary": body.result_summary or "",
            "evidence": body.evidence or {},
            "submitted_at": datetime.utcnow().isoformat() + "Z",
        }
        if escrow:
            idx = int(escrow.get("current_index", 0) or 0)
            ms = escrow.get("milestones") or []
            payload["escrow_milestone_index"] = idx
            payload["escrow_milestone_title"] = ms[idx].get("title") if idx < len(ms) else None
            payload["escrow_current_acceptance_criteria"] = ms[idx].get("acceptance_criteria") if idx < len(ms) else None
            payload["escrow_total_milestones"] = len(ms)
        max_attempts = 3
        last_err: Optional[str] = None
        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(timeout=10.0) as client:
                    r = client.post(webhook_url, json=payload)
                if r.status_code < 400:
                    last_err = None
                    break
                if 400 <= r.status_code < 500:
                    raise HTTPException(
                        status_code=502,
                        detail=f"完成回调返回异常：{r.status_code}，发布方需验收通过后再在平台确认",
                    )
                last_err = f"完成回调返回异常：{r.status_code}"
            except httpx.RequestError as e:
                last_err = f"调用完成回调失败：{str(e)}"
            if attempt < max_attempts:
                time.sleep(0.2 * attempt)
        if last_err:
            raise HTTPException(status_code=502, detail=f"{last_err}（已重试 {max_attempts} 次）")
    task.status = "pending_verification"
    task.submitted_at = datetime.utcnow()
    task.verification_deadline_at = datetime.utcnow() + timedelta(hours=VERIFICATION_HOURS)
    if body.result_summary or body.evidence:
        base = task.output_data if isinstance(task.output_data, dict) else {}
        task.output_data = {**(base or {}), "result_summary": body.result_summary or "", "evidence": body.evidence or {}}
    if escrow:
        base = task.output_data if isinstance(task.output_data, dict) else {}
        idx = int(escrow.get("current_index", 0) or 0)
        task.output_data = {**(base or {}), "escrow_submit_milestone_index": idx}
    db.commit()
    return {
        "message": "已提交验收，发布者需在 6 小时内确认，否则将自动完成并发奖",
        "task_id": task_id,
        "verification_deadline_at": iso_utc(task.verification_deadline_at),
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
    escrow = get_escrow(task)
    if task.status == "pending_verification" and escrow:
        info = apply_escrow_milestone_confirm(task, db, auto=False)
        db.commit()
        msg = (
            "托管里程碑验收通过，奖励已发放"
            if not info.get("escrow_finished")
            else "托管任务已全部完成，奖励已发放"
        )
        return {
            "message": msg,
            "task_id": task_id,
            "reward_paid": info.get("reward_paid", 0),
            "reward_total": reward_points,
            "commission": info.get("commission", 0),
            "escrow": {
                "milestone_index": info.get("milestone_index"),
                "finished": bool(info.get("escrow_finished")),
            },
        }
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
    task.status = "in_progress" if get_escrow(task) else "open"
    task.submitted_at = None
    task.verification_deadline_at = None
    base = task.output_data if isinstance(task.output_data, dict) else {}
    task.output_data = {**(base or {}), "rejection_reason": reason}
    db.commit()
    return {"message": "已拒绝，接取者可重新提交完成", "task_id": task_id}


@app.post("/tasks/{task_id}/escrow/dispute")
def escrow_dispute(
    task_id: int,
    body: EscrowDisputeBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """托管争议：发布方或接取方发起，任务进入 disputed，暂停提交与放款直至管理员处理。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    escrow = get_escrow(task)
    if not escrow:
        raise HTTPException(status_code=400, detail="该任务未启用托管里程碑")
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="任务已完成，无法发起争议")
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="请填写争议说明")
    evidence = body.evidence if isinstance(body.evidence, dict) else {}
    is_pub = task.owner_id == uid
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first() if task.agent_id else None
    is_exe = agent and agent.owner_id == uid
    if not is_pub and not is_exe:
        raise HTTPException(status_code=403, detail="仅发布方或接取方可发起托管争议")
    escrow["disputed"] = True
    escrow["dispute_reason"] = reason[:4000]
    # 争议证据：限制到合理体量，避免 input_data 被滥用过大
    try:
        # 截断所有字符串字段，避免存储超大文本
        def _trim_obj(x, max_len: int = 4000):
            if isinstance(x, str):
                return x[:max_len]
            if isinstance(x, list):
                return [_trim_obj(i, max_len) for i in x[:20]]
            if isinstance(x, dict):
                out = {}
                for k, v in list(x.items())[:20]:
                    out[str(k)[:50]] = _trim_obj(v, max_len)
                return out
            return x

        escrow["dispute_evidence"] = _trim_obj(evidence, 4000)
    except Exception:
        escrow["dispute_evidence"] = {}
    save_escrow_to_task(task, escrow)
    task.status = "disputed"
    db.commit()
    try:
        db.add(
            SystemLog(
                level="warning",
                category="task",
                message="escrow_dispute",
                user_id=uid,
                extra={"task_id": task_id, "reason_preview": reason[:200]},
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "已记录托管争议，任务已冻结", "task_id": task_id}


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
            if task.status == "pending_verification" and get_escrow(task):
                apply_escrow_milestone_confirm(task, db, auto=False)
            elif task.status == "pending_verification":
                _pay_task_reward(task, db)
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
        "submitted_at": iso_utc(getattr(task, "submitted_at", None)),
        "verification_deadline_at": iso_utc(getattr(task, "verification_deadline_at", None)),
        "created_at": iso_utc(task.created_at),
        "output_data": task.output_data if isinstance(getattr(task, "output_data", None), dict) else None,
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
            "created_at": iso_utc(c.created_at),
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
        "created_at": iso_utc(comment.created_at),
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
        "submitted_at": iso_utc(getattr(task, "submitted_at", None)),
        "verification_deadline_at": iso_utc(getattr(task, "verification_deadline_at", None)),
        "created_at": iso_utc(task.created_at),
        "completed_at": iso_utc(getattr(task, "completed_at", None)),
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
        "created_at": iso_utc(comment.created_at),
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
            "created_at": iso_utc(c.created_at),
        })
    return {"messages": out}


@app.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, retry_count: int = 0, current_user: str = Depends(get_current_user)):
    """Execute a task using available agents（支持失败自动重试）。"""
    retries = max(0, min(3, int(retry_count or 0)))
    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        try:
            result = await task_system.execute_task(task_id, current_user)
            if attempt > 0 and isinstance(result, dict):
                result["retried"] = attempt
            return result
        except Exception as e:
            last_err = str(e)
            if attempt < retries:
                await asyncio.sleep(0.2 * (attempt + 1))
                continue
            raise HTTPException(status_code=500, detail=f"执行失败：{last_err}（已重试 {retries} 次）")


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
            {"id": r.id, "amount": r.amount, "task_id": r.task_id, "remark": r.remark or "", "created_at": iso_utc(r.created_at)}
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