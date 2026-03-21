"""
管理后台：核心指标、运行日志（仅 is_superuser 可访问）
"""
from datetime import datetime, timedelta
from typing import Optional, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database.relational_db import get_db, User, Task, Agent, SystemLog
from app.services.escrow_tasks import get_escrow, save_escrow_to_task, apply_escrow_milestone_confirm

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
    hour_ago = now - timedelta(hours=1)

    tasks_total = db.query(Task).count()
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    tasks_today = db.query(Task).filter(Task.created_at >= today_start).count()
    tasks_pending_verification = db.query(Task).filter(Task.status == "pending_verification").count()
    tasks_disputed = db.query(Task).filter(Task.status == "disputed").count()

    users_total = db.query(User).count()
    users_new_today = db.query(User).filter(User.created_at >= today_start).count()
    users_active_count = db.query(User).filter(User.is_active == True).count()

    agents_total = db.query(Agent).count()
    agents_today = db.query(Agent).filter(Agent.created_at >= today_start).count()
    agents_active = db.query(Agent).filter(Agent.is_active == True).count()

    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0

    requests_last_hour = db.query(SystemLog).filter(
        SystemLog.category == "request",
        SystemLog.created_at >= hour_ago,
    ).count()
    errors_last_hour = db.query(SystemLog).filter(
        SystemLog.level == "error",
        SystemLog.created_at >= hour_ago,
    ).count()

    return {
        "tasks": {
            "total": tasks_total,
            "open": tasks_open,
            "completed": tasks_completed,
            "today": tasks_today,
            "pending_verification": tasks_pending_verification,
            "disputed": tasks_disputed,
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
        "observability": {
            "requests_last_hour": int(requests_last_hour),
            "errors_last_hour": int(errors_last_hour),
        },
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

@router.get("/tasks/disputed")
def get_disputed_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Task).filter(Task.status == "disputed").order_by(desc(Task.updated_at), desc(Task.id))
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 200)).all()
    items = []
    for t in rows:
        escrow = get_escrow(t) or {}
        items.append({
            "id": t.id,
            "title": t.title,
            "owner_id": t.owner_id,
            "agent_id": t.agent_id,
            "status": t.status,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "dispute_reason": escrow.get("dispute_reason"),
            "dispute_evidence": escrow.get("dispute_evidence"),
            "current_index": int(escrow.get("current_index", 0) or 0),
            "milestones_total": len(escrow.get("milestones") or []),
        })
    return {"items": items, "total": total, "skip": skip, "limit": len(items)}


class EscrowDisputeResolveBody(BaseModel):
    note: str = ""
    resolution_type: str = "resume"


@router.post("/tasks/{task_id}/escrow/dispute/resolve")
def admin_resolve_escrow_dispute(
    task_id: int,
    body: EscrowDisputeResolveBody,
    db: Session = Depends(get_db),
):
    """解除托管争议冻结，恢复为可继续执行（in_progress / open）。"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    escrow = get_escrow(task)
    if not escrow:
        raise HTTPException(status_code=400, detail="该任务未启用托管")
    resolution_type = (body.resolution_type or "").strip() or "resume"

    # 通用：取消冻结标记，清空争议理由（保留其它审计字段用于前端回显）
    escrow["disputed"] = False
    escrow["dispute_reason"] = None
    if (body.note or "").strip():
        escrow["admin_resolve_note"] = (body.note or "").strip()[:2000]

    ms = escrow.get("milestones") or []
    current_index = int(escrow.get("current_index", 0) or 0)

    if resolution_type == "force_confirm":
        # 直接按当前里程碑执行“放款/推进”逻辑（等价于发布者验收通过）。
        task.status = "pending_verification"
        save_escrow_to_task(task, escrow)
        info = apply_escrow_milestone_confirm(task, db, auto=False)
        db.commit()
        return {
            "ok": True,
            "task_id": task_id,
            "status": task.status,
            "resolution_type": resolution_type,
            "escrow": {
                "milestone_index": info.get("milestone_index", current_index),
                "finished": bool(info.get("escrow_finished")),
            },
            "reward_paid": int(info.get("reward_paid", 0) or 0),
            "commission": int(info.get("commission", 0) or 0),
        }

    # 默认 resume：解冻后回到可继续状态（in_progress / open），由接取者重新提交完成，发布者再走确认/拒绝。
    save_escrow_to_task(task, escrow)
    task.status = "in_progress" if task.agent_id else "open"
    db.commit()
    finished = current_index >= (len(ms) - 1) if ms else False
    return {
        "ok": True,
        "task_id": task_id,
        "status": task.status,
        "resolution_type": resolution_type,
        "escrow": {
            "milestone_index": current_index,
            "finished": finished,
        },
    }
