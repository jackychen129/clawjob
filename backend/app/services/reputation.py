"""Agent 信誉卡（Reputation Card）聚合服务。

对外暴露 `compute_agent_reputation(db, agent_id)`；指标基于 Task 聚合，
Redis 缓存 5 分钟，任务状态变更时失效。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task, User

_DISPUTE_KEY = "disputed"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _agent_skill_token(agent: Agent) -> Optional[str]:
    cfg = agent.config or {}
    if not isinstance(cfg, dict):
        return None
    tok = cfg.get("skill_bound_token")
    if not tok:
        return None
    return str(tok).strip() or None


def _collect_top_skills(tasks: List[Task], limit: int = 3) -> List[str]:
    bag: Counter[str] = Counter()
    for t in tasks:
        extra = t.input_data if isinstance(t.input_data, dict) else {}
        skills = extra.get("skills") if isinstance(extra, dict) else None
        if isinstance(skills, list):
            for s in skills:
                s_str = str(s).strip()
                if s_str:
                    bag[s_str] += 1
        cat = getattr(t, "category", None)
        if cat:
            bag[str(cat).strip()] += 1
    return [name for name, _ in bag.most_common(limit)]


def _reputation_score(
    *,
    completed: int,
    accepted: int,
    rejection_count: int,
    dispute_count: int,
    first_pass_confirm_rate: Optional[float],
    avg_completion_hours: Optional[float],
    recent_30d_completed: int,
) -> int:
    if accepted == 0:
        return 60
    score = 60.0
    if first_pass_confirm_rate is not None:
        score += first_pass_confirm_rate * 30.0
    active_bonus = min(10.0, (recent_30d_completed / 5.0) * 10.0)
    score += active_bonus
    denom = max(accepted, 1)
    dispute_rate = dispute_count / denom
    rejection_rate = rejection_count / denom
    score -= dispute_rate * 25.0
    score -= rejection_rate * 15.0
    if avg_completion_hours is not None:
        if avg_completion_hours < 24:
            score += 5.0
        elif avg_completion_hours < 72:
            score += 3.0
    return max(0, min(100, int(round(score))))


def compute_agent_reputation(db: Session, agent_id: int, *, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """计算 Agent 信誉卡。若 Agent 不存在返回 None。"""
    aid = int(agent_id)
    if use_cache:
        from app.services.reputation_cache import get_cached_reputation, set_cached_reputation

        cached = get_cached_reputation(aid)
        if cached is not None:
            return cached
    card = _compute_agent_reputation_uncached(db, aid)
    if card and use_cache:
        from app.services.reputation_cache import set_cached_reputation

        set_cached_reputation(aid, card)
    return card


def _compute_agent_reputation_uncached(db: Session, agent_id: int) -> Optional[Dict[str, Any]]:
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        return None

    owner: Optional[User] = db.query(User).filter(User.id == agent.owner_id).first()

    accepted_count = int(
        db.query(func.count(Task.id)).filter(Task.agent_id == agent.id).scalar() or 0
    )
    completed_count = int(
        db.query(func.count(Task.id))
        .filter(Task.agent_id == agent.id, Task.status == "completed")
        .scalar()
        or 0
    )
    reward_points_total = int(
        db.query(func.coalesce(func.sum(Task.reward_points), 0))
        .filter(Task.agent_id == agent.id, Task.status == "completed")
        .scalar()
        or 0
    )

    now = datetime.utcnow()
    d30 = now - timedelta(days=30)
    d90 = now - timedelta(days=90)
    recent_30 = int(
        db.query(func.count(Task.id))
        .filter(
            Task.agent_id == agent.id,
            Task.status == "completed",
            Task.completed_at.isnot(None),
            Task.completed_at >= d30,
        )
        .scalar()
        or 0
    )
    recent_90 = int(
        db.query(func.count(Task.id))
        .filter(
            Task.agent_id == agent.id,
            Task.status == "completed",
            Task.completed_at.isnot(None),
            Task.completed_at >= d90,
        )
        .scalar()
        or 0
    )

    rejection_count = 0
    dispute_count = 0
    completion_durations_hours: List[float] = []
    last_active_at: Optional[datetime] = None
    completed_tasks_for_skills: List[Task] = []

    task_rows = (
        db.query(
            Task.status,
            Task.input_data,
            Task.created_at,
            Task.completed_at,
            Task.updated_at,
            Task.category,
        )
        .filter(Task.agent_id == agent.id)
        .yield_per(200)
    )
    for status, input_data, created_at, completed_at, updated_at, category in task_rows:
        extra = input_data if isinstance(input_data, dict) else {}
        if isinstance(extra, dict):
            escrow = extra.get("escrow") if isinstance(extra.get("escrow"), dict) else None
            if escrow and escrow.get(_DISPUTE_KEY):
                dispute_count += 1
            timeline = extra.get("timeline") if isinstance(extra.get("timeline"), list) else []
            for ev in timeline:
                if not isinstance(ev, dict):
                    continue
                kind = str(ev.get("kind") or ev.get("event") or "").lower()
                if kind in {"rejected", "reject", "verification_rejected"}:
                    rejection_count += 1
        if status == "completed":
            if isinstance(created_at, datetime) and isinstance(completed_at, datetime):
                delta = completed_at - created_at
                if delta.total_seconds() > 0:
                    completion_durations_hours.append(delta.total_seconds() / 3600.0)
            ts = completed_at or updated_at or created_at
            if len(completed_tasks_for_skills) < 50:
                completed_tasks_for_skills.append(
                    Task(status=status, input_data=input_data, category=category, completed_at=completed_at)
                )
        else:
            ts = updated_at or created_at
        if isinstance(ts, datetime) and (last_active_at is None or ts > last_active_at):
            last_active_at = ts

    avg_completion_hours: Optional[float] = None
    if completion_durations_hours:
        avg_completion_hours = round(sum(completion_durations_hours) / len(completion_durations_hours), 2)

    denom = max(completed_count, 1)
    first_pass_rate: Optional[float] = None
    if completed_count > 0:
        first_pass_rate = round(max(0.0, (completed_count - rejection_count) / denom), 4)

    accepted_denom = max(accepted_count, 1)
    rejection_rate = round(rejection_count / accepted_denom, 4) if accepted_count else 0.0
    dispute_rate = round(dispute_count / accepted_denom, 4) if accepted_count else 0.0
    top_skills = _collect_top_skills(completed_tasks_for_skills)

    score = _reputation_score(
        completed=completed_count,
        accepted=accepted_count,
        rejection_count=rejection_count,
        dispute_count=dispute_count,
        first_pass_confirm_rate=first_pass_rate,
        avg_completion_hours=avg_completion_hours,
        recent_30d_completed=recent_30,
    )

    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description or "",
            "agent_type": agent.agent_type or "general",
            "category": getattr(agent, "category", None) or "api",
            "skill_token": _agent_skill_token(agent),
            "owner": {
                "id": owner.id if owner else None,
                "username": owner.username if owner else None,
                "joined_at": owner.created_at.isoformat() if owner and getattr(owner, "created_at", None) else None,
            },
            "is_active": bool(agent.is_active),
            "created_at": agent.created_at.isoformat() if getattr(agent, "created_at", None) else None,
        },
        "stats": {
            "accepted_task_count": accepted_count,
            "completed_task_count": completed_count,
            "rejection_count": rejection_count,
            "dispute_count": dispute_count,
            "rejection_rate": rejection_rate,
            "dispute_rate": dispute_rate,
            "first_pass_confirm_rate": first_pass_rate,
            "reward_points_total": reward_points_total,
            "avg_completion_hours": avg_completion_hours,
            "recent_30d_completed_count": recent_30,
            "recent_90d_completed_count": recent_90,
            "last_active_at": last_active_at.isoformat() if isinstance(last_active_at, datetime) else None,
            "top_skills": top_skills,
        },
        "reputation_score": score,
    }


def compute_bulk_reputations(db: Session, agent_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """为多个 Agent 计算信誉卡；优先读 Redis 缓存。"""
    out: Dict[int, Dict[str, Any]] = {}
    missing: List[int] = []
    from app.services.reputation_cache import get_cached_reputation, set_cached_reputation

    for aid in agent_ids:
        try:
            cached = get_cached_reputation(int(aid))
        except Exception:
            cached = None
        if cached is not None:
            out[int(aid)] = cached
        else:
            missing.append(int(aid))
    for aid in missing:
        try:
            card = _compute_agent_reputation_uncached(db, aid)
        except Exception:
            card = None
        if card is not None:
            out[aid] = card
            try:
                set_cached_reputation(aid, card)
            except Exception:
                pass
    return out
