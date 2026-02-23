"""
ClawJob - 任务大厅：公开任务列表、发布任务、订阅任务
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database.relational_db import get_db, Task, Agent, TaskSubscription, User

router = APIRouter(tags=["clawjob-tasks"])


class PublishTaskBody(BaseModel):
    title: str
    description: str = ""
    task_type: str = "general"
    priority: str = "medium"


class SubscribeTaskBody(BaseModel):
    agent_id: int


def get_optional_user(token: Optional[str] = None):
    """可选认证：无 token 时返回 None"""
    if not token:
        return None
    try:
        from app.security import oauth2_scheme
        from app.main import get_current_user
        # 这里需要从 request 取 token，简化处理：由依赖 get_current_user_optional 提供
        return None
    except Exception:
        return None


@router.get("/tasks")
def list_tasks_public(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """任务大厅：公开列出所有任务（无需登录）"""
    q = db.query(Task).order_by(Task.created_at.desc())
    if status_filter:
        q = q.filter(Task.status == status_filter)
    tasks = q.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        owner = db.query(User).filter(User.id == t.owner_id).first()
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        out.append({
            "id": t.id,
            "title": t.title,
            "description": t.description or "",
            "status": t.status,
            "priority": t.priority,
            "task_type": t.task_type,
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "agent_id": t.agent_id,
            "subscription_count": sub_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"tasks": out, "total": len(out)}


@router.post("/tasks")
def publish_task(
    body: PublishTaskBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: None),  # 将由 main 覆盖为 get_current_user
):
    """发布任务（需登录）"""
    # current_user 由 main 挂载时注入
    raise HTTPException(status_code=501, detail="Use main app mount with get_current_user")


@router.post("/tasks/{task_id}/subscribe")
def subscribe_task(
    task_id: int,
    body: SubscribeTaskBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(lambda: None),
):
    """订阅任务：用我的 Agent 接取/订阅该任务（需登录）"""
    raise HTTPException(status_code=501, detail="Use main app mount with get_current_user")
