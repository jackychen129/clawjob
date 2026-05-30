"""Agent 信任卡（Trust Card）：面向 Agent 开发者与爬虫的公开竞争力摘要。"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Agent, PublishedSkill, Task, User
from app.services.escrow_tasks import get_escrow
from app.services.onboarding_quest import task_is_onboarding
from app.services.reputation import _agent_skill_token, compute_agent_reputation


def _count_escrow_completed(agent_id: int, tasks: List[Task]) -> int:
    n = 0
    for t in tasks:
        if t.status != "completed":
            continue
        if get_escrow(t):
            n += 1
    return n


def _onboarding_quest_complete(agent_id: int, tasks: List[Task]) -> bool:
    n = sum(1 for t in tasks if t.status == "completed" and task_is_onboarding(t))
    return n >= 3


def _verified_skills_for_agent(db: Session, agent: Agent) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    tok = _agent_skill_token(agent)
    if tok:
        row = (
            db.query(PublishedSkill)
            .filter(PublishedSkill.skill_token == tok, PublishedSkill.verified.is_(True))
            .first()
        )
        if row:
            seen.add(tok)
            out.append({
                "skill_token": row.skill_token,
                "name": row.name,
                "verified": True,
            })
    rows = (
        db.query(PublishedSkill)
        .filter(PublishedSkill.author_user_id == agent.owner_id, PublishedSkill.verified.is_(True))
        .order_by(PublishedSkill.created_at.desc())
        .limit(10)
        .all()
    )
    for row in rows:
        if row.skill_token in seen:
            continue
        seen.add(row.skill_token)
        out.append({
            "skill_token": row.skill_token,
            "name": row.name,
            "verified": True,
        })
    return out[:8]


def compute_agent_trust_card(db: Session, agent_id: int) -> Optional[Dict[str, Any]]:
    """聚合信任卡字段；Agent 不存在时返回 None。"""
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        return None

    rep = compute_agent_reputation(db, agent_id)
    if not rep:
        return None

    accepted = int(rep["stats"]["accepted_task_count"])
    completed = int(rep["stats"]["completed_task_count"])
    completion_rate: Optional[float] = None
    if accepted > 0:
        completion_rate = round(completed / accepted, 4)

    tasks: List[Task] = db.query(Task).filter(Task.agent_id == agent.id).all()
    escrow_done = _count_escrow_completed(agent.id, tasks)
    onboarding_done = _onboarding_quest_complete(agent.id, tasks)

    badges: List[str] = []
    if onboarding_done:
        badges.append("onboarding_quest_complete")
    if escrow_done > 0:
        badges.append("escrow_executor")
    if completed >= 5:
        badges.append("proven_executor")
    verified = _verified_skills_for_agent(db, agent)
    if verified:
        badges.append("verified_skill_author")

    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")

    score = int(rep.get("reputation_score", 60))
    one_liner_zh = (
        f"已完成 {completed} 单"
        + (f"，托管 {escrow_done} 单" if escrow_done else "")
        + f"，信誉 {score}"
    )
    one_liner_en = (
        f"{completed} tasks completed"
        + (f", {escrow_done} escrow" if escrow_done else "")
        + f", reputation {score}"
    )

    owner: Optional[User] = db.query(User).filter(User.id == agent.owner_id).first()
    member_since = (
        agent.created_at.isoformat()
        if getattr(agent, "created_at", None)
        else (owner.created_at.isoformat() if owner and getattr(owner, "created_at", None) else None)
    )

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "completion_rate": completion_rate,
        "escrow_tasks_completed": escrow_done,
        "total_earned": int(rep["stats"]["reward_points_total"]),
        "verified_skills": verified,
        "member_since": member_since,
        "badges": badges,
        "reputation_score": score,
        "stats": rep["stats"],
        "one_liner_zh": one_liner_zh,
        "one_liner_en": one_liner_en,
        "urls": {
            "trust_card": f"{api_base}/agents/{agent.id}/trust-card",
            "reputation": f"{api_base}/agents/{agent.id}/reputation",
            "profile": f"{app_base}/#/agents/{agent.id}",
            "cases": f"{api_base}/agents/{agent.id}/cases",
        },
    }
