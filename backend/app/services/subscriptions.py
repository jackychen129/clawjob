"""订阅与席位（D-18）。

四个档位：
- free：默认 1 席，无月度赠点，平台佣金 0bp 折扣
- pro：1 席，月度 200 任务点，500bp 佣金折扣（5%），可用 RFQ 预览
- team：10 席，月度 1500 任务点，1000bp 佣金折扣（10%），可用 RFQ 提交、优先撮合
- enterprise：50 席，月度 8000 任务点，2000bp 佣金折扣（20%），可用 全部企业级能力

策略上：订阅升级 / 续费会立即按 plan.monthly_credits 给到目标实体（user 或 workspace），
并同步更新 user.subscription_tier 或 workspace.plan / seats。本期不接外部支付网关，
扣款用现有任务点余额完成（消费扣款 = monthly_price_cents / 100，1 cent ≈ 1 任务点）。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import (
    Subscription,
    SubscriptionPlan,
    User,
    Workspace,
    CreditTransaction,
)


DEFAULT_PLANS: List[Dict] = [
    {
        "code": "free",
        "name": "Free",
        "monthly_price_cents": 0,
        "monthly_credits": 0,
        "seat_quota": 3,
        "commission_discount_bp": 0,
        "features": ["basic_publish", "basic_match"],
    },
    {
        "code": "pro",
        "name": "Pro",
        "monthly_price_cents": 1900,
        "monthly_credits": 200,
        "seat_quota": 3,
        "commission_discount_bp": 500,
        "features": ["basic_publish", "rfq_preview", "priority_support"],
    },
    {
        "code": "team",
        "name": "Team",
        "monthly_price_cents": 9900,
        "monthly_credits": 1500,
        "seat_quota": 10,
        "commission_discount_bp": 1000,
        "features": ["rfq_submit", "priority_match", "sandbox_x2", "audit_export"],
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "monthly_price_cents": 49900,
        "monthly_credits": 8000,
        "seat_quota": 50,
        "commission_discount_bp": 2000,
        "features": [
            "rfq_submit",
            "rfq_csv_bulk",
            "priority_match",
            "sandbox_x5",
            "audit_export",
            "dedicated_success",
        ],
    },
]


def ensure_default_plans(db: Session) -> None:
    """确保系统初始化后存在 4 个标准档位。重复调用幂等。"""
    for plan in DEFAULT_PLANS:
        row = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.code == plan["code"])
            .first()
        )
        if row is None:
            db.add(
                SubscriptionPlan(
                    code=plan["code"],
                    name=plan["name"],
                    monthly_price_cents=plan["monthly_price_cents"],
                    monthly_credits=plan["monthly_credits"],
                    seat_quota=plan["seat_quota"],
                    commission_discount_bp=plan["commission_discount_bp"],
                    features=plan["features"],
                    is_active=True,
                )
            )
        else:
            row.monthly_price_cents = plan["monthly_price_cents"]
            row.monthly_credits = plan["monthly_credits"]
            row.seat_quota = plan["seat_quota"]
            row.commission_discount_bp = plan["commission_discount_bp"]
            row.features = plan["features"]
            row.is_active = True
    db.commit()


def list_plans(db: Session) -> List[SubscriptionPlan]:
    return (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.monthly_price_cents.asc())
        .all()
    )


def serialize_plan(p: SubscriptionPlan) -> Dict:
    return {
        "code": p.code,
        "name": p.name,
        "monthly_price_cents": p.monthly_price_cents,
        "monthly_price_credits": p.monthly_price_cents,
        "monthly_credits": p.monthly_credits,
        "seat_quota": p.seat_quota,
        "commission_discount_bp": p.commission_discount_bp,
        "features": p.features or [],
    }


def serialize_subscription(s: Subscription) -> Dict:
    return {
        "id": s.id,
        "plan_code": s.plan_code,
        "status": s.status,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "renews_at": s.renews_at.isoformat() if s.renews_at else None,
        "cancelled_at": s.cancelled_at.isoformat() if s.cancelled_at else None,
        "user_id": s.user_id,
        "workspace_id": s.workspace_id,
        "seats": s.seats,
        "last_charge_amount": s.last_charge_amount,
    }


def _active_for_user(db: Session, user_id: int) -> Optional[Subscription]:
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.workspace_id.is_(None),
            Subscription.status == "active",
        )
        .order_by(Subscription.id.desc())
        .first()
    )


def _active_for_workspace(db: Session, workspace_id: int) -> Optional[Subscription]:
    return (
        db.query(Subscription)
        .filter(
            Subscription.workspace_id == workspace_id, Subscription.status == "active"
        )
        .order_by(Subscription.id.desc())
        .first()
    )


def subscribe_user(db: Session, *, user: User, plan_code: str) -> Subscription:
    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.code == plan_code, SubscriptionPlan.is_active.is_(True))
        .first()
    )
    if plan is None:
        raise ValueError(f"unknown plan: {plan_code}")
    cost = int(plan.monthly_price_cents)  # 1 cent ≈ 1 task point
    if cost > 0:
        try:
            u = db.query(User).filter(User.id == user.id).with_for_update().first()
        except Exception:
            u = user
        if (u.credits or 0) < cost:
            raise ValueError(
                f"task points insufficient: have {u.credits or 0}, need {cost}"
            )
        u.credits = (u.credits or 0) - cost
        db.add(
            CreditTransaction(
                user_id=u.id,
                amount=-cost,
                type="subscription",
                ref_id=plan.id,
                remark=f"订阅 {plan.code} 扣款 {cost}",
            )
        )
    # 取消之前的活跃订阅
    prev = _active_for_user(db, user.id)
    if prev is not None and prev.plan_code != plan.code:
        prev.status = "cancelled"
        prev.cancelled_at = datetime.utcnow()
    sub = Subscription(
        user_id=user.id,
        workspace_id=None,
        plan_code=plan.code,
        status="active",
        started_at=datetime.utcnow(),
        renews_at=datetime.utcnow() + timedelta(days=30),
        seats=plan.seat_quota,
        last_charge_amount=cost,
    )
    db.add(sub)
    user.subscription_tier = plan.code
    user.subscription_renews_at = sub.renews_at
    if plan.monthly_credits:
        user.credits = (user.credits or 0) + int(plan.monthly_credits)
        db.add(
            CreditTransaction(
                user_id=user.id,
                amount=int(plan.monthly_credits),
                type="subscription_credits",
                ref_id=plan.id,
                remark=f"订阅 {plan.code} 月度赠送 {plan.monthly_credits}",
            )
        )
    db.commit()
    db.refresh(sub)
    return sub


def subscribe_workspace(
    db: Session, *, workspace: Workspace, plan_code: str, actor_user_id: int
) -> Subscription:
    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.code == plan_code, SubscriptionPlan.is_active.is_(True))
        .first()
    )
    if plan is None:
        raise ValueError(f"unknown plan: {plan_code}")
    cost = int(plan.monthly_price_cents)
    if cost > 0:
        try:
            ws = (
                db.query(Workspace)
                .filter(Workspace.id == workspace.id)
                .with_for_update()
                .first()
            )
        except Exception:
            ws = workspace
        if (ws.credits or 0) < cost:
            raise ValueError(
                f"workspace credits insufficient: have {ws.credits or 0}, need {cost}"
            )
        ws.credits = (ws.credits or 0) - cost
        db.add(
            CreditTransaction(
                user_id=actor_user_id,
                amount=-cost,
                type="subscription_workspace",
                ref_id=workspace.id,
                remark=f"工作区 {workspace.name} 订阅 {plan.code} 扣款 {cost}",
            )
        )
    prev = _active_for_workspace(db, workspace.id)
    if prev is not None and prev.plan_code != plan.code:
        prev.status = "cancelled"
        prev.cancelled_at = datetime.utcnow()
    sub = Subscription(
        user_id=None,
        workspace_id=workspace.id,
        plan_code=plan.code,
        status="active",
        started_at=datetime.utcnow(),
        renews_at=datetime.utcnow() + timedelta(days=30),
        seats=plan.seat_quota,
        last_charge_amount=cost,
    )
    db.add(sub)
    workspace.plan = plan.code if plan.code in ("free", "team", "enterprise") else workspace.plan
    workspace.seats = plan.seat_quota
    if plan.monthly_credits:
        workspace.credits = (workspace.credits or 0) + int(plan.monthly_credits)
    db.commit()
    db.refresh(sub)
    return sub


def cancel_user(db: Session, *, user: User) -> Optional[Subscription]:
    sub = _active_for_user(db, user.id)
    if sub is None:
        return None
    sub.status = "cancelled"
    sub.cancelled_at = datetime.utcnow()
    user.subscription_tier = "free"
    user.subscription_renews_at = None
    db.commit()
    db.refresh(sub)
    return sub


def get_user_summary(db: Session, *, user: User) -> Dict:
    sub = _active_for_user(db, user.id)
    plan_code = sub.plan_code if sub else (user.subscription_tier or "free")
    plan = (
        db.query(SubscriptionPlan).filter(SubscriptionPlan.code == plan_code).first()
    )
    return {
        "tier": plan_code,
        "renews_at": user.subscription_renews_at.isoformat()
        if user.subscription_renews_at
        else None,
        "active_subscription": serialize_subscription(sub) if sub else None,
        "plan": serialize_plan(plan) if plan else None,
    }
