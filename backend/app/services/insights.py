"""
Insights report aggregations.

Two main surfaces:

* ``publisher_report(user_id)`` — per-user spending / ROI breakdown.
* ``platform_report()`` — admin-only GMV, matching funnel, retention matrix.

All methods avoid expensive N+1 joins by using a handful of ``GROUP BY``
queries and small in-memory reductions — the dataset is expected to stay
modest at this stage of the product.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.database.relational_db import (
    CreditTransaction,
    Task,
    TaskBid,
    User,
)


# -------------------------------------------------------------------
# Publisher report
# -------------------------------------------------------------------


def publisher_report(db: Session, user_id: int, *, days: int = 90) -> Dict[str, Any]:
    days = max(1, min(365, int(days or 90)))
    since = datetime.utcnow() - timedelta(days=days)

    total_spent = (
        db.query(func.coalesce(func.sum(CreditTransaction.amount), 0))
        .filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.amount < 0,
            CreditTransaction.created_at >= since,
        )
        .scalar()
        or 0
    )
    refund_received = (
        db.query(func.coalesce(func.sum(CreditTransaction.amount), 0))
        .filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.amount > 0,
            CreditTransaction.type.in_(
                [
                    "task_cancel_refund",
                    "auction_refund",
                    "escrow_refund",
                ]
            ),
            CreditTransaction.created_at >= since,
        )
        .scalar()
        or 0
    )
    # Task-level aggregation
    my_tasks = (
        db.query(Task)
        .filter(Task.owner_id == user_id, Task.created_at >= since)
        .all()
    )
    total = len(my_tasks)
    completed = sum(1 for t in my_tasks if (t.status or "") == "completed")
    cancelled = sum(1 for t in my_tasks if (t.status or "").startswith("cancel"))
    open_ = sum(1 for t in my_tasks if (t.status or "") in ("open", "pending"))
    in_progress = sum(1 for t in my_tasks if (t.status or "") in ("in_progress", "pending_verification"))

    # Failure / rejection hotspots
    rejection_reasons: Dict[str, int] = {}
    for t in my_tasks:
        ih = (t.input_data or {}).get("rejection_history") if isinstance(t.input_data, dict) else None
        if isinstance(ih, list):
            for row in ih:
                reason = (row or {}).get("reason") if isinstance(row, dict) else None
                if isinstance(reason, str):
                    short = reason[:60].strip()
                    if short:
                        rejection_reasons[short] = rejection_reasons.get(short, 0) + 1

    top_reasons = sorted(rejection_reasons.items(), key=lambda kv: kv[1], reverse=True)[:5]

    # Category distribution of spending
    spending_by_category: Dict[str, int] = {}
    for t in my_tasks:
        cat = (t.category or "uncategorized").strip() or "uncategorized"
        spending_by_category[cat] = spending_by_category.get(cat, 0) + int(t.reward_points or 0)

    return {
        "window_days": days,
        "since": since.isoformat() + "Z",
        "spent_points": int(abs(total_spent)),
        "refund_points": int(refund_received),
        "net_spent_points": int(abs(total_spent) - int(refund_received)),
        "tasks": {
            "total": total,
            "completed": completed,
            "cancelled": cancelled,
            "open": open_,
            "in_progress": in_progress,
            "completion_rate": round(completed / total, 4) if total else 0.0,
        },
        "spending_by_category": spending_by_category,
        "top_rejection_reasons": [{"reason": r, "count": c} for r, c in top_reasons],
    }


# -------------------------------------------------------------------
# Platform report
# -------------------------------------------------------------------


def platform_report(db: Session, *, days: int = 30) -> Dict[str, Any]:
    days = max(1, min(365, int(days or 30)))
    since = datetime.utcnow() - timedelta(days=days)

    # GMV = sum of reward_points of tasks published in the window
    gmv = (
        db.query(func.coalesce(func.sum(Task.reward_points), 0))
        .filter(Task.created_at >= since)
        .scalar()
        or 0
    )
    # Revenue = platform commission (kind='commission')
    revenue = (
        db.query(func.coalesce(func.sum(CreditTransaction.amount), 0))
        .filter(
            CreditTransaction.created_at >= since,
            CreditTransaction.type.in_(["commission", "platform_commission"]),
        )
        .scalar()
        or 0
    )

    # Funnel: published -> had_bid -> assigned -> completed
    tasks_in_window = (
        db.query(Task.id, Task.status, Task.agent_id, Task.input_data)
        .filter(Task.created_at >= since)
        .all()
    )
    published = len(tasks_in_window)
    assigned = sum(1 for t in tasks_in_window if t.agent_id)
    completed = sum(1 for t in tasks_in_window if (t.status or "") == "completed")

    task_ids = [t.id for t in tasks_in_window]
    had_bid = 0
    if task_ids:
        had_bid_rows = (
            db.query(TaskBid.task_id)
            .filter(TaskBid.task_id.in_(task_ids))
            .distinct()
            .all()
        )
        had_bid = len(had_bid_rows)

    # Daily buckets for GMV / completed
    def _bucket(dt: Optional[datetime]) -> Optional[str]:
        if not dt:
            return None
        return dt.strftime("%Y-%m-%d")

    daily: Dict[str, Dict[str, int]] = {}
    for t in (
        db.query(Task)
        .filter(Task.created_at >= since)
        .all()
    ):
        d = _bucket(t.created_at)
        if not d:
            continue
        row = daily.setdefault(d, {"published": 0, "completed": 0, "gmv": 0})
        row["published"] += 1
        row["gmv"] += int(t.reward_points or 0)
        if (t.status or "") == "completed":
            row["completed"] += 1
    daily_list = [
        {"date": k, **v} for k, v in sorted(daily.items(), key=lambda kv: kv[0])
    ]

    # Basic retention matrix: cohort = signup date, day-7 activity = had any
    # task-related credit transaction within 7 days of signup.
    retention = _simple_retention_matrix(db, since)

    return {
        "window_days": days,
        "since": since.isoformat() + "Z",
        "gmv": int(gmv or 0),
        "revenue": int(revenue or 0),
        "funnel": {
            "published": published,
            "had_bid_or_subscription": had_bid,
            "assigned": assigned,
            "completed": completed,
            "bid_rate": round(had_bid / published, 4) if published else 0.0,
            "assign_rate": round(assigned / published, 4) if published else 0.0,
            "completion_rate": round(completed / published, 4) if published else 0.0,
        },
        "daily": daily_list,
        "retention": retention,
    }


def _simple_retention_matrix(db: Session, since: datetime) -> Dict[str, Any]:
    """Compute a lightweight weekly retention matrix.

    Buckets users by signup ISO week; for each cohort, reports how many
    remained active (any CreditTransaction) in the next 1/2/4 weeks.
    """
    users = (
        db.query(User.id, User.created_at)
        .filter(User.created_at >= since)
        .all()
    )
    if not users:
        return {"cohorts": []}

    user_ids = [u.id for u in users]
    tx_rows = (
        db.query(CreditTransaction.user_id, CreditTransaction.created_at)
        .filter(
            CreditTransaction.user_id.in_(user_ids),
            CreditTransaction.created_at >= since,
        )
        .all()
    )
    by_user: Dict[int, List[datetime]] = {}
    for uid, at in tx_rows:
        by_user.setdefault(uid, []).append(at)

    cohort_map: Dict[str, Dict[str, int]] = {}
    for u in users:
        if not u.created_at:
            continue
        year, week, _ = u.created_at.isocalendar()
        key = f"{year}-W{week:02d}"
        row = cohort_map.setdefault(key, {"size": 0, "w1": 0, "w2": 0, "w4": 0})
        row["size"] += 1
        activity = by_user.get(u.id, [])
        for t in activity:
            delta = t - u.created_at
            if delta <= timedelta(days=7):
                row["w1"] += 1
                break
        for t in activity:
            delta = t - u.created_at
            if timedelta(days=7) < delta <= timedelta(days=14):
                row["w2"] += 1
                break
        for t in activity:
            delta = t - u.created_at
            if timedelta(days=14) < delta <= timedelta(days=28):
                row["w4"] += 1
                break

    cohorts = [
        {
            "cohort": k,
            "size": v["size"],
            "w1_active": v["w1"],
            "w2_active": v["w2"],
            "w4_active": v["w4"],
        }
        for k, v in sorted(cohort_map.items(), key=lambda kv: kv[0])
    ]
    return {"cohorts": cohorts}
