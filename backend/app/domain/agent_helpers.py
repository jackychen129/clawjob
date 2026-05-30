"""Agent domain helpers."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, PublishedSkill, engine as db_engine

class CapabilityItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: Optional[str] = None

class CapabilityItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: Optional[str] = None


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
def ensure_agents_category_column() -> None:
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


def norm_capabilities(caps: Optional[List[Any]]) -> list:
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
def published_skill_ids_by_token(db: Session, agents: List[Agent]) -> dict:
    """skill_bound_token -> PublishedSkill.id，用于前端展示「Skill 已上架」。"""
    tokens = set()
    for a in agents:
        cfg = a.config or {}
        tok = (cfg.get("skill_bound_token") or "").strip()
        if tok:
            tokens.add(tok)
    if not tokens:
        return {}
    rows = db.query(PublishedSkill).filter(PublishedSkill.skill_token.in_(list(tokens))).all()
    return {r.skill_token: r.id for r in rows}
def get_my_agent(agent_id: int, db: Session, user_id: int) -> Optional[Agent]:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.owner_id != user_id:
        return None
    return agent
class SendMessageBody(BaseModel):
    content: str

