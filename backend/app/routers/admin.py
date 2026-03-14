"""
管理后台：核心指标、运行日志（仅 is_superuser 可访问）
"""
from datetime import datetime
from typing import Optional, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database.relational_db import get_db, User, Task, Agent, SystemLog

router = APIRouter(prefix="", tags=["admin"])


def get_superuser_dep(get_current_user: Callable, get_db_fn: Callable):
    """返回「要求超级用户」的依赖，供 main 在 include_router 时注入。"""
    async def _require_superuser(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db_fn),
    ):
        uid = current_user.get("user_id")
        if uid is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要登录")
        try:
            uid_int = int(uid)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无效用户")
        user = db.query(User).filter(User.id == uid_int).first()
        if not user or not getattr(user, "is_superuser", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
        return {"user_id": uid, "username": getattr(user, "username", None)}
    return _require_superuser


@router.get("/metrics")
def get_metrics(
    db: Session = Depends(get_db),
):
    """核心指标：任务数、新注册人数、Agent 数等（含今日新增）。需管理员权限。"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    tasks_total = db.query(Task).count()
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    tasks_today = db.query(Task).filter(Task.created_at >= today_start).count()
    tasks_pending_verification = db.query(Task).filter(Task.status == "pending_verification").count()

    users_total = db.query(User).count()
    users_new_today = db.query(User).filter(User.created_at >= today_start).count()
    users_active_count = db.query(User).filter(User.is_active == True).count()

    agents_total = db.query(Agent).count()
    agents_today = db.query(Agent).filter(Agent.created_at >= today_start).count()
    agents_active = db.query(Agent).filter(Agent.is_active == True).count()

    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0

    return {
        "tasks": {
            "total": tasks_total,
            "open": tasks_open,
            "completed": tasks_completed,
            "today": tasks_today,
            "pending_verification": tasks_pending_verification,
        },
        "users": {
            "total": users_total,
            "new_today": users_new_today,
            "active": users_active_count,
        },
        "agents": {
            "total": agents_total,
            "new_today": agents_today,
            "active": agents_active,
        },
        "rewards_paid": int(rewards_paid),
        "generated_at": now.isoformat(),
    }


@router.get("/logs")
def get_logs(
    skip: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """分页查询系统日志（请求、认证、任务等）。"""
    q = db.query(SystemLog).order_by(desc(SystemLog.created_at))
    if level:
        q = q.filter(SystemLog.level == level)
    if category:
        q = q.filter(SystemLog.category == category)
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 500)).all()
    return {
        "items": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "level": r.level,
                "category": r.category,
                "message": r.message,
                "path": r.path,
                "method": r.method,
                "status_code": r.status_code,
                "user_id": r.user_id,
                "extra": r.extra,
            }
            for r in rows
        ],
        "total": total,
        "skip": skip,
        "limit": len(rows),
    }


@router.get("/me")
def admin_me():
    """确认当前用户为管理员（由路由级 dependency 校验），供前端判断是否展示管理入口。"""
    return {"ok": True, "is_superuser": True}
