"""Admin dashboard routes (extracted from admin.py)."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task, User, get_db

router = APIRouter()


@router.get("/overview")
def get_admin_overview(db: Session = Depends(get_db)):
    from app.services.admin_overview import get_cached_admin_overview

    return get_cached_admin_overview(db)


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    from app.services.admin_overview import build_admin_overview

    snapshot = build_admin_overview(db)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "tasks": {
            **snapshot["tasks"],
            "today": db.query(Task).filter(Task.created_at >= today_start).count(),
        },
        "users": {
            **snapshot["users"],
            "active": db.query(User).filter(User.is_active == True).count(),  # noqa: E712
        },
        "agents": {
            **snapshot["agents"],
            "active": db.query(Agent).filter(Agent.is_active == True).count(),  # noqa: E712
        },
        "rewards_paid": snapshot["rewards_paid"],
        "pending_settlements": snapshot["pending"]["settlements"],
        "observability": snapshot["observability"],
        "generated_at": snapshot["generated_at"],
    }


@router.get("/me")
def admin_me():
    return {"ok": True, "is_superuser": True}
