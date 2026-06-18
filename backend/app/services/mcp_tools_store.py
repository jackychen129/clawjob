"""Persistence layer for MCP tool marketplace."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import PublishedMcpTool, User


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", (name or "").strip().lower()).strip("-")
    return (slug or "tool")[:128]


def _unique_slug(db: Session, base: str, author_user_id: int) -> str:
    candidate = base[:128]
    if not db.query(PublishedMcpTool).filter(PublishedMcpTool.tool_slug == candidate).first():
        return candidate
    suffix = f"u{author_user_id}-{base}"[:128]
    if not db.query(PublishedMcpTool).filter(PublishedMcpTool.tool_slug == suffix).first():
        return suffix
    n = 2
    while n < 1000:
        alt = f"{suffix}-{n}"[:128]
        if not db.query(PublishedMcpTool).filter(PublishedMcpTool.tool_slug == alt).first():
            return alt
        n += 1
    raise ValueError("Could not allocate unique tool slug")


def row_to_item(row: PublishedMcpTool, publisher_username: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": row.id,
        "tool_slug": row.tool_slug,
        "name": row.name,
        "description": row.description or "",
        "category": row.category or "general",
        "parameters": row.parameters if isinstance(row.parameters, dict) else (row.parameters or {}),
        "return_type": row.return_type or "object",
        "requires_auth": bool(row.requires_auth),
        "rate_limit": int(row.rate_limit or 100),
        "verified": bool(row.verified),
        "version_tag": row.version_tag or "v1",
        "pricing_model": row.pricing_model or "free",
        "price_per_unit": int(row.price_per_unit or 0),
        "revenue_share_bp": int(row.revenue_share_bp or 7000),
        "author_user_id": row.author_user_id,
        "publisher_username": publisher_username,
        "source": "market",
    }


def list_market_tools(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q = db.query(PublishedMcpTool).order_by(PublishedMcpTool.created_at.desc())
    if category:
        q = q.filter(PublishedMcpTool.category == category)
    rows = q.offset(skip).limit(limit).all()
    out: List[Dict[str, Any]] = []
    for row in rows:
        pub_name = None
        if row.author_user_id:
            u = db.query(User).filter(User.id == row.author_user_id).first()
            pub_name = u.username if u else None
        out.append(row_to_item(row, pub_name))
    return out


def count_market_tools(db: Session) -> int:
    return db.query(PublishedMcpTool).count()


def publish_tool(db: Session, author_user_id: int, config: dict) -> PublishedMcpTool:
    name = (config.get("name") or "").strip()
    if not name:
        raise ValueError("Tool name is required")
    description = (config.get("description") or "").strip() or None
    category = (config.get("category") or "general").strip()[:64] or "general"
    return_type = (config.get("return_type") or "object").strip()[:64] or "object"
    parameters = config.get("parameters") if isinstance(config.get("parameters"), dict) else {}
    requires_auth = bool(config.get("requires_auth", False))
    rate_limit = int(config.get("rate_limit") or 100)
    version_tag = ((config.get("version_tag") or "v1").strip() or "v1")[:64]
    explicit_slug = (config.get("tool_slug") or "").strip()

    existing_by_name = (
        db.query(PublishedMcpTool)
        .filter(PublishedMcpTool.author_user_id == author_user_id, PublishedMcpTool.name == name)
        .first()
    )
    if existing_by_name:
        existing_by_name.description = description
        existing_by_name.category = category
        existing_by_name.parameters = parameters
        existing_by_name.return_type = return_type
        existing_by_name.requires_auth = requires_auth
        existing_by_name.rate_limit = rate_limit
        existing_by_name.version_tag = version_tag
        db.commit()
        db.refresh(existing_by_name)
        return existing_by_name

    base_slug = _slugify(explicit_slug or name)
    tool_slug = _unique_slug(db, base_slug, author_user_id)

    row = PublishedMcpTool(
        tool_slug=tool_slug,
        name=name,
        description=description,
        category=category,
        parameters=parameters,
        return_type=return_type,
        requires_auth=requires_auth,
        rate_limit=rate_limit,
        author_user_id=author_user_id,
        verified=False,
        version_tag=version_tag,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_tool(db: Session, tool_id: int, user_id: int, *, is_superuser: bool = False) -> bool:
    row = db.query(PublishedMcpTool).filter(PublishedMcpTool.id == tool_id).first()
    if not row:
        return False
    if not is_superuser and row.author_user_id != user_id:
        raise PermissionError("Not allowed to delete this tool")
    db.delete(row)
    db.commit()
    return True
