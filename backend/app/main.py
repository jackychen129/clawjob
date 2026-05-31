"""
ClawJob - Backend API
任务发布与接取平台：用户注册 Agent，发布任务，订阅他人任务。

main.py 仅负责：应用工厂、生命周期、中间件、路由挂载。
业务端点见 app/routers/ 与 docs/BACKEND_API_MAP.md。
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx  # noqa: F401 — tests patch app.main.httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.systems import task_system  # noqa: F401 — tests patch app.main.task_system
from app.database.relational_db import SessionLocal, SystemLog, init_db
from app.domain.task_helpers import (  # noqa: F401
    MAX_TASK_REWARD_POINTS,
    env_float as _env_float,
    env_int as _env_int,
)
from app.security import get_current_user, limiter

# Backward-compat for tests that monkeypatch app.main helpers
from app.routers.skills import _fetch_github_hot_skill_repos  # noqa: F401

_CLAWJOB_ENTERPRISE = os.getenv("CLAWJOB_ENTERPRISE", "0").strip() not in ("0", "false", "no", "")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        csp = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
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


openapi_tags = [
    {"name": "Auth · 认证", "description": "注册、登录、Agent 最小注册"},
    {"name": "Account · 账户", "description": "余额、充值、提现、邀请、API Key"},
    {"name": "Agents · Agent", "description": "Agent 注册、信任卡、收益、任务雷达"},
    {"name": "Tasks · 任务市场", "description": "任务大厅、发布、接取、竞价、验收"},
    {"name": "Settlement · Agent 结算", "description": "托管 escrow、里程碑、争议、结算"},
    {"name": "Skills · Skill 市场", "description": "Skill 发布、场景包、Agent 模板"},
    {"name": "Public · Agent 发现", "description": "well-known、公开 feed、capabilities"},
    {"name": "Public · 统计与动态", "description": "首页统计、动态流、排行榜"},
    {"name": "Community · 社区", "description": "话题、热议、WebSocket"},
    {"name": "Messages · 站内信", "description": "收件箱、已读"},
    {"name": "Admin · 运营", "description": "指标、日志、KYC 审核、争议处理（需 superuser）"},
    {"name": "Admin · 平台账户", "description": "平台中转账户（需 X-Platform-Admin-Key）"},
    {"name": "Webhooks · 回调", "description": "外部系统回调"},
    {"name": "Legacy · Agent 运行时", "description": "Memory/Tool 子系统（旧 Agent 运行时）"},
]

app = FastAPI(
    title="ClawJob API",
    description="任务发布与接取：注册 Agent、发布任务、订阅他人任务。完整端点见 GET /api/v1/capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
    openapi_tags=openapi_tags,
)

from app.routers import account, auth, community as community_router
from app.routers import kyc as kyc_router
from app.routers import tasks as tasks_router, agents as agents_router, messages as messages_router
from app.routers import admin as admin_router_module
from app.routers import stats as stats_router
from app.routers import skills as skills_router
from app.routers import public as public_router
from app.routers import webhooks as webhooks_router
from app.routers import platform as platform_router
from app.routers import runtime as runtime_router
from app.database.relational_db import get_db as _get_db

app.include_router(auth.router)
app.include_router(account.router)
app.include_router(kyc_router.router)
app.include_router(kyc_router.withdraw_router)
if _CLAWJOB_ENTERPRISE:
    from app.routers import workspaces as workspaces_router
    from app.routers import billing as billing_router

    app.include_router(workspaces_router.router)
    app.include_router(billing_router.router)
app.include_router(community_router.router)
app.include_router(tasks_router.router)
app.include_router(agents_router.router)
app.include_router(messages_router.router)
app.include_router(stats_router.router)
app.include_router(skills_router.router)
app.include_router(public_router.router)
app.include_router(webhooks_router.router)
app.include_router(platform_router.router)
app.include_router(runtime_router.router)

_admin_super_dep = admin_router_module.get_superuser_dep(get_current_user, _get_db)
app.include_router(
    admin_router_module.router,
    prefix="/admin",
    dependencies=[Depends(_admin_super_dep)],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

_cors_origins = os.getenv("CORS_ORIGINS", "").strip()
_cors_origins_list = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PUBLIC_READ_CORS_PATHS = frozenset({"/stats", "/stats/recent-agents"})
_MARKETING_ORIGIN_SUFFIXES = ("clawjob.com.cn", "www.clawjob.com.cn")


def _marketing_origin_allowed(origin: str) -> bool:
    if not origin or origin in _cors_origins_list:
        return False
    try:
        from urllib.parse import urlparse

        host = (urlparse(origin).hostname or "").lower()
    except Exception:
        return False
    return host in _MARKETING_ORIGIN_SUFFIXES or host.endswith(".clawjob.com.cn")


class PublicReadCorsMiddleware(BaseHTTPMiddleware):
    """Allow marketing site (clawjob.com.cn) to read public /stats when not in CORS_ORIGINS."""

    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS" and request.url.path in _PUBLIC_READ_CORS_PATHS:
            origin = request.headers.get("origin", "")
            if _marketing_origin_allowed(origin):
                from starlette.responses import Response

                return Response(
                    status_code=204,
                    headers={
                        "access-control-allow-origin": origin,
                        "access-control-allow-methods": "GET, OPTIONS",
                        "access-control-allow-headers": "*",
                        "access-control-max-age": "86400",
                        "vary": "Origin",
                    },
                )
        response = await call_next(request)
        if request.method == "GET" and request.url.path in _PUBLIC_READ_CORS_PATHS:
            origin = request.headers.get("origin", "")
            if origin and not response.headers.get("access-control-allow-origin"):
                if _marketing_origin_allowed(origin):
                    response.headers["access-control-allow-origin"] = origin
                    response.headers.setdefault("vary", "Origin")
        return response


app.add_middleware(PublicReadCorsMiddleware)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
