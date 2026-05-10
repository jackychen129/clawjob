"""工作区 / 团队（D-17）：成员、角色、邀请、共享余额。

角色权限：
- owner：全部权限，工作区只能有 1 名 owner（创建者）。
- admin：成员/角色管理 + 发布 + 充值；不能转让 owner。
- publisher：发布任务 / 提交 RFQ / 消耗余额。
- accounting：查看充值与对账，可发起提现申请，不可发布任务。
- auditor：只读查看（任务、账单、审计）。
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import (
    Workspace,
    WorkspaceMember,
    WorkspaceInvitation,
    User,
)


ROLES = ("owner", "admin", "publisher", "accounting", "auditor")
PUBLISH_ROLES = {"owner", "admin", "publisher"}
BILLING_ROLES = {"owner", "admin", "accounting"}
MEMBER_MGMT_ROLES = {"owner", "admin"}
PLAN_DEFAULT_SEATS = {"free": 3, "team": 10, "enterprise": 50}


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", (name or "").strip().lower()).strip("-")
    return s[:40] or "ws"


def _unique_slug(db: Session, base: str) -> str:
    slug = base or "ws"
    n = 0
    while db.query(Workspace).filter(Workspace.slug == slug).first() is not None:
        n += 1
        slug = f"{base}-{n}"
        if n > 50:
            slug = f"{base}-{secrets.token_hex(3)}"
            break
    return slug


def create_workspace(
    db: Session,
    *,
    owner: User,
    name: str,
    plan: str = "free",
    billing_email: Optional[str] = None,
) -> Workspace:
    nm = (name or "").strip()
    if not nm:
        raise ValueError("name required")
    plan = plan if plan in PLAN_DEFAULT_SEATS else "free"
    seats = PLAN_DEFAULT_SEATS[plan]
    ws = Workspace(
        name=nm[:128],
        slug=_unique_slug(db, _slugify(nm)),
        owner_user_id=owner.id,
        plan=plan,
        seats=seats,
        credits=0,
        billing_email=(billing_email or owner.email)[:256],
    )
    db.add(ws)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=owner.id,
            role="owner",
            invited_by_user_id=owner.id,
        )
    )
    if owner.active_workspace_id is None:
        owner.active_workspace_id = ws.id
    db.commit()
    db.refresh(ws)
    return ws


def get_member(db: Session, workspace_id: int, user_id: int) -> Optional[WorkspaceMember]:
    return (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )


def require_member(
    db: Session, workspace_id: int, user_id: int, allowed_roles: Optional[Iterable[str]] = None
) -> WorkspaceMember:
    m = get_member(db, workspace_id, user_id)
    if m is None:
        raise PermissionError("not a workspace member")
    if allowed_roles is not None and m.role not in set(allowed_roles):
        raise PermissionError(f"role '{m.role}' not allowed; need one of {sorted(allowed_roles)}")
    return m


def list_user_workspaces(db: Session, user_id: int) -> List[Workspace]:
    rows = (
        db.query(Workspace, WorkspaceMember)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at.desc())
        .all()
    )
    return [ws for ws, _m in rows]


def list_members(db: Session, workspace_id: int) -> List[WorkspaceMember]:
    return (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.joined_at.asc())
        .all()
    )


def add_member(
    db: Session, *, workspace: Workspace, user: User, role: str, invited_by: int
) -> WorkspaceMember:
    if role not in ROLES:
        raise ValueError("invalid role")
    if role == "owner":
        raise ValueError("only one owner per workspace; transfer is not supported here")
    existing = get_member(db, workspace.id, user.id)
    if existing is not None:
        existing.role = role
        db.commit()
        db.refresh(existing)
        return existing
    seats_used = (
        db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace.id).count()
    )
    if seats_used >= workspace.seats:
        raise ValueError(f"seat limit reached ({workspace.seats}); upgrade plan to invite more")
    m = WorkspaceMember(
        workspace_id=workspace.id, user_id=user.id, role=role, invited_by_user_id=invited_by
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def remove_member(db: Session, *, workspace: Workspace, user_id: int) -> bool:
    m = get_member(db, workspace.id, user_id)
    if m is None:
        return False
    if m.role == "owner":
        raise ValueError("cannot remove the workspace owner")
    db.delete(m)
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None and user.active_workspace_id == workspace.id:
        user.active_workspace_id = None
    db.commit()
    return True


def update_member_role(
    db: Session, *, workspace: Workspace, target_user_id: int, role: str
) -> WorkspaceMember:
    if role not in ROLES:
        raise ValueError("invalid role")
    if role == "owner":
        raise ValueError("owner role cannot be set via update")
    m = get_member(db, workspace.id, target_user_id)
    if m is None:
        raise ValueError("member not found")
    if m.role == "owner":
        raise ValueError("cannot demote the workspace owner")
    m.role = role
    db.commit()
    db.refresh(m)
    return m


def create_invitation(
    db: Session, *, workspace: Workspace, email: str, role: str, invited_by: int
) -> WorkspaceInvitation:
    if role not in ROLES or role == "owner":
        raise ValueError("invalid role for invitation")
    e = (email or "").strip().lower()
    if "@" not in e:
        raise ValueError("invalid email")
    inv = WorkspaceInvitation(
        workspace_id=workspace.id,
        email=e[:256],
        role=role,
        token=secrets.token_urlsafe(24),
        status="pending",
        invited_by_user_id=invited_by,
        expires_at=datetime.utcnow() + timedelta(days=14),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def accept_invitation(db: Session, *, token: str, user: User) -> WorkspaceMember:
    inv = (
        db.query(WorkspaceInvitation)
        .filter(WorkspaceInvitation.token == token)
        .first()
    )
    if inv is None:
        raise ValueError("invitation not found")
    if inv.status != "pending":
        raise ValueError(f"invitation already {inv.status}")
    if inv.expires_at and inv.expires_at < datetime.utcnow():
        inv.status = "expired"
        db.commit()
        raise ValueError("invitation expired")
    ws = db.query(Workspace).filter(Workspace.id == inv.workspace_id).first()
    if ws is None:
        raise ValueError("workspace not found")
    member = add_member(
        db, workspace=ws, user=user, role=inv.role, invited_by=inv.invited_by_user_id
    )
    inv.status = "accepted"
    inv.accepted_at = datetime.utcnow()
    if user.active_workspace_id is None:
        user.active_workspace_id = ws.id
    db.commit()
    db.refresh(member)
    return member


def serialize_workspace(ws: Workspace, *, member: Optional[WorkspaceMember] = None) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "slug": ws.slug,
        "plan": ws.plan,
        "seats": ws.seats,
        "credits": ws.credits,
        "billing_email": ws.billing_email,
        "owner_user_id": ws.owner_user_id,
        "kyb_record_id": ws.kyb_record_id,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "my_role": member.role if member else None,
    }


def serialize_member(m: WorkspaceMember, *, user: Optional[User] = None) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "role": m.role,
        "username": user.username if user else None,
        "email": user.email if user else None,
        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
    }


def serialize_invitation(inv: WorkspaceInvitation) -> dict:
    return {
        "id": inv.id,
        "workspace_id": inv.workspace_id,
        "email": inv.email,
        "role": inv.role,
        "token": inv.token,
        "status": inv.status,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
    }
