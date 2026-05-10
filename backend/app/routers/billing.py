"""订阅与 Skill 分成账本路由（D-18 / D-19）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    User,
    Workspace,
    PublishedSkill,
    get_db,
)
from app.security import get_current_user
from app.services import subscriptions as _subs
from app.services import skill_revenue as _skill_rev
from app.services import workspaces as _ws


router = APIRouter(tags=["billing"])


# ---------------- 订阅计划目录（公开） ----------------

@router.get("/subscriptions/plans")
def list_plans(db: Session = Depends(get_db)):
    _subs.ensure_default_plans(db)
    return {"plans": [_subs.serialize_plan(p) for p in _subs.list_plans(db)]}


# ---------------- 个人订阅 ----------------


class SubscribeUserBody(BaseModel):
    plan_code: str


@router.get("/account/subscription")
def get_my_subscription(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    _subs.ensure_default_plans(db)
    user = db.query(User).filter(User.id == int(current_user["user_id"])).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _subs.get_user_summary(db, user=user)


@router.post("/account/subscription/subscribe")
def subscribe_user(
    body: SubscribeUserBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _subs.ensure_default_plans(db)
    user = db.query(User).filter(User.id == int(current_user["user_id"])).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    try:
        sub = _subs.subscribe_user(db, user=user, plan_code=body.plan_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "subscription": _subs.serialize_subscription(sub),
        "summary": _subs.get_user_summary(db, user=user),
    }


@router.post("/account/subscription/cancel")
def cancel_user_subscription(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == int(current_user["user_id"])).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    sub = _subs.cancel_user(db, user=user)
    return {
        "cancelled": sub is not None,
        "summary": _subs.get_user_summary(db, user=user),
    }


# ---------------- 工作区订阅 ----------------


class SubscribeWorkspaceBody(BaseModel):
    plan_code: str


@router.post("/workspaces/{workspace_id}/subscribe")
def subscribe_workspace(
    workspace_id: int,
    body: SubscribeWorkspaceBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _subs.ensure_default_plans(db)
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if ws is None:
        raise HTTPException(status_code=404, detail="工作区不存在")
    user_id = int(current_user["user_id"])
    member = _ws.get_member(db, ws.id, user_id)
    if member is None or member.role not in _ws.BILLING_ROLES:
        raise HTTPException(status_code=403, detail="仅 owner / admin / accounting 可订阅")
    try:
        sub = _subs.subscribe_workspace(
            db, workspace=ws, plan_code=body.plan_code, actor_user_id=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "subscription": _subs.serialize_subscription(sub),
        "workspace": {
            "id": ws.id,
            "plan": ws.plan,
            "seats": ws.seats,
            "credits": ws.credits,
        },
    }


# ---------------- Skill 付费分成 ----------------


class SkillPricingBody(BaseModel):
    pricing_model: str  # free | per_invoke | per_download | subscription
    price_per_unit: int = 0
    revenue_share_bp: int = 7000


@router.post("/skills/{skill_token}/pricing")
def set_skill_pricing(
    skill_token: str,
    body: SkillPricingBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    skill = (
        db.query(PublishedSkill)
        .filter(PublishedSkill.skill_token == skill_token)
        .first()
    )
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill 未发布")
    uid = int(current_user["user_id"])
    # 首次定价时锁定作者；后续仅作者或超管可改
    if skill.author_user_id and skill.author_user_id != uid:
        user = db.query(User).filter(User.id == uid).first()
        if not user or not user.is_superuser:
            raise HTTPException(status_code=403, detail="仅 Skill 作者可修改定价")
    try:
        skill = _skill_rev.set_pricing(
            db,
            skill=skill,
            author_user_id=uid,
            pricing_model=body.pricing_model,
            price_per_unit=int(body.price_per_unit or 0),
            revenue_share_bp=int(body.revenue_share_bp or 7000),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "skill_token": skill.skill_token,
        "pricing_model": skill.pricing_model,
        "price_per_unit": skill.price_per_unit,
        "revenue_share_bp": skill.revenue_share_bp,
        "author_user_id": skill.author_user_id,
    }


@router.post("/skills/{skill_token}/charge")
def trigger_skill_charge(
    skill_token: str,
    related_task_id: Optional[int] = None,
    event_kind: str = "download",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """消费方手动触发计费（前端下载场景 / 测试用）。invoke 场景由任务完成流水自动触发。"""
    skill = (
        db.query(PublishedSkill)
        .filter(PublishedSkill.skill_token == skill_token)
        .first()
    )
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill 未发布")
    uid = int(current_user["user_id"])
    consumer = db.query(User).filter(User.id == uid).first()
    if consumer is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    try:
        share = _skill_rev.charge(
            db,
            skill=skill,
            consumer=consumer,
            event_kind=event_kind if event_kind in ("invoke", "download", "subscribe") else "download",
            related_task_id=related_task_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if share is None:
        return {"charged": False, "reason": "skill is free or price=0"}
    return {"charged": True, "share": _skill_rev.serialize_share(share)}


@router.get("/account/skill-revenue")
def list_my_skill_revenue(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    total, rows = _skill_rev.list_for_author(
        db, author_user_id=uid, skip=skip, limit=limit
    )
    payout_sum = sum(int(r.author_payout or 0) for r in rows)
    return {
        "total": total,
        "skip": skip,
        "visible_payout_sum": payout_sum,
        "items": [_skill_rev.serialize_share(r) for r in rows],
    }
