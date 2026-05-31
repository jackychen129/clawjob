"""
ClawJob - Backend API
任务发布与接取平台：用户注册 Agent，发布任务，订阅他人任务。
"""
from fastapi import FastAPI, Depends, HTTPException, Request, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import func, text, desc
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict, Tuple
import copy
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
    InternalMessage,
    TaskBid,
    Referral,
    SafetyEvent,
    ExecutionRun,
    ExecutionStep,
)
from app.database.cache_db import CacheDB
from app.utils.datetime_iso import iso_utc
from app.services.escrow_tasks import (
    get_escrow,
    build_escrow_plan,
    save_escrow_to_task,
    apply_escrow_milestone_confirm,
)
from app.services import reverse_auction as _ra
from app.services import safety_pipeline as _safety
from app.services import execution_sandbox as _sandbox
from app.services import step_replay as _replay
from app.services import insights as _insights
from app.services.preflight import run_preflight, enforce_preflight
from app.services.skill_contract import validate_contract, validate_payload
from app.services.workflow_dag import validate_workflow_dag, predecessors
from app.services.task_timeline import append_timeline_event as _append_timeline_event

# Agent system imports
from app.agents.agent_manager import AgentManager

# Security & routers
from app.security import get_current_user, get_current_user_optional, limiter
from app.routers import auth
from app.routers import account
from app.routers import community as community_router

from app.domain.skill_xp import (
    agent_skill_xp_map,
    apply_skill_decay,
    level_from_xp,
    skill_decay_meta,
    task_related_skill,
    task_skills_for_xp,
)
from app.domain.task_helpers import (
    CLAWJOB_SYSTEM_USERNAME,
    MAX_TASK_REWARD_POINTS,
    SKILL_DECAY_IDLE_DAYS,
    SKILL_DECAY_MAX_RATIO,
    SKILL_DECAY_WEEKLY_RATIO,
    VERIFICATION_HOURS,
    compute_publish_fee as _compute_publish_fee,
    env_float as _env_float,
    env_int as _env_int,
    get_or_create_clearing_account,
    intent_rate_bucket as _intent_rate_bucket,
    INTENT_RATE_LIMIT_MAX as _INTENT_RATE_LIMIT_MAX,
    INTENT_RATE_LIMIT_WINDOW as _INTENT_RATE_LIMIT_WINDOW,
    owner_display_name as _owner_display_name,
    task_extra as _task_extra,
    task_is_public_listing,
)

_CLAWJOB_ENTERPRISE = os.getenv("CLAWJOB_ENTERPRISE", "0").strip() not in ("0", "false", "no", "")


def _safe_int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except (TypeError, ValueError):
        return default


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应添加安全头（CSP、X-Frame-Options 等），满足线上安全要求。"""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # NOTE: translated comment in English.
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
    community_stop = None
    community_task = None
    if os.getenv("CLAWJOB_COMMUNITY_BACKGROUND_JOBS", "1").strip() != "0":
        from app.services.community_jobs import run_community_background_loop

        community_stop = asyncio.Event()
        community_task = asyncio.create_task(run_community_background_loop(community_stop))
    yield
    if community_stop is not None and community_task is not None:
        community_stop.set()
        community_task.cancel()
        try:
            await community_task
        except asyncio.CancelledError:
            pass
    # NOTE: translated comment in English.


app = FastAPI(
    title="ClawJob API",
    description="任务发布与接取：注册 Agent、发布任务、订阅他人任务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
)

from app.core.systems import (
    agent_manager,
    cache_db,
    memory_system,
    relational_db,
    runtime_guard,
    task_system,
    tool_system,
    vector_db,
)

# Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.include_router(auth.router)
app.include_router(account.router)
if _CLAWJOB_ENTERPRISE:
    from app.routers import kyc as kyc_router
    from app.routers import workspaces as workspaces_router
    from app.routers import billing as billing_router

    app.include_router(kyc_router.router)
    app.include_router(kyc_router.withdraw_router)
    app.include_router(workspaces_router.router)
    app.include_router(billing_router.router)
app.include_router(community_router.router)
from app.routers import tasks as tasks_router
from app.routers import agents as agents_router
from app.routers import messages as messages_router

app.include_router(tasks_router.router)
app.include_router(agents_router.router)
app.include_router(messages_router.router)
# NOTE: translated comment in English.
from app.routers import admin as admin_router_module
from app.database.relational_db import get_db as _get_db
_admin_super_dep = admin_router_module.get_superuser_dep(get_current_user, _get_db)
app.include_router(admin_router_module.router, prefix="/admin", dependencies=[Depends(_admin_super_dep)])

# NOTE: translated comment in English.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# NOTE: translated comment in English.
app.add_middleware(SecurityHeadersMiddleware)
# NOTE: translated comment in English.
app.add_middleware(RequestLoggingMiddleware)

# NOTE: translated comment in English.
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
        },
        "features": {
            "enterprise_enabled": _CLAWJOB_ENTERPRISE,
            "community_enabled": os.getenv("CLAWJOB_COMMUNITY_ENABLED", "1").strip() != "0",
            "community_hot_dispatch_enabled": os.getenv("CLAWJOB_COMMUNITY_HOT_DISPATCH_ENABLED", "1").strip() != "0",
            "community_background_jobs": os.getenv("CLAWJOB_COMMUNITY_BACKGROUND_JOBS", "1").strip() != "0",
            "community_dispatch_interval_sec": max(60, _safe_int_env("CLAWJOB_COMMUNITY_DISPATCH_INTERVAL_SEC", 900)),
        },
    }


@app.get("/stats")
def get_public_stats(db: Session = Depends(get_db)):
    """公开统计：任务总数、开放数、已完成数、活跃 Agent、累计发放报酬（供首页/官网 Counters 与 Dashboard）。"""
    from app.domain.agent_public import count_public_agents, count_total_agents

    tasks_count = db.query(Task).count()
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0
    agents_count_public = count_public_agents(db)
    agents_count_total = count_total_agents(db)
    agents_active = db.query(Agent).filter(Agent.is_active == True).count()
    agents_with_completions = db.query(Task.agent_id).filter(
        Task.status == "completed", Task.agent_id.isnot(None)
    ).distinct().count()
    return {
        "tasks_count": tasks_count,
        "tasks_open": tasks_open,
        "agents_count": agents_count_public,
        "agents_count_public": agents_count_public,
        "agents_count_total": agents_count_total,
        "tasks_total": tasks_count,
        "tasks_completed": tasks_completed,
        "rewards_paid": int(rewards_paid),
        "agents_active": agents_active,
        "agents_with_completions": agents_with_completions,
    }


@app.get("/stats/recent-agents")
def get_recent_agents_count(db: Session = Depends(get_db)):
    """近 7 天新注册 Agent 数量（无 PII，供 Dashboard 社交证明）。"""
    from app.domain.agent_public import count_public_agents, count_total_agents

    since = datetime.utcnow() - timedelta(days=7)
    return {
        "recent_agents_7d": int(count_public_agents(db, since=since)),
        "recent_agents_7d_total": int(count_total_agents(db, since=since)),
        "period_days": 7,
    }


@app.get("/public/agent-opportunities.json")
def get_agent_opportunities_feed(db: Session = Depends(get_db)):
    """机器可读 Agent 发现 feed：开放任务、Top 奖励、注册 curl、邀请与护城河摘要。"""
    from app.services.agent_discovery import build_agent_opportunities_feed

    return build_agent_opportunities_feed(db)


def _activity_agent_is_internal(agent: Agent, owner: Optional[User]) -> bool:
    """判断 Agent 是否不应进入公开 Live feed。"""
    from app.domain.agent_public import agent_is_public

    return not agent_is_public(agent, owner)


@app.get("/activity")
def get_activity(limit: int = 50, db: Session = Depends(get_db)):
    """实时动态流：最近任务发布、任务完成、Agent 注册。用于 Dashboard Live Feed。

    过滤掉 hidden_from_public/register_via_skill 握手任务、clawjob_system 拥有的任务，
    以及内部部署探活 Agent（DeployProbe_* 等）——保证首页看到的都是真实业务动态。
    """
    events = []
    # NOTE: pull 3x limit per stream so that after filtering we still have enough results.
    fetch_n = max(limit * 3, limit + 20)
    completed = (
        db.query(Task, Agent, User)
        .outerjoin(Agent, Task.agent_id == Agent.id)
        .join(User, Task.owner_id == User.id)
        .filter(Task.status == "completed")
        .order_by(Task.completed_at.desc().nullslast(), Task.updated_at.desc())
        .limit(fetch_n)
    ).all()
    for t, a, owner in completed:
        if not task_is_public_listing(t, owner):
            continue
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
    created = (
        db.query(Task, User)
        .join(User, Task.owner_id == User.id)
        .filter(Task.status == "open")
        .order_by(Task.created_at.desc())
        .limit(fetch_n)
    ).all()
    for t, owner in created:
        if not task_is_public_listing(t, owner):
            continue
        events.append({
            "type": "task_created",
            "at": iso_utc(t.created_at or datetime.utcnow()),
            "task_id": t.id,
            "task_title": (t.title or "")[:80],
            "publisher_name": owner.username if owner else None,
        })
    agents = (
        db.query(Agent, User)
        .join(User, Agent.owner_id == User.id)
        .order_by(Agent.created_at.desc())
        .limit(fetch_n)
    ).all()
    for a, owner in agents:
        if _activity_agent_is_internal(a, owner):
            continue
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
    # NOTE: translated comment in English.
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
    from app.domain.agent_public import apply_public_agent_filters, filter_public_agent_rows

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
    )
    q = apply_public_agent_filters(q)
    fetch_n = max(limit * 3, limit + 20)
    rows = (
        q.order_by(completed_subq.c.earned.desc().nullslast(), Agent.id.desc())
        .offset(skip)
        .limit(fetch_n)
        .all()
    )
    rows = filter_public_agent_rows(rows)[:limit]
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




@app.get("/agents/{agent_id}/skills")
def get_agent_skills(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """技能维度 XP：公开可读（便于 Agent 主页展示）；折旧策略详情仅拥有者可见。"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    uid = None
    if current_user and current_user.get("user_id") is not None:
        try:
            uid = int(current_user["user_id"])
        except (TypeError, ValueError):
            uid = None
    is_owner = uid is not None and int(agent.owner_id) == uid
    tasks = db.query(Task).filter(Task.agent_id == agent_id, Task.status == "completed").all()
    xp_map = agent_skill_xp_map(db, agent_id)
    dec = skill_decay_meta(tasks)
    xp_map = apply_skill_decay(xp_map, float(dec.get("ratio") or 0.0))
    items = []
    for name, xp in sorted(xp_map.items(), key=lambda kv: (-kv[1], kv[0])):
        lv = level_from_xp(int(xp))
        items.append({"name": name, "xp": int(xp), **lv})
    decay_out: Dict[str, Any] = {
        "ratio": float(dec.get("ratio") or 0.0),
        "last_active_at": iso_utc(dec.get("last_active_at")),
    }
    if is_owner:
        decay_out["policy"] = {
            "idle_days": SKILL_DECAY_IDLE_DAYS,
            "weekly_ratio": SKILL_DECAY_WEEKLY_RATIO,
            "max_ratio": SKILL_DECAY_MAX_RATIO,
        }
    return {
        "agent_id": agent_id,
        "items": items,
        "decay": decay_out,
        "viewer_is_owner": is_owner,
    }


@app.get("/account/skill-tree")
def get_my_skill_tree(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = int(current_user["user_id"])
    my_agents = db.query(Agent).filter(Agent.owner_id == uid).all()
    total: dict = {}
    max_decay = 0.0
    latest_active: Optional[datetime] = None
    for a in my_agents:
        tasks = db.query(Task).filter(Task.agent_id == a.id, Task.status == "completed").all()
        xp_map = agent_skill_xp_map(db, a.id)
        dec = skill_decay_meta(tasks)
        ratio = float(dec.get("ratio") or 0.0)
        xp_map = apply_skill_decay(xp_map, ratio)
        if ratio > max_decay:
            max_decay = ratio
        la = dec.get("last_active_at")
        if la and (latest_active is None or la > latest_active):
            latest_active = la
        for k, v in xp_map.items():
            total[k] = int(total.get(k, 0) or 0) + int(v or 0)
    nodes = []
    for name, xp in sorted(total.items(), key=lambda kv: (-kv[1], kv[0])):
        lv = level_from_xp(int(xp))
        nodes.append({"name": name, "xp": int(xp), **lv})
    return {
        "nodes": nodes[:24],
        "total_skills": len(nodes),
        "decay": {
            "max_ratio": float(round(max_decay, 4)),
            "last_active_at": iso_utc(latest_active),
            "policy": {
                "idle_days": SKILL_DECAY_IDLE_DAYS,
                "weekly_ratio": SKILL_DECAY_WEEKLY_RATIO,
                "max_ratio": SKILL_DECAY_MAX_RATIO,
            },
        },
    }


@app.get("/stats/roi-series")
def get_roi_series(days: int = 14, db: Session = Depends(get_db)):
    # NOTE: translated comment in English.
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
    # NOTE: translated comment in English.
    # NOTE: translated comment in English.
    skill_token: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    version_tag: Optional[str] = "v1"
    download_skill_url: Optional[str] = None
    contract_schema: Optional[dict] = None
    failure_semantics: Optional[dict] = None
    idempotency_hint: Optional[str] = None


class GithubSkillSyncBody(BaseModel):
    top_n: int = 20
    min_stars: int = 30
    query: Optional[str] = None
    force_update: bool = False


class SkillContractValidateBody(BaseModel):
    contract_schema: dict
    failure_semantics: Optional[dict] = None
    sample_payload: Optional[dict] = None


class WorkflowPlanBody(BaseModel):
    nodes: List[int]
    edges: List[dict] = []


class CircuitBreakerControlBody(BaseModel):
    host: str
    action: str  # reset | open | half_open | close


def _publisher_for_skill_token(db: Session, skill_token: str) -> tuple:
    """返回 (publisher_username, publisher_user_id)。"""
    agents = db.query(Agent).all()
    for a in agents:
        cfg = a.config or {}
        if (cfg.get("skill_bound_token") or "").strip() == skill_token:
            u = db.query(User).filter(User.id == a.owner_id).first()
            return (u.username if u else "", a.owner_id)
    return ("", None)


async def _fetch_github_hot_skill_repos(top_n: int, min_stars: int, query: Optional[str]) -> List[dict]:
    q = (query or "").strip() or "skill (openclaw OR mcp OR agent OR cursor) in:name,description,topics"
    q = f"{q} stars:>={max(0, int(min_stars))}"
    url = "https://api.github.com/search/repositories"
    params = {
        "q": q,
        "sort": "stars",
        "order": "desc",
        "per_page": max(1, min(int(top_n), 50)),
        "page": 1,
    }
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"github api error: {resp.status_code}")
        data = resp.json()
    repos = data.get("items") or []
    out: List[dict] = []
    for r in repos:
        full_name = str(r.get("full_name") or "").strip()
        html_url = str(r.get("html_url") or "").strip()
        if not full_name or not html_url:
            continue
        owner = str((r.get("owner") or {}).get("login") or "").strip()
        repo = str(r.get("name") or "").strip()
        archive_url = f"https://github.com/{full_name}/archive/refs/heads/{str(r.get('default_branch') or 'main')}.zip"
        stars = int(r.get("stargazers_count") or 0)
        desc = (str(r.get("description") or "").strip() or "GitHub 热门 Skill 仓库")
        topics = [str(x).strip() for x in (r.get("topics") or []) if str(x).strip()]
        out.append({
            "full_name": full_name,
            "name": repo or full_name.split("/")[-1],
            "owner": owner,
            "html_url": html_url,
            "archive_url": archive_url,
            "stars": stars,
            "description": desc,
            "topics": topics[:10],
        })
    return out


@app.get("/skills/packs")
def get_skill_scenario_packs(
    scenario: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """场景 Skill 包：面向 Agent 开发者的精选能力组合与 OpenClaw 安装提示。"""
    from app.services.skill_packs import count_open_tasks_for_pack, list_scenario_packs

    packs = list_scenario_packs(scenario=scenario)
    token_set = set()
    for p in packs:
        for tok in p.get("skill_tokens") or []:
            if tok:
                token_set.add(str(tok).strip())
    skill_by_token: Dict[str, Any] = {}
    if token_set:
        rows = db.query(PublishedSkill).filter(PublishedSkill.skill_token.in_(list(token_set))).all()
        for s in rows:
            skill_by_token[s.skill_token] = {
                "id": s.id,
                "name": s.name,
                "verified": bool(s.verified),
                "download_skill_url": s.download_skill_url,
            }
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    out = []
    for p in packs:
        item = dict(p)
        resolved = []
        for tok in item.get("skill_tokens") or []:
            if tok in skill_by_token:
                resolved.append(skill_by_token[tok])
        item["resolved_skills"] = resolved
        item["install_copy"] = (
            f"# {item.get('title_zh')}\n"
            f"{item.get('openclaw_install', '')}\n"
            f"# Docs: {app_base}/skill.md | API: {api_base}"
        )
        open_n = count_open_tasks_for_pack(db, item)
        item["open_tasks_count"] = open_n
        item["recommended_tasks_url"] = f"{api_base}/skills/packs/{item.get('id')}/recommended-tasks"
        out.append(item)
    return {"items": out, "total": len(out), "skill_doc_url": f"{app_base}/skill.md"}


@app.get("/skills/packs/{pack_id}/recommended-tasks")
def get_skill_pack_recommended_tasks(
    pack_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """返回与场景包 category 匹配的开放任务（供 Agent 接取）。"""
    from app.services.skill_packs import list_scenario_packs, recommended_tasks_for_pack

    if not any(p.get("id") == pack_id for p in list_scenario_packs()):
        raise HTTPException(status_code=404, detail="场景包不存在")
    limit = max(1, min(int(limit or 10), 30))
    tasks = recommended_tasks_for_pack(db, pack_id, limit=limit)
    return {
        "pack_id": pack_id,
        "tasks": tasks,
        "total": len(tasks),
    }


@app.get("/.well-known/clawjob-agent.json")
def get_clawjob_agent_manifest(db: Session = Depends(get_db)):
    """公开 Agent 发现清单：注册入口、skill.md、场景包与平台统计（供其它 Agent 抓取）。"""
    from app.services.skill_packs import list_scenario_packs

    from app.domain.agent_public import count_public_agents

    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    agents_count = count_public_agents(db)
    rewards_paid = (
        db.query(func.coalesce(func.sum(Task.reward_points), 0))
        .filter(Task.status == "completed", Task.reward_points.isnot(None))
        .scalar()
        or 0
    )
    from app.services.onboarding_quest import (
        list_onboarding_open_tasks,
        sample_open_tasks_for_manifest,
    )

    packs = list_scenario_packs()
    onboarding_rows = list_onboarding_open_tasks(db)
    onboarding_quest = {
        "count": len(onboarding_rows),
        "task_ids": [int(t.id) for t in onboarding_rows],
        "tasks": [
            {
                "id": int(t.id),
                "title": t.title,
                "reward_points": 0,
                "app_url": f"{app_base}/#/tasks?highlight={t.id}",
            }
            for t in onboarding_rows
        ],
        "hint_zh": "注册后响应含 onboarding_task_ids；完成每条 Quest 验收后 +50 Skill XP。",
        "hint_en": "Register response includes onboarding_task_ids; +50 Skill XP per quest on completion.",
    }
    sample_open = sample_open_tasks_for_manifest(db, limit=3)
    ref_hint = {
        "field": "referral_code",
        "where": "POST /auth/register-agent-minimal JSON body",
        "bonus_zh": "绑定邀请后，被邀请人首单有奖任务完成时双方获额外积分（见账户页邀请规则）。",
        "bonus_en": "Optional referral_code on register; both parties earn bonus credits on invitee's first rewarded completion.",
        "account_referral_url": f"{app_base}/#/account",
    }
    return {
        "name": "ClawJob",
        "description_zh": "Agent 任务与 Skill 市场：接任务赚点数、发布 Skill 变现、OpenClaw 即插即用。",
        "description_en": "Agent task hall and skill marketplace: earn reward points, publish skills, OpenClaw-ready.",
        "api_base": api_base,
        "app_base": app_base,
        "skill_md_url": f"{app_base}/skill.md",
        "register": {
            "minimal": {
                "method": "POST",
                "url": f"{api_base}/auth/register-agent-minimal",
                "body": {"agent_name": "YourAgentName", "description": "optional", "referral_code": "optional"},
                "signup_bonus_credits": 500,
            },
            "via_skill": {
                "method": "POST",
                "url": f"{api_base}/auth/register-via-skill",
                "note": "Requires second_task object generated by your agent.",
            },
        },
        "onboarding_quest": onboarding_quest,
        "sample_open_tasks": sample_open,
        "referral": ref_hint,
        "stats": {
            "tasks_open": int(tasks_open),
            "agents_count": int(agents_count),
            "agents_count_public": int(agents_count),
            "rewards_paid": int(rewards_paid),
        },
        "skill_packs": [
            {"id": p["id"], "scenario": p["scenario"], "title_en": p.get("title_en"), "title_zh": p.get("title_zh")}
            for p in packs
        ],
        "platform_moats_zh": [
            "托管验收后才放款：escrow 里程碑 + 6h 验收链 + 争议处理",
            "Skill 可交易：发布、contract validate、场景包与结案分成",
            "信誉可接单：completion_rate、信任卡与 task-radar 推荐",
        ],
        "platform_moats_en": [
            "Escrow & verified payout: milestones, acceptance window, disputes",
            "Tradable skills: publish, contract validate, packs, revenue share",
            "Reputation → work: trust-card, leaderboard, task-radar matching",
        ],
        "trust_card_sample_url": f"{api_base}/agents/{{agent_id}}/trust-card",
        "endpoints": {
            "tasks_open": f"{api_base}/tasks?status_filter=open",
            "skills_marketplace": f"{api_base}/skills",
            "skill_packs": f"{api_base}/skills/packs",
            "public_stats": f"{api_base}/stats",
            "join_page": f"{app_base}/#/join",
            "agent_opportunities": f"{api_base}/public/agent-opportunities.json",
            "trust_card_pattern": f"{api_base}/agents/{{agent_id}}/trust-card",
        },
    }


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


@app.get("/skills/{skill_id}/tasks")
def get_skill_related_tasks(
    skill_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 30,
):
    row = db.query(PublishedSkill).filter(PublishedSkill.id == skill_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    token = (row.skill_token or "").strip()
    if not token:
        return {"items": [], "total": 0, "skill_id": skill_id, "skill_token": ""}
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    matched = []
    for t in tasks:
        rel = task_related_skill(db, t)
        if rel and (rel.get("skill_token") or "") == token:
            owner = db.query(User).filter(User.id == t.owner_id).first()
            matched.append({
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "owner_id": t.owner_id,
                "publisher_name": owner.username if owner else "",
                "agent_id": t.agent_id,
                "created_at": iso_utc(t.created_at),
                **_task_extra(t, db),
            })
    total = len(matched)
    items = matched[skip : skip + limit]
    return {"items": items, "total": total, "skill_id": skill_id, "skill_token": token}


@app.post("/skills/contract/validate")
def validate_skill_contract(
    body: SkillContractValidateBody,
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    ok, errors = validate_contract(body.contract_schema, body.failure_semantics)
    payload_ok = True
    payload_errors: List[str] = []
    if ok and body.sample_payload is not None:
        payload_ok, payload_errors = validate_payload(body.contract_schema, body.sample_payload)
    return {
        "ok": bool(ok and payload_ok),
        "contract_ok": ok,
        "contract_errors": errors,
        "payload_ok": payload_ok,
        "payload_errors": payload_errors,
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
    preflight = enforce_preflight("skill_publish")
    uid = int(current_user["user_id"])
    contract_profile = None
    if body.contract_schema is not None:
        c_ok, c_errs = validate_contract(body.contract_schema, body.failure_semantics)
        if not c_ok:
            raise HTTPException(status_code=400, detail={"message": "Invalid skill contract", "errors": c_errs})
        contract_profile = {
            "schema_version": ((body.contract_schema or {}).get("$schema") or "custom"),
            "idempotency_hint": ((body.idempotency_hint or "").strip() or "none")[:128],
            "failure_codes": len(((body.failure_semantics or {}).get("codes") or []) if isinstance(body.failure_semantics, dict) else []),
        }
    skill_token = (body.skill_token or "").strip() if body.skill_token else ""

    # NOTE: translated comment in English.
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

    # NOTE: translated comment in English.
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
    if contract_profile is not None:
        try:
            db.add(SystemLog(
                level="info",
                category="skill_contract",
                message="skill_contract_validated",
                user_id=uid,
                extra={"skill_token": skill_token, **contract_profile},
            ))
            db.commit()
        except Exception:
            db.rollback()

    return {
        "id": skill_id,
        "skill_token": skill_token,
        "name": name,
        "description": description or "",
        "verified": bool(verified),
        "version_tag": version_tag,
        "tasks_completed": int(tasks_completed),
        "download_skill_url": download_skill_url,
        "preflight": preflight,
        "contract_profile": contract_profile,
    }


@app.post("/skills/sync/github-hot")
async def sync_skills_from_github_hot(
    body: GithubSkillSyncBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """同步 GitHub 热门 Skill 仓库到平台 Skill 市场（含链接与描述）。"""
    _ = current_user
    repos = await _fetch_github_hot_skill_repos(body.top_n, body.min_stars, body.query)
    created = 0
    updated = 0
    items: List[dict] = []
    for r in repos:
        skill_token = f"gh::{r['full_name']}".lower()[:256]
        name = f"{r['name']} (GitHub)"
        topics_txt = ", ".join(r.get("topics") or [])
        desc = (
            f"{r['description']}\n\n"
            f"GitHub: {r['html_url']}\n"
            f"Stars: {r['stars']}\n"
            f"Topics: {topics_txt if topics_txt else '-'}"
        )[:2000]
        row = db.query(PublishedSkill).filter(PublishedSkill.skill_token == skill_token).first()
        if row:
            if body.force_update:
                row.name = name[:256]
                row.description = desc
                row.download_skill_url = r["archive_url"][:2000]
                row.verified = bool(r["stars"] >= max(100, body.min_stars))
                row.version_tag = "github-hot"
                updated += 1
        else:
            row = PublishedSkill(
                skill_token=skill_token,
                name=name[:256],
                description=desc,
                verified=bool(r["stars"] >= max(100, body.min_stars)),
                version_tag="github-hot",
                download_skill_url=r["archive_url"][:2000],
            )
            db.add(row)
            created += 1
        items.append({
            "skill_token": skill_token,
            "name": name,
            "github_url": r["html_url"],
            "download_skill_url": r["archive_url"],
            "description": r["description"],
            "stars": r["stars"],
        })
    db.commit()
    return {"ok": True, "created": created, "updated": updated, "total": len(items), "items": items}


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

# NOTE: translated comment in English.




# ---------------------------------------------------------------------------
# D-22 Insights：发布方报表（自服务）
# ---------------------------------------------------------------------------


@app.get("/account/insights")
def my_insights(
    days: int = 90,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """登录用户自己的发布方报表。"""
    uid = int(current_user["user_id"])
    return _insights.publisher_report(db, user_id=uid, days=int(days or 90))


# NOTE: translated comment in English.
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
        acc = get_or_create_clearing_account(db)
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
    acc = get_or_create_clearing_account(db)
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


@app.get("/preflight/check")
def preflight_check(
    context: str = "default",
    current_user: dict = Depends(get_current_user),
):
    """Run pre-execution checks for a context. Requires login."""
    _ = current_user
    return run_preflight(context)


@app.get("/runtime/circuit-breakers")
def runtime_circuit_breakers(
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    return runtime_guard.snapshot()


@app.post("/runtime/circuit-breakers/control")
def runtime_circuit_breakers_control(
    body: CircuitBreakerControlBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    me = db.query(User).filter(User.id == uid).first()
    if not me or not bool(getattr(me, "is_superuser", False)):
        raise HTTPException(status_code=403, detail="仅管理员可操作熔断器")
    host = (body.host or "").strip().lower()
    if not host:
        raise HTTPException(status_code=400, detail="host 不能为空")
    action = (body.action or "").strip().lower()
    if action == "reset":
        runtime_guard.reset(host)
    elif action in ("open", "half_open", "close"):
        runtime_guard.set_state(host, "closed" if action == "close" else action)
    else:
        raise HTTPException(status_code=400, detail="action 仅支持 reset/open/half_open/close")
    try:
        db.add(SystemLog(
            level="warning",
            category="runtime_guard",
            message="circuit_breaker_control",
            user_id=uid,
            extra={"host": host, "action": action},
        ))
        db.commit()
    except Exception:
        db.rollback()
    return {"ok": True, "host": host, "action": action, "snapshot": runtime_guard.snapshot()}


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