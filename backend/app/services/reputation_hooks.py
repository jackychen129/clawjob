"""Refresh / invalidate agent reputation after task lifecycle events."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Task
from app.services.reputation_cache import invalidate_agent_reputation


def touch_agent_reputation_for_task(db: Session, task: Task) -> None:
    """Drop cached reputation when task state affects an agent's stats."""
    ids = set()
    if getattr(task, "agent_id", None):
        ids.add(int(task.agent_id))
    if getattr(task, "creator_agent_id", None):
        ids.add(int(task.creator_agent_id))
    for aid in ids:
        invalidate_agent_reputation(aid)


def touch_agent_reputation(db: Session, agent_id: Optional[int]) -> None:
    invalidate_agent_reputation(agent_id)
