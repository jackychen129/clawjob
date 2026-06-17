"""Public stats, health, activity, leaderboard."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.systems import cache_db, relational_db, vector_db
from app.database.relational_db import Agent, Task, User, get_db
from app.domain.task_helpers import owner_display_name as _owner_display_name, task_is_public_listing, count_public_listing_tasks
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["Public · 统计与动态"])

_CLAWJOB_ENTERPRISE = os.getenv("CLAWJOB_ENTERPRISE", "0").strip() not in ("0", "false", "no", "")


def _safe_int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except (TypeError, ValueError):
        return default


def _activity_agent_is_internal(agent: Agent, owner: Optional[User]) -> bool:
    from app.domain.agent_public import agent_is_public
    return not agent_is_public(agent, owner)


@router.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "clawjob-backend",
        "databases": {
            "vector_db": await vector_db.health_check(),
            "relational_db": await relational_db.health_check(),
            "cache_db": await cache_db.health_check()
        },
        "agent_systems": {
            "agent_manager": "active",
            "task_system": "active", 
            "memory_system": "active",
            "tool_system": "active"
        },
        "features": {
            "enterprise_enabled": _CLAWJOB_ENTERPRISE,
            "payout_enabled": True,
            "community_enabled": os.getenv("CLAWJOB_COMMUNITY_ENABLED", "1").strip() != "0",
            "community_hot_dispatch_enabled": os.getenv("CLAWJOB_COMMUNITY_HOT_DISPATCH_ENABLED", "1").strip() != "0",
            "community_background_jobs": os.getenv("CLAWJOB_COMMUNITY_BACKGROUND_JOBS", "1").strip() != "0",
            "community_dispatch_interval_sec": max(60, _safe_int_env("CLAWJOB_COMMUNITY_DISPATCH_INTERVAL_SEC", 900)),
        },
    }


@router.get("/stats")
def get_public_stats(db: Session = Depends(get_db)):
    """公开统计：任务总数、开放数、已完成数、活跃 Agent、累计发放报酬（供首页/官网 Counters 与 Dashboard）。"""
    from app.domain.agent_public import count_public_agents, count_total_agents

    tasks_count = db.query(Task).count()
    tasks_open = count_public_listing_tasks(db, status="open")
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0
    agents_count_public = count_public_agents(db)
    agents_count_total = count_total_agents(db)
    agents_active = db.query(Agent).filter(Agent.is_active == True).count()
    agents_with_completions = db.query(Task.agent_id).filter(
        Task.status == "completed", Task.agent_id.isnot(None)
    ).distinct().count()
    tasks_disputed = db.query(Task).filter(Task.status == "disputed").count()
    from app.services import settlement as _settlement

    settlement_counts = _settlement.count_unpaid_settlements(db)
    return {
        "tasks_count": tasks_count,
        "tasks_open": tasks_open,
        "agents_count": agents_count_public,
        "agents_count_public": agents_count_public,
        "agents_count_total": agents_count_total,
        "tasks_total": tasks_count,
        "tasks_completed": tasks_completed,
        "tasks_disputed": int(tasks_disputed),
        "rewards_paid": int(rewards_paid),
        "agents_active": agents_active,
        "agents_with_completions": agents_with_completions,
        "settlement_pending_count": int(settlement_counts["pending_total"]),
        "settlement_awaiting_payee_count": int(settlement_counts["awaiting_payee"]),
    }


@router.get("/stats/recent-agents")
def get_recent_agents_count(db: Session = Depends(get_db)):
    """近 7 天新注册 Agent 数量（无 PII，供 Dashboard 社交证明）。"""
    from app.domain.agent_public import count_public_agents, count_total_agents

    since = datetime.utcnow() - timedelta(days=7)
    return {
        "recent_agents_7d": int(count_public_agents(db, since=since)),
        "recent_agents_7d_total": int(count_total_agents(db, since=since)),
        "period_days": 7,
    }
@router.get("/activity")
def get_activity(limit: int = 50, db: Session = Depends(get_db)):
    """实时动态流：最近任务发布、任务完成、Agent 注册。用于 Dashboard Live Feed。

    过滤掉 hidden_from_public/register_via_skill 握手任务、clawjob_system 拥有的任务，
    以及内部部署探活 Agent（DeployProbe_* 等）——保证首页看到的都是真实业务动态。
    """
    events = []
    # NOTE: pull 3x limit per stream so that after filtering we still have enough results.
    fetch_n = max(limit * 3, limit + 20)
    completed = (
        db.query(Task, Agent, User)
        .outerjoin(Agent, Task.agent_id == Agent.id)
        .join(User, Task.owner_id == User.id)
        .filter(Task.status == "completed")
        .order_by(Task.completed_at.desc().nullslast(), Task.updated_at.desc())
        .limit(fetch_n)
    ).all()
    for t, a, owner in completed:
        if not task_is_public_listing(t, owner):
            continue
        at = (t.completed_at or t.updated_at or t.created_at) or datetime.utcnow()
        events.append({
            "type": "task_completed",
            "at": iso_utc(at) or str(at),
            "task_id": t.id,
            "task_title": (t.title or "")[:80],
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "agent_name": a.name if a else None,
            "publisher_name": owner.username if owner else None,
        })
    created = (
        db.query(Task, User)
        .join(User, Task.owner_id == User.id)
        .filter(Task.status == "open")
        .order_by(Task.created_at.desc())
        .limit(fetch_n)
    ).all()
    for t, owner in created:
        if not task_is_public_listing(t, owner):
            continue
        events.append({
            "type": "task_created",
            "at": iso_utc(t.created_at or datetime.utcnow()),
            "task_id": t.id,
            "task_title": (t.title or "")[:80],
            "publisher_name": owner.username if owner else None,
        })
    agents = (
        db.query(Agent, User)
        .join(User, Agent.owner_id == User.id)
        .order_by(Agent.created_at.desc())
        .limit(fetch_n)
    ).all()
    for a, owner in agents:
        if _activity_agent_is_internal(a, owner):
            continue
        events.append({
            "type": "agent_registered",
            "at": iso_utc(a.created_at or datetime.utcnow()),
            "agent_id": a.id,
            "agent_name": a.name,
            "owner_name": owner.username if owner else None,
        })
    events.sort(key=lambda e: e["at"], reverse=True)
    return {"events": events[:limit]}


@router.get("/leaderboard")
def get_leaderboard(skip: int = 0, limit: int = 50, shadow: int = 0, db: Session = Depends(get_db)):
    """Agent 声誉排行榜：Earned、完成任务数、成功率。shadow=1 时仅返回新星（任务数少但成功率高的 Agent）。"""
    # NOTE: translated comment in English.
    from sqlalchemy import case
    completed_subq = (
        db.query(
            Task.agent_id,
            func.count(Task.id).label("completed_count"),
            func.coalesce(func.sum(Task.reward_points), 0).label("earned"),
        )
        .filter(Task.status == "completed", Task.agent_id.isnot(None))
        .group_by(Task.agent_id)
    ).subquery()
    total_subq = (
        db.query(Task.agent_id, func.count(Task.id).label("total_count"))
        .filter(Task.agent_id.isnot(None))
        .group_by(Task.agent_id)
    ).subquery()
    from app.domain.agent_public import apply_public_agent_filters, filter_public_agent_rows

    q = (
        db.query(
            Agent,
            User,
            func.coalesce(completed_subq.c.completed_count, 0).label("completed_count"),
            func.coalesce(completed_subq.c.earned, 0).label("earned"),
            func.coalesce(total_subq.c.total_count, 0).label("total_count"),
        )
        .join(User, Agent.owner_id == User.id)
        .outerjoin(completed_subq, Agent.id == completed_subq.c.agent_id)
        .outerjoin(total_subq, Agent.id == total_subq.c.agent_id)
    )
    q = apply_public_agent_filters(q)
    is_shadow = bool(int(shadow or 0))
    # 影子榜（新星）需要更大候选集，便于在内存中按成功率筛选 / 排序
    fetch_n = 500 if is_shadow else max(limit * 3, limit + 20)
    rows = (
        q.order_by(completed_subq.c.earned.desc().nullslast(), Agent.id.desc())
        .offset(0 if is_shadow else skip)
        .limit(fetch_n)
        .all()
    )
    rows = filter_public_agent_rows(rows)
    entries = []
    for (a, owner, completed_count, earned, total_count) in rows:
        total_count = total_count or 0
        completed_count = completed_count or 0
        success_rate = (completed_count / total_count * 100) if total_count else 0
        entries.append({
            "agent_id": a.id,
            "agent_name": a.name,
            "owner_name": _owner_display_name(owner.username if owner else None),
            "earned": int(earned),
            "tasks_completed": int(completed_count),
            "tasks_total": int(total_count),
            "success_rate": round(success_rate, 1),
            "certified": False,  # 预留：Playbook 验证后为 True
        })
    if is_shadow:
        # 新星：完成 ≥1 单、总任务数较少（≤5）、成功率 ≥50%，按成功率→收益排序
        entries = [
            e for e in entries
            if e["tasks_completed"] >= 1 and e["tasks_total"] <= 5 and e["success_rate"] >= 50.0
        ]
        entries.sort(key=lambda e: (e["success_rate"], e["earned"]), reverse=True)
        entries = entries[skip: skip + limit]
    else:
        entries = entries[:limit]
    out = []
    for i, e in enumerate(entries):
        e["rank"] = skip + i + 1
        out.append(e)
    return {"items": out, "total": len(out)}
@router.get("/stats/roi-series")
def get_roi_series(days: int = 14, db: Session = Depends(get_db)):
    # NOTE: translated comment in English.
    d = max(7, min(90, int(days or 14)))
    start = datetime.utcnow() - timedelta(days=d - 1)
    tasks = db.query(Task).filter(Task.status == "completed", Task.completed_at.isnot(None), Task.completed_at >= start).all()
    bucket = {}
    for t in tasks:
        key = (t.completed_at or datetime.utcnow()).strftime("%Y-%m-%d")
        obj = bucket.get(key) or {"date": key, "rewards": 0, "tasks": 0}
        obj["rewards"] += int(getattr(t, "reward_points", 0) or 0)
        obj["tasks"] += 1
        bucket[key] = obj
    out = []
    for i in range(d):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        out.append(bucket.get(day) or {"date": day, "rewards": 0, "tasks": 0})
    return {"series": out, "days": d}
