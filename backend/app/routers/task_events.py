"""
Task event SSE — reduce Agent polling (benchmark: AgentGigs Webhook/SSE).

GET /account/task-events/stream — authenticated SSE for tasks owned or assigned to user.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task
from app.security import get_current_user

router = APIRouter(prefix="/account", tags=["Account · 账户"])

_POLL_SECONDS = 5
_MAX_TASKS = 80


def _task_snapshot(task: Task) -> Dict[str, Any]:
    return {
        "task_id": task.id,
        "status": task.status,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "title": (task.title or "")[:120],
    }


def _fetch_user_tasks(db: Session, uid: int) -> List[Task]:
    agent_ids = [row[0] for row in db.query(Agent.id).filter(Agent.owner_id == uid).all()]
    filters = [Task.owner_id == uid]
    if agent_ids:
        filters.append(Task.agent_id.in_(agent_ids))
    since = datetime.utcnow() - timedelta(days=30)
    return (
        db.query(Task)
        .filter(or_(*filters))
        .filter(Task.updated_at >= since)
        .order_by(Task.updated_at.desc())
        .limit(_MAX_TASKS)
        .all()
    )


def _diff_snapshots(
    prev: Dict[int, Tuple[str, Optional[str]]],
    tasks: List[Task],
) -> Tuple[List[Dict[str, Any]], Dict[int, Tuple[str, Optional[str]]]]:
    events: List[Dict[str, Any]] = []
    nxt: Dict[int, Tuple[str, Optional[str]]] = {}
    for t in tasks:
        key = (t.status, t.updated_at.isoformat() if t.updated_at else None)
        nxt[t.id] = key
        if t.id not in prev or prev[t.id] != key:
            events.append(_task_snapshot(t))
    return events, nxt


@router.get("/task-events/stream")
async def stream_task_events(
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])

    async def event_generator():
        from app.database.relational_db import SessionLocal

        prev: Dict[int, Tuple[str, Optional[str]]] = {}
        yield "event: connected\ndata: {}\n\n"
        while True:
            db = SessionLocal()
            try:
                tasks = _fetch_user_tasks(db, uid)
                events, prev = _diff_snapshots(prev, tasks)
                for ev in events:
                    yield f"event: task_update\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            finally:
                db.close()
            yield ": heartbeat\n\n"
            await asyncio.sleep(_POLL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
