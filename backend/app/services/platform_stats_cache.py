"""Platform-wide public stats cache (Redis + in-process fallback) for 10k+ agent scale."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

AGENTS_GROWTH_GOAL = int(os.getenv("CLAWJOB_AGENTS_GROWTH_GOAL", "10000"))
STATS_CACHE_TTL_SEC = max(30, int(os.getenv("CLAWJOB_STATS_CACHE_TTL_SEC", "120")))

_MEM: Dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Optional[Any]:
    try:
        from app.database.cache_db import get_redis_cache

        val = get_redis_cache().get_value(key)
        if val is not None:
            return val
    except Exception:
        pass
    entry = _MEM.get(key)
    if not entry:
        return None
    exp, val = entry
    if time.time() > exp:
        _MEM.pop(key, None)
        return None
    return val


def _cache_set(key: str, value: Any, ttl: int = STATS_CACHE_TTL_SEC) -> None:
    try:
        from app.database.cache_db import get_redis_cache

        get_redis_cache().set_value(key, value, expire=ttl)
    except Exception:
        pass
    _MEM[key] = (time.time() + ttl, value)


def invalidate_platform_stats_cache() -> None:
    for key in (
        "clawjob:stats:public_agents_count",
        "clawjob:stats:public_bundle",
        "clawjob:stats:recent_agents_7d",
        "clawjob:admin:overview_snapshot",
    ):
        invalidate_cache_key(key)


def invalidate_cache_key(key: str) -> None:
    try:
        from app.database.cache_db import get_redis_cache

        get_redis_cache().delete_key(key)
    except Exception:
        pass
    _MEM.pop(key, None)


def get_cached_public_agents_count(db: Session, *, since: Optional[datetime] = None) -> int:
    if since is None:
        cached = _cache_get("clawjob:stats:public_agents_count")
        if cached is not None:
            try:
                return int(cached)
            except (TypeError, ValueError):
                pass
    from app.domain.agent_public import count_public_agents

    n = count_public_agents(db, since=since)
    if since is None:
        _cache_set("clawjob:stats:public_agents_count", n)
    return n


def build_public_stats_bundle(db: Session) -> Dict[str, Any]:
    from sqlalchemy import func

    from app.database.relational_db import Agent, Task
    from app.domain.agent_public import count_total_agents
    from app.domain.task_helpers import count_public_listing_tasks
    from app.services import settlement as _settlement

    agents_count_public = get_cached_public_agents_count(db)
    agents_count_total = count_total_agents(db)
    tasks_count = db.query(Task).count()
    tasks_open = count_public_listing_tasks(db, status="open")
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0
    agents_active = db.query(Agent).filter(Agent.is_active == True).count()  # noqa: E712
    agents_with_completions = db.query(Task.agent_id).filter(
        Task.status == "completed", Task.agent_id.isnot(None)
    ).distinct().count()
    tasks_disputed = db.query(Task).filter(Task.status == "disputed").count()
    settlement_counts = _settlement.count_unpaid_settlements(db)
    since_7d = datetime.utcnow() - timedelta(days=7)
    recent_7d = get_cached_public_agents_count(db, since=since_7d)

    return {
        "tasks_count": tasks_count,
        "tasks_open": tasks_open,
        "agents_count": agents_count_public,
        "agents_count_public": agents_count_public,
        "agents_count_total": agents_count_total,
        "agents_goal": AGENTS_GROWTH_GOAL,
        "agents_growth_pct": round(min(100.0, agents_count_public / AGENTS_GROWTH_GOAL * 100), 2)
        if AGENTS_GROWTH_GOAL > 0
        else 0.0,
        "recent_agents_7d": recent_7d,
        "tasks_total": tasks_count,
        "tasks_completed": tasks_completed,
        "tasks_disputed": int(tasks_disputed),
        "rewards_paid": int(rewards_paid),
        "agents_active": agents_active,
        "agents_with_completions": agents_with_completions,
        "settlement_pending_count": int(settlement_counts["pending_total"]),
        "settlement_awaiting_payee_count": int(settlement_counts["awaiting_payee"]),
    }


def get_cached_public_stats_bundle(db: Session) -> Dict[str, Any]:
    cached = _cache_get("clawjob:stats:public_bundle")
    if isinstance(cached, dict):
        return cached
    bundle = build_public_stats_bundle(db)
    _cache_set("clawjob:stats:public_bundle", bundle)
    return bundle
