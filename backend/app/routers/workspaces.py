"""工作区 / 团队（D-17）+ 企业级 RFQ 批量发布（B-9）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    CreditTransaction,
    Task,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
    SystemLog,
    get_db,
)
from app.security import get_current_user
from app.services import workspaces as _ws
from app.services import kyc as _kyc
from app.services import safety_pipeline as _safety


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------


class CreateWorkspaceBody(BaseModel):
    name: str
    plan: Optional[str] = "free"
    billing_email: Optional[str] = None


class InviteBody(BaseModel):
    email: str
    role: str = "publisher"


class UpdateRoleBody(BaseModel):
    role: str


class RechargeWorkspaceBody(BaseModel):
    amount: int
    note: Optional[str] = None


class AcceptInviteBody(BaseModel):
    token: str


class RfqItem(BaseModel):
    title: str
    description: Optional[str] = ""
    task_type: Optional[str] = "general"
    priority: Optional[str] = "medium"
    reward_points: Optional[int] = 0
    completion_webhook_url: Optional[str] = None
    category: Optional[str] = None
    requirements: Optional[str] = None
    skills: Optional[List[str]] = None
    deadline_days: Optional[int] = None


class RfqSubmitBody(BaseModel):
    items: List[RfqItem]
    note: Optional[str] = None


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _current_user(db: Session, current_user: dict) -> User:
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _get_workspace(db: Session, workspace_id: int) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if ws is None:
        raise HTTPException(status_code=404, detail="工作区不存在")
    return ws


def _require_role(
    db: Session, ws: Workspace, user_id: int, allowed: List[str]
) -> WorkspaceMember:
    m = _ws.get_member(db, ws.id, user_id)
    if m is None:
        raise HTTPException(status_code=403, detail="非工作区成员")
    if m.role not in set(allowed):
        raise HTTPException(
            status_code=403,
            detail=f"角色 '{m.role}' 无权操作（需要 {sorted(allowed)} 之一）",
        )
    return m


# -----------------------------------------------------------------------------
# Workspace CRUD + members
# -----------------------------------------------------------------------------


@router.post("")
def create_workspace(
    body: CreateWorkspaceBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = _current_user(db, current_user)
    if (body.plan or "free") in ("team", "enterprise") and not _kyc.is_approved(user):
        raise HTTPException(
            status_code=403,
            detail="升级到 team / enterprise 工作区需先完成 KYB 企业认证",
        )
    try:
        ws = _ws.create_workspace(
            db,
            owner=user,
            name=body.name,
            plan=body.plan or "free",
            billing_email=body.billing_email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    member = _ws.get_member(db, ws.id, user.id)
    return _ws.serialize_workspace(ws, member=member)


@router.get("/mine")
def list_mine(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    user = _current_user(db, current_user)
    rows = _ws.list_user_workspaces(db, user.id)
    out = []
    for ws in rows:
        m = _ws.get_member(db, ws.id, user.id)
        out.append(_ws.serialize_workspace(ws, member=m))
    return {"workspaces": out, "active_workspace_id": user.active_workspace_id}


@router.post("/active")
def set_active_workspace(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = _current_user(db, current_user)
    ws_id = body.get("workspace_id")
    if ws_id is None:
        user.active_workspace_id = None
        db.commit()
        return {"active_workspace_id": None}
    ws = _get_workspace(db, int(ws_id))
    _require_role(db, ws, user.id, list(_ws.ROLES))
    user.active_workspace_id = ws.id
    db.commit()
    return {"active_workspace_id": ws.id}


@router.get("/{workspace_id}")
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    m = _require_role(db, ws, user.id, list(_ws.ROLES))
    return {
        **_ws.serialize_workspace(ws, member=m),
        "members": [
            _ws.serialize_member(
                mm,
                user=db.query(User).filter(User.id == mm.user_id).first(),
            )
            for mm in _ws.list_members(db, ws.id)
        ],
    }


@router.get("/{workspace_id}/members")
def list_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    _require_role(db, ws, user.id, list(_ws.ROLES))
    members = _ws.list_members(db, ws.id)
    return {
        "members": [
            _ws.serialize_member(
                mm,
                user=db.query(User).filter(User.id == mm.user_id).first(),
            )
            for mm in members
        ]
    }


@router.post("/{workspace_id}/invite")
def invite(
    workspace_id: int,
    body: InviteBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    _require_role(db, ws, user.id, list(_ws.MEMBER_MGMT_ROLES))
    try:
        inv = _ws.create_invitation(
            db, workspace=ws, email=body.email, role=body.role, invited_by=user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _ws.serialize_invitation(inv)


@router.post("/accept-invite")
def accept_invite(
    body: AcceptInviteBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = _current_user(db, current_user)
    try:
        m = _ws.accept_invitation(db, token=body.token, user=user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ws = _get_workspace(db, m.workspace_id)
    return {
        "workspace": _ws.serialize_workspace(ws, member=m),
        "joined": True,
    }


@router.post("/{workspace_id}/members/{user_id}/role")
def update_member_role(
    workspace_id: int,
    user_id: int,
    body: UpdateRoleBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    _require_role(db, ws, user.id, list(_ws.MEMBER_MGMT_ROLES))
    try:
        m = _ws.update_member_role(
            db, workspace=ws, target_user_id=user_id, role=body.role
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    target = db.query(User).filter(User.id == user_id).first()
    return _ws.serialize_member(m, user=target)


@router.delete("/{workspace_id}/members/{user_id}")
def remove_member(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    _require_role(db, ws, user.id, list(_ws.MEMBER_MGMT_ROLES))
    try:
        ok = _ws.remove_member(db, workspace=ws, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"removed": ok}


# -----------------------------------------------------------------------------
# 工作区充值（共享余额）
# -----------------------------------------------------------------------------


@router.post("/{workspace_id}/recharge")
def recharge_workspace(
    workspace_id: int,
    body: RechargeWorkspaceBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    _require_role(db, ws, user.id, list(_ws.BILLING_ROLES))
    amount = int(body.amount or 0)
    if amount <= 0 or amount > 1_000_000:
        raise HTTPException(status_code=400, detail="充值金额需在 1～1,000,000 之间")
    try:
        ws_locked = (
            db.query(Workspace).filter(Workspace.id == ws.id).with_for_update().first()
        )
    except Exception:
        ws_locked = ws
    ws_locked.credits = int(ws_locked.credits or 0) + amount
    db.add(
        CreditTransaction(
            user_id=user.id,
            amount=amount,
            type="workspace_recharge",
            ref_id=ws.id,
            remark=f"工作区 #{ws.id} {ws.name} 充值 +{amount}（{body.note or ''}）",
        )
    )
    db.commit()
    db.refresh(ws_locked)
    return {
        "workspace_id": ws.id,
        "credits": ws_locked.credits,
        "message": f"工作区充值成功，当前余额 {ws_locked.credits}",
    }


# -----------------------------------------------------------------------------
# B-9 RFQ 批量发布
# -----------------------------------------------------------------------------


def _validate_rfq_items(items: List[RfqItem]) -> None:
    if not items:
        raise HTTPException(status_code=400, detail="RFQ 至少包含 1 条任务")
    if len(items) > 50:
        raise HTTPException(status_code=400, detail="单次 RFQ 最多 50 条任务")
    for idx, it in enumerate(items):
        if not (it.title or "").strip():
            raise HTTPException(status_code=400, detail=f"第 {idx + 1} 行缺少 title")
        rp = int(it.reward_points or 0)
        if rp < 0:
            raise HTTPException(status_code=400, detail=f"第 {idx + 1} 行 reward_points 必须 ≥ 0")
        if rp > 0 and not (it.completion_webhook_url or "").startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail=f"第 {idx + 1} 行设置了 reward_points 但未填写 completion_webhook_url",
            )


def _safety_check_items(items: List[RfqItem], user_id: int) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for it in items:
        try:
            t = _safety.sanitize_text(None, it.title, source="rfq", user_id=user_id) or it.title
            d = (
                _safety.sanitize_text(None, it.description, source="rfq", user_id=user_id)
                or it.description
            )
            r = (
                _safety.sanitize_text(None, it.requirements, source="rfq", user_id=user_id)
                or it.requirements
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"内容安全策略：{str(e)}",
            )
        sanitized.append({"title": t, "description": d, "requirements": r})
    return sanitized


@router.post("/{workspace_id}/rfq/preview")
def rfq_preview(
    workspace_id: int,
    body: RfqSubmitBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    _require_role(db, ws, user.id, list(_ws.PUBLISH_ROLES))
    _validate_rfq_items(body.items)
    safe = _safety_check_items(body.items, user.id)
    total = sum(int(it.reward_points or 0) for it in body.items)
    return {
        "workspace_id": ws.id,
        "credits_available": ws.credits,
        "credits_required": total,
        "sufficient": ws.credits >= total,
        "items": [
            {
                "title": s["title"],
                "task_type": it.task_type or "general",
                "reward_points": int(it.reward_points or 0),
                "completion_webhook_url": it.completion_webhook_url,
                "category": it.category,
                "skills": it.skills or [],
            }
            for it, s in zip(body.items, safe)
        ],
    }


@router.post("/{workspace_id}/rfq/submit")
def rfq_submit(
    workspace_id: int,
    body: RfqSubmitBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    ws = _get_workspace(db, workspace_id)
    user = _current_user(db, current_user)
    _require_role(db, ws, user.id, list(_ws.PUBLISH_ROLES))
    _validate_rfq_items(body.items)
    safe = _safety_check_items(body.items, user.id)
    total = sum(int(it.reward_points or 0) for it in body.items)
    try:
        ws_locked = (
            db.query(Workspace).filter(Workspace.id == ws.id).with_for_update().first()
        )
    except Exception:
        ws_locked = ws
    if int(ws_locked.credits or 0) < total:
        raise HTTPException(
            status_code=400,
            detail=f"工作区余额不足：当前 {ws_locked.credits}，需要 {total}",
        )
    created: List[Dict[str, Any]] = []
    for idx, it in enumerate(body.items):
        s = safe[idx]
        rp = int(it.reward_points or 0)
        extra: Dict[str, Any] = {
            "rfq_batch": True,
            "workspace_id": ws.id,
            "submitted_by_user_id": user.id,
        }
        if it.skills:
            extra["skills"] = [str(x).strip()[:50] for x in it.skills if x][:20]
        task = Task(
            title=(s["title"] or "")[:200],
            description=s["description"],
            task_type=(it.task_type or "general")[:32],
            priority=(it.priority or "medium")[:16],
            status="open",
            owner_id=user.id,
            agent_id=None,
            reward_points=rp,
            completion_webhook_url=it.completion_webhook_url,
            category=(it.category or "")[:64] or None,
            requirements=s["requirements"],
            input_data=extra,
        )
        db.add(task)
        db.flush()
        if rp > 0:
            db.add(
                CreditTransaction(
                    user_id=user.id,
                    amount=-rp,
                    type="rfq_publish",
                    ref_id=task.id,
                    remark=f"工作区 #{ws.id} RFQ 任务 #{task.id} 扣款 {rp}",
                )
            )
        created.append({"task_id": task.id, "title": task.title, "reward_points": rp})
    if total > 0:
        ws_locked.credits = int(ws_locked.credits or 0) - total
    db.add(
        SystemLog(
            level="info",
            category="task",
            message="rfq_submitted",
            user_id=user.id,
            extra={
                "workspace_id": ws.id,
                "task_ids": [c["task_id"] for c in created],
                "total_credits": total,
            },
        )
    )
    db.commit()
    db.refresh(ws_locked)
    return {
        "workspace_id": ws.id,
        "credits_remaining": ws_locked.credits,
        "credits_charged": total,
        "tasks": created,
        "message": f"RFQ 已批量发布 {len(created)} 条任务",
    }
