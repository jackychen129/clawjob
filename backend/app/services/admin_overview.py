"""Admin dashboard overview builder with Redis snapshot cache."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, KycRecord, SystemLog, Task, User, WithdrawalRequest
from app.services.platform_stats_cache import (
    AGENTS_GROWTH_GOAL,
    STATS_CACHE_TTL_SEC,
    _cache_get,
    _cache_set,
    get_cached_public_agents_count,
)
from app.services import settlement as _settlement

_OVERVIEW_KEY = "clawjob:admin:overview_snapshot"


def _task_status_counts(db: Session) -> Dict[str, int]:
    rows = db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    return {str(status or ""): int(count) for status, count in rows}


def build_admin_overview(db: Session) -> Dict[str, Any]:
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)

    status_map = _task_status_counts(db)
    tasks_total = sum(status_map.values())
    tasks_open = status_map.get("open", 0)
    tasks_completed = status_map.get("completed", 0)
    tasks_pending_verification = status_map.get("pending_verification", 0)
    tasks_disputed = status_map.get("disputed", 0)

    users_total = db.query(User).count()
    users_new_today = db.query(User).filter(User.created_at >= today_start).count()
    agents_total = db.query(Agent).count()
    agents_new_today = db.query(Agent).filter(Agent.created_at >= today_start).count()
    agents_public = get_cached_public_agents_count(db)

    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0

    kyc_pending = db.query(KycRecord).filter(KycRecord.status == "pending").count()
    withdrawals_pending = db.query(WithdrawalRequest).filter(WithdrawalRequest.status == "pending").count()
    settlement_counts = _settlement.count_unpaid_settlements(db)

    requests_last_hour = db.query(SystemLog).filter(
        SystemLog.category == "request", SystemLog.created_at >= hour_ago,
    ).count()
    errors_last_hour = db.query(SystemLog).filter(
        SystemLog.level == "error", SystemLog.created_at >= hour_ago,
    ).count()

    growth_pct = (
        round(min(100.0, agents_public / AGENTS_GROWTH_GOAL * 100), 2)
        if AGENTS_GROWTH_GOAL > 0
        else 0.0
    )

    return {
        "generated_at": now.isoformat() + "Z",
        "tasks": {
            "total": tasks_total,
            "open": tasks_open,
            "completed": tasks_completed,
            "pending_verification": tasks_pending_verification,
            "disputed": tasks_disputed,
        },
        "users": {"total": users_total, "new_today": users_new_today},
        "agents": {
            "total": agents_total,
            "new_today": agents_new_today,
            "public": agents_public,
            "goal": AGENTS_GROWTH_GOAL,
            "growth_pct": growth_pct,
        },
        "rewards_paid": int(rewards_paid),
        "pending": {
            "kyc_reviews": kyc_pending,
            "withdrawals": withdrawals_pending,
            "disputed_tasks": tasks_disputed,
            "pending_verification_tasks": tasks_pending_verification,
            "settlements": settlement_counts,
        },
        "observability": {
            "requests_last_hour": int(requests_last_hour),
            "errors_last_hour": int(errors_last_hour),
        },
    }


def get_cached_admin_overview(db: Session) -> Dict[str, Any]:
    cached = _cache_get(_OVERVIEW_KEY)
    if isinstance(cached, dict):
        return cached
    snapshot = build_admin_overview(db)
    _cache_set(_OVERVIEW_KEY, snapshot, ttl=STATS_CACHE_TTL_SEC)
    return snapshot


def invalidate_admin_overview_cache() -> None:
    from app.services.platform_stats_cache import invalidate_cache_key

    invalidate_cache_key("clawjob:admin:overview_snapshot")
