"""Preflight, circuit breakers, memory & tool systems (legacy agent runtime)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.systems import memory_system, runtime_guard, tool_system
from app.database.relational_db import User
from app.database.relational_db import SystemLog, User, get_db
from app.security import get_current_user, get_current_user_optional
from app.services.preflight import run_preflight

router = APIRouter(tags=["Legacy · Agent 运行时"])

_DEPRECATION = ' sunset="2026-12-31"; link="https://docs.clawjob.com.cn/api/legacy-runtime"'


def _legacy_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 31 Dec 2026 23:59:59 GMT"
    response.headers["Link"] = f'<https://docs.clawjob.com.cn/api/legacy-runtime>; rel="deprecation"'


class CircuitBreakerControlBody(BaseModel):
    host: str
    action: str  # reset | open | half_open | close


class CircuitBreakerConfigBody(BaseModel):
    threshold: Optional[int] = None
    open_seconds: Optional[int] = None


def _require_superuser(db: Session, current_user: dict) -> User:
    uid = int(current_user["user_id"])
    me = db.query(User).filter(User.id == uid).first()
    if not me or not bool(getattr(me, "is_superuser", False)):
        raise HTTPException(status_code=403, detail="仅管理员可配置熔断策略")
    return me


@router.get("/preflight/check")
def preflight_check(
    context: str = "default",
    current_user: dict = Depends(get_current_user),
):
    """Run pre-execution checks for a context. Requires login."""
    _ = current_user
    return run_preflight(context)


@router.get("/runtime/circuit-breakers")
def runtime_circuit_breakers(
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    return runtime_guard.snapshot()


@router.get("/runtime/circuit-breakers/config")
def runtime_circuit_breakers_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_superuser(db, current_user)
    cfg = runtime_guard.update_config()
    return {"ok": True, **cfg}


@router.patch("/runtime/circuit-breakers/config")
def patch_runtime_circuit_breakers_config(
    body: CircuitBreakerConfigBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    reviewer = _require_superuser(db, current_user)
    if body.threshold is None and body.open_seconds is None:
        raise HTTPException(status_code=400, detail="至少提供 threshold 或 open_seconds")
    cfg = runtime_guard.update_config(threshold=body.threshold, open_seconds=body.open_seconds)
    try:
        db.add(SystemLog(
            level="info",
            category="runtime_guard",
            message="circuit_breaker_config",
            user_id=reviewer.id,
            extra=cfg,
        ))
        db.commit()
    except Exception:
        db.rollback()
    return {"ok": True, **cfg, "snapshot": runtime_guard.snapshot()}


@router.post("/runtime/circuit-breakers/control")
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
@router.post("/memory")
async def store_memory(memory_data: dict, current_user: str = Depends(get_current_user)):
    """Store memory in vector database"""
    return await memory_system.store_memory(memory_data, current_user)

@router.get("/memory/search")
async def search_memory(query: str, current_user: str = Depends(get_current_user)):
    """Search memory using semantic search"""
    return await memory_system.search_memory(query, current_user)

@router.get("/memory/{memory_id}")
async def get_memory(memory_id: str, current_user: str = Depends(get_current_user)):
    """Retrieve specific memory"""
    return await memory_system.get_memory(memory_id, current_user)

# Tool System Endpoints
@router.get("/tools")
async def list_tools(current_user: Optional[dict] = Depends(get_current_user_optional)):
    """List available tools for agents (public catalog; auth optional)."""
    return tool_system.list_tools(current_user)

@router.post("/tools")
async def create_tool(tool_config: dict, current_user: str = Depends(get_current_user)):
    """Create a new tool for agents to use"""
    return await tool_system.create_tool(tool_config, current_user)

@router.post("/agents/{agent_id}/use-tool")
async def use_tool(agent_id: str, tool_request: dict, current_user: str = Depends(get_current_user)):
    """Allow agent to use a specific tool"""
    return await tool_system.use_tool(agent_id, tool_request, current_user)
