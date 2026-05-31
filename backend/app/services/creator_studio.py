"""Creator Studio dashboard aggregation for agent owners."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task
from app.services.reputation import compute_agent_reputation


def _pct(values: List[Optional[float]]) -> Optional[float]:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 4)


def compute_creator_studio(db: Session, user_id: int, days: int = 30) -> Dict[str, Any]:
    days = max(7, min(int(days or 30), 90))
    agents = (
        db.query(Agent)
        .filter(Agent.owner_id == int(user_id), Agent.is_active.is_(True))  # noqa: E712
        .order_by(Agent.id.asc())
        .all()
    )
    agent_ids = [a.id for a in agents]

    agent_rows: List[Dict[str, Any]] = []
    total_completed = 0
    total_earned = 0
    top_score = 0
    recent_30d = 0
    first_pass_rates: List[Optional[float]] = []
    dispute_rates: List[Optional[float]] = []
    avg_hours_list: List[Optional[float]] = []

    for a in agents:
        rep = compute_agent_reputation(db, a.id) or {}
        stats = rep.get("stats") or {}
        completed = int(stats.get("completed_task_count", 0) or 0)
        earned = int(stats.get("reward_points_total", 0) or 0)
        score = int(rep.get("reputation_score", 0) or 0)
        r30 = int(stats.get("recent_30d_completed_count", 0) or 0)
        total_completed += completed
        total_earned += earned
        top_score = max(top_score, score)
        recent_30d += r30
        first_pass_rates.append(stats.get("first_pass_confirm_rate"))
        dispute_rates.append(stats.get("dispute_rate"))
        avg_hours_list.append(stats.get("avg_completion_hours"))
        agent_rows.append({
            "agent_id": a.id,
            "name": a.name,
            "reputation_score": score,
            "completed_task_count": completed,
            "reward_points_total": earned,
            "recent_30d_completed_count": r30,
            "first_pass_confirm_rate": stats.get("first_pass_confirm_rate"),
            "dispute_rate": stats.get("dispute_rate"),
            "avg_completion_hours": stats.get("avg_completion_hours"),
            "top_skills": stats.get("top_skills") or [],
        })

    pending_delivery = 0
    pending_verification = 0
    if agent_ids:
        pending_delivery = (
            db.query(Task)
            .filter(Task.agent_id.in_(agent_ids), Task.status == "in_progress")
            .count()
        )
        pending_verification = (
            db.query(Task)
            .filter(Task.agent_id.in_(agent_ids), Task.status == "pending_verification")
            .count()
        )

    since = datetime.utcnow() - timedelta(days=days)
    by_date: Dict[str, Dict[str, int]] = defaultdict(lambda: {"rewards": 0, "tasks": 0})
    if agent_ids:
        completed_tasks = (
            db.query(Task)
            .filter(
                Task.agent_id.in_(agent_ids),
                Task.status == "completed",
            )
            .all()
        )
        for t in completed_tasks:
            ts = getattr(t, "completed_at", None) or getattr(t, "updated_at", None)
            if not isinstance(ts, datetime) or ts < since:
                continue
            key = ts.strftime("%Y-%m-%d")
            by_date[key]["tasks"] += 1
            by_date[key]["rewards"] += int(getattr(t, "reward_points", 0) or 0)

    series: List[Dict[str, Any]] = []
    for i in range(days):
        d = (since + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        row = by_date.get(d, {"rewards": 0, "tasks": 0})
        series.append({"date": d, "rewards": row["rewards"], "tasks": row["tasks"]})

    suggestions: List[Dict[str, str]] = []
    if not agents:
        suggestions.append({"key": "register_agent", "href": "/agents"})
    else:
        if total_completed == 0:
            suggestions.append({"key": "first_task", "href": "/tasks"})
        if not any(a.get("top_skills") for a in agent_rows):
            suggestions.append({"key": "publish_skill", "href": "/agents"})
        if pending_delivery > 0:
            suggestions.append({"key": "deliver_pending", "href": "/tasks"})
        if top_score < 70 and total_completed >= 1:
            suggestions.append({"key": "improve_quality", "href": "/community"})
        if recent_30d == 0 and total_completed > 0:
            suggestions.append({"key": "stay_active", "href": "/tasks"})

    return {
        "summary": {
            "agents_count": len(agents),
            "completed_task_count": total_completed,
            "reward_points_total": total_earned,
            "top_reputation_score": top_score,
            "recent_30d_completed_count": recent_30d,
            "pending_delivery": int(pending_delivery),
            "pending_verification": int(pending_verification),
            "avg_first_pass_confirm_rate": _pct(first_pass_rates),
            "avg_dispute_rate": _pct(dispute_rates),
            "avg_completion_hours": _pct(avg_hours_list),
        },
        "agents": agent_rows,
        "income_series": series,
        "days": days,
        "cold_start_suggestions": suggestions,
    }
