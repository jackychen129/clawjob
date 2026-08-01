"""Pre-aggregated per-agent task metrics (10k+ agent scale)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.relational_db import AgentStats, Task


def _ensure_row(db: Session, agent_id: int) -> AgentStats:
    row = db.query(AgentStats).filter(AgentStats.agent_id == int(agent_id)).first()
    if row is None:
        row = AgentStats(agent_id=int(agent_id))
        db.add(row)
        db.flush()
    return row


def on_task_published(db: Session, task: Task) -> None:
    cid = getattr(task, "creator_agent_id", None)
    if cid:
        row = _ensure_row(db, int(cid))
        row.published_count = int(row.published_count or 0) + 1
        row.updated_at = datetime.utcnow()


def on_task_assigned(db: Session, agent_id: int) -> None:
    row = _ensure_row(db, int(agent_id))
    row.assigned_count = int(row.assigned_count or 0) + 1
    row.updated_at = datetime.utcnow()


def on_task_completed(db: Session, task: Task) -> None:
    aid = getattr(task, "agent_id", None)
    if not aid:
        return
    row = _ensure_row(db, int(aid))
    row.completed_count = int(row.completed_count or 0) + 1
    row.earned_points = int(row.earned_points or 0) + int(getattr(task, "reward_points", 0) or 0)
    row.updated_at = datetime.utcnow()


def get_stats_map(db: Session, agent_ids: list[int]) -> dict[int, AgentStats]:
    if not agent_ids:
        return {}
    rows = db.query(AgentStats).filter(AgentStats.agent_id.in_(agent_ids)).all()
    return {int(r.agent_id): r for r in rows}


def backfill_all_agent_stats(db: Session, *, batch_size: int = 500) -> int:
    """Recompute agent_stats from tasks table."""
    from sqlalchemy import func

    from app.database.relational_db import Agent

    db.query(AgentStats).delete()
    db.commit()
    offset = 0
    inserted = 0
    while True:
        ids = [r[0] for r in db.query(Agent.id).order_by(Agent.id).offset(offset).limit(batch_size).all()]
        if not ids:
            break
        for aid in ids:
            completed = (
                db.query(func.count(Task.id), func.coalesce(func.sum(Task.reward_points), 0))
                .filter(Task.agent_id == aid, Task.status == "completed")
                .first()
            )
            published = db.query(func.count(Task.id)).filter(Task.creator_agent_id == aid).scalar() or 0
            assigned = db.query(func.count(Task.id)).filter(Task.agent_id == aid).scalar() or 0
            cc = int(completed[0] or 0) if completed else 0
            ep = int(completed[1] or 0) if completed else 0
            if cc or published or assigned:
                db.add(
                    AgentStats(
                        agent_id=aid,
                        completed_count=cc,
                        earned_points=ep,
                        published_count=int(published),
                        assigned_count=int(assigned),
                    )
                )
                inserted += 1
        db.commit()
        offset += batch_size
        if len(ids) < batch_size:
            break
    return inserted
