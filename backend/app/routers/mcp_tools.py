"""MCP tool marketplace — persisted tool catalog (Step B)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.systems import tool_system
from app.database.relational_db import User, get_db
from app.security import get_current_user
from app.services import mcp_tools_store

router = APIRouter(tags=["MCP · 工具市场"])


class PublishMcpToolBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    category: str = Field(default="general", max_length=64)
    return_type: str = Field(default="object", max_length=64)
    parameters: Optional[Dict[str, Any]] = None
    tool_slug: Optional[str] = Field(default=None, max_length=128)
    requires_auth: bool = False
    rate_limit: int = Field(default=100, ge=1, le=10000)
    version_tag: str = Field(default="v1", max_length=64)


def _platform_tools() -> List[Dict[str, Any]]:
    """Built-in runtime tools (read-only, not persisted)."""
    out: List[Dict[str, Any]] = []
    try:
        for meta in tool_system.list_tools():
            dumped = meta.model_dump() if hasattr(meta, "model_dump") else dict(meta)
            out.append({
                "id": None,
                "tool_slug": dumped.get("name"),
                "name": dumped.get("name"),
                "description": dumped.get("description") or "",
                "category": dumped.get("category") or "general",
                "return_type": dumped.get("return_type") or "object",
                "parameters": dumped.get("parameters") or {},
                "requires_auth": bool(dumped.get("requires_auth")),
                "rate_limit": int(dumped.get("rate_limit") or 100),
                "verified": False,
                "version_tag": "v1",
                "pricing_model": "free",
                "price_per_unit": 0,
                "revenue_share_bp": 7000,
                "author_user_id": None,
                "publisher_username": "ClawJob",
                "source": "platform",
            })
    except Exception:
        pass
    return out


@router.get("/mcp-tools")
def list_mcp_tools(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    include_platform: bool = True,
):
    """Public MCP tool catalog: community-published + optional platform builtins."""
    limit = max(1, min(int(limit or 100), 200))
    skip = max(0, int(skip or 0))
    community = mcp_tools_store.list_market_tools(db, skip=0, limit=500, category=category)
    platform = _platform_tools() if include_platform else []
    community_slugs = {it.get("tool_slug") for it in community}
    merged = list(community) + [p for p in platform if p.get("tool_slug") not in community_slugs]
    total = len(merged)
    page = merged[skip : skip + limit]
    return {"items": page, "total": total, "skip": skip, "limit": limit}


@router.get("/mcp-tools/stats")
def mcp_tools_stats(db: Session = Depends(get_db)):
    total = mcp_tools_store.count_market_tools(db)
    return {"tool_count": total, "verified_count": 0}


@router.post("/mcp-tools/publish")
def publish_mcp_tool(
    body: PublishMcpToolBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    try:
        row = mcp_tools_store.publish_tool(
            db,
            uid,
            {
                "name": body.name,
                "description": body.description,
                "category": body.category,
                "return_type": body.return_type,
                "parameters": body.parameters,
                "tool_slug": body.tool_slug,
                "requires_auth": body.requires_auth,
                "rate_limit": body.rate_limit,
                "version_tag": body.version_tag,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    me = db.query(User).filter(User.id == uid).first()
    return {
        "ok": True,
        "status": "published",
        "item": mcp_tools_store.row_to_item(row, me.username if me else None),
    }


@router.delete("/mcp-tools/{tool_id}")
def delete_mcp_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    me = db.query(User).filter(User.id == uid).first()
    is_superuser = bool(me and getattr(me, "is_superuser", False))
    try:
        ok = mcp_tools_store.delete_tool(db, tool_id, uid, is_superuser=is_superuser)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="MCP tool not found")
    return {"ok": True, "id": tool_id}
