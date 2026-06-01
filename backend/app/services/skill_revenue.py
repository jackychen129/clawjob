"""Skill 付费分成结算链（D-19）。

两条资金路径：
- 作者收益 → 作者 `user.commission_balance`（复用现有佣金余额，可走提现）；
- 平台抽成 → `PlatformClearingAccount`。

事件类型：
- invoke：每次 Skill 被任务引用并验收成功时结算一次（`per_invoke` 定价）。
- download：市场页下载（`per_download` 定价），本版本仅触发一次计费（同一用户当月幂等）。

结算发生时要求：消费方 `user.credits >= price_per_unit`；不足则拒绝。
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.database.relational_db import (
    CreditTransaction,
    PlatformClearingAccount,
    PlatformCommissionRecord,
    PublishedSkill,
    SkillPurchase,
    SkillRevenueShare,
    User,
    UserCommissionRecord,
)


def refund_window_days() -> int:
    """退款窗口（天），默认 7。可用 SKILL_REFUND_WINDOW_DAYS 配置。"""
    try:
        return max(0, int(os.getenv("SKILL_REFUND_WINDOW_DAYS", "7")))
    except (TypeError, ValueError):
        return 7


def subscription_period_days() -> int:
    """订阅周期（天），默认 30。可用 SKILL_SUBSCRIPTION_DAYS 配置。"""
    try:
        return max(1, int(os.getenv("SKILL_SUBSCRIPTION_DAYS", "30")))
    except (TypeError, ValueError):
        return 30


def _ensure_clearing_account(db: Session) -> PlatformClearingAccount:
    row = db.query(PlatformClearingAccount).first()
    if row is None:
        row = PlatformClearingAccount(balance=0)
        db.add(row)
        db.flush()
    return row


def set_pricing(
    db: Session,
    *,
    skill: PublishedSkill,
    author_user_id: int,
    pricing_model: str,
    price_per_unit: int,
    revenue_share_bp: int = 7000,
) -> PublishedSkill:
    if pricing_model not in ("free", "per_invoke", "per_download", "subscription"):
        raise ValueError("invalid pricing_model")
    if pricing_model == "free":
        price_per_unit = 0
    else:
        if price_per_unit <= 0:
            raise ValueError("price_per_unit must be > 0 for paid pricing")
    if revenue_share_bp < 0 or revenue_share_bp > 10_000:
        raise ValueError("revenue_share_bp must be between 0 and 10000")
    skill.author_user_id = author_user_id
    skill.pricing_model = pricing_model
    skill.price_per_unit = int(price_per_unit)
    skill.revenue_share_bp = int(revenue_share_bp)
    db.commit()
    db.refresh(skill)
    return skill


def charge(
    db: Session,
    *,
    skill: PublishedSkill,
    consumer: User,
    event_kind: str,
    related_task_id: Optional[int] = None,
) -> Optional[SkillRevenueShare]:
    """对一次 Skill 消费事件进行结算。若 skill 为 free 或价格为 0 则返回 None。"""
    if skill.pricing_model in (None, "free") or int(skill.price_per_unit or 0) <= 0:
        return None
    if skill.author_user_id is None:
        raise ValueError("skill has no author; cannot settle revenue share")
    price = int(skill.price_per_unit)
    # 幂等：同一消费者 + 同一 task 的 invoke 只结算一次
    if event_kind == "invoke" and related_task_id is not None:
        existing = (
            db.query(SkillRevenueShare)
            .filter(
                SkillRevenueShare.skill_token == skill.skill_token,
                SkillRevenueShare.consumer_user_id == consumer.id,
                SkillRevenueShare.related_task_id == related_task_id,
                SkillRevenueShare.event_kind == "invoke",
            )
            .first()
        )
        if existing is not None:
            return existing
    try:
        c = db.query(User).filter(User.id == consumer.id).with_for_update().first()
    except Exception:
        c = consumer
    if (c.credits or 0) < price:
        raise ValueError(
            f"consumer credits insufficient: have {c.credits or 0}, need {price}"
        )
    c.credits = (c.credits or 0) - price
    db.add(
        CreditTransaction(
            user_id=c.id,
            amount=-price,
            type="skill_charge",
            ref_id=related_task_id,
            remark=f"Skill {skill.skill_token} {event_kind} 计费 -{price}",
        )
    )
    author_bp = max(0, min(10_000, int(skill.revenue_share_bp or 7000)))
    author_cut = price * author_bp // 10_000
    platform_cut = price - author_cut
    try:
        author = (
            db.query(User)
            .filter(User.id == skill.author_user_id)
            .with_for_update()
            .first()
        )
    except Exception:
        author = (
            db.query(User).filter(User.id == skill.author_user_id).first()
        )
    if author is None:
        raise ValueError("skill author user not found")
    if author_cut > 0:
        author.commission_balance = int(author.commission_balance or 0) + author_cut
        db.add(
            UserCommissionRecord(
                user_id=author.id,
                amount=author_cut,
                task_id=related_task_id,
                remark=f"Skill {skill.skill_token} {event_kind} 分成 +{author_cut}",
            )
        )
    if platform_cut > 0:
        acct = _ensure_clearing_account(db)
        acct.balance = int(acct.balance or 0) + platform_cut
        db.add(
            PlatformCommissionRecord(
                clearing_account_id=acct.id,
                amount=platform_cut,
                task_id=related_task_id,
                remark=f"Skill {skill.skill_token} 平台抽成 +{platform_cut}",
            )
        )
    share = SkillRevenueShare(
        skill_token=skill.skill_token,
        author_user_id=author.id,
        consumer_user_id=c.id,
        related_task_id=related_task_id,
        event_kind=event_kind,
        gross_amount=price,
        platform_fee=platform_cut,
        author_payout=author_cut,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


def list_for_author(
    db: Session, *, author_user_id: int, skip: int = 0, limit: int = 50
) -> Tuple[int, list]:
    q = (
        db.query(SkillRevenueShare)
        .filter(SkillRevenueShare.author_user_id == author_user_id)
        .order_by(SkillRevenueShare.created_at.desc())
    )
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 200)).all()
    return total, rows


def serialize_share(s: SkillRevenueShare) -> dict:
    return {
        "id": s.id,
        "skill_token": s.skill_token,
        "consumer_user_id": s.consumer_user_id,
        "related_task_id": s.related_task_id,
        "event_kind": s.event_kind,
        "gross_amount": s.gross_amount,
        "platform_fee": s.platform_fee,
        "author_payout": s.author_payout,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# --------------------------------------------------------------------------- #
# 购买 / 权益 / 退款（D-19 端到端闭环）                                          #
# --------------------------------------------------------------------------- #


def active_entitlement(
    db: Session, *, skill_token: str, buyer_user_id: int
) -> Optional[SkillPurchase]:
    """返回买家对该 Skill 当前有效的购买凭证（download 永久 / subscription 未过期）。"""
    now = datetime.utcnow()
    rows = (
        db.query(SkillPurchase)
        .filter(
            SkillPurchase.skill_token == skill_token,
            SkillPurchase.buyer_user_id == buyer_user_id,
            SkillPurchase.status == "active",
        )
        .order_by(SkillPurchase.created_at.desc())
        .all()
    )
    for r in rows:
        if r.expires_at is not None and r.expires_at <= now:
            r.status = "expired"
            continue
        return r
    if rows:
        db.commit()
    return None


def purchase(
    db: Session,
    *,
    skill: PublishedSkill,
    buyer: User,
) -> Tuple[SkillPurchase, bool]:
    """买家购买/订阅一个付费 Skill，返回 (凭证, 是否本次新建)。

    - `per_download`：幂等，已拥有有效权益则直接返回（不重复扣点）。
    - `subscription`：若已有未过期订阅则续返回；否则扣点并新建带到期时间的权益。
    - `per_invoke` / `free`：不走购买路径，抛 ValueError 由路由转 400。
    """
    model = (skill.pricing_model or "free").strip()
    if model in ("free",) or int(skill.price_per_unit or 0) <= 0:
        raise ValueError("skill is free; no purchase required")
    if model == "per_invoke":
        raise ValueError(
            "per_invoke skills are settled per task invocation, not via purchase"
        )
    if model not in ("per_download", "subscription"):
        raise ValueError(f"unsupported pricing_model for purchase: {model}")
    if skill.author_user_id is None:
        raise ValueError("skill has no author; cannot settle revenue share")
    if skill.author_user_id == buyer.id:
        raise ValueError("cannot purchase your own skill")

    existing = active_entitlement(
        db, skill_token=skill.skill_token, buyer_user_id=buyer.id
    )
    if existing is not None:
        return existing, False

    share = charge(
        db,
        skill=skill,
        consumer=buyer,
        event_kind="download" if model == "per_download" else "subscribe",
    )
    expires_at = None
    if model == "subscription":
        expires_at = datetime.utcnow() + timedelta(days=subscription_period_days())
    row = SkillPurchase(
        skill_token=skill.skill_token,
        buyer_user_id=buyer.id,
        author_user_id=skill.author_user_id,
        pricing_model=model,
        gross_amount=int(share.gross_amount) if share else 0,
        platform_fee=int(share.platform_fee) if share else 0,
        author_payout=int(share.author_payout) if share else 0,
        revenue_share_id=share.id if share else None,
        status="active",
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, True


def refund(
    db: Session, *, purchase_id: int, buyer_user_id: int
) -> SkillPurchase:
    """退款：在退款窗口内冲正买家扣点、作者分成与平台抽成。

    规则（最小可行）：仅 `active` 状态、且距购买未超过退款窗口的购买可退；退款后
    凭证置为 `refunded`，并写入一条负向 `refund` 收入流水以保持账本平衡。
    """
    row = (
        db.query(SkillPurchase)
        .filter(SkillPurchase.id == purchase_id)
        .first()
    )
    if row is None:
        raise ValueError("purchase not found")
    if row.buyer_user_id != buyer_user_id:
        raise ValueError("only the buyer can refund this purchase")
    if row.status != "active":
        raise ValueError(f"purchase is not refundable (status={row.status})")
    window = refund_window_days()
    created = row.created_at or datetime.utcnow()
    if window > 0 and datetime.utcnow() - created > timedelta(days=window):
        raise ValueError(f"refund window of {window} day(s) has elapsed")

    gross = int(row.gross_amount or 0)
    author_cut = int(row.author_payout or 0)
    platform_cut = int(row.platform_fee or 0)

    buyer = db.query(User).filter(User.id == row.buyer_user_id).first()
    if buyer is None:
        raise ValueError("buyer not found")
    buyer.credits = int(buyer.credits or 0) + gross
    db.add(
        CreditTransaction(
            user_id=buyer.id,
            amount=gross,
            type="skill_refund",
            remark=f"Skill {row.skill_token} 退款 +{gross}",
        )
    )

    if author_cut > 0 and row.author_user_id is not None:
        author = db.query(User).filter(User.id == row.author_user_id).first()
        if author is not None:
            author.commission_balance = max(
                0, int(author.commission_balance or 0) - author_cut
            )
            db.add(
                UserCommissionRecord(
                    user_id=author.id,
                    amount=-author_cut,
                    remark=f"Skill {row.skill_token} 退款冲正 -{author_cut}",
                )
            )
    if platform_cut > 0:
        acct = _ensure_clearing_account(db)
        acct.balance = max(0, int(acct.balance or 0) - platform_cut)
        db.add(
            PlatformCommissionRecord(
                clearing_account_id=acct.id,
                amount=-platform_cut,
                remark=f"Skill {row.skill_token} 退款冲正 -{platform_cut}",
            )
        )

    if gross > 0 and row.author_user_id is not None:
        db.add(
            SkillRevenueShare(
                skill_token=row.skill_token,
                author_user_id=row.author_user_id,
                consumer_user_id=row.buyer_user_id,
                related_task_id=None,
                event_kind="refund",
                gross_amount=-gross,
                platform_fee=-platform_cut,
                author_payout=-author_cut,
            )
        )

    row.status = "refunded"
    row.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def list_purchases_for_buyer(
    db: Session, *, buyer_user_id: int, skip: int = 0, limit: int = 50
) -> Tuple[int, list]:
    q = (
        db.query(SkillPurchase)
        .filter(SkillPurchase.buyer_user_id == buyer_user_id)
        .order_by(SkillPurchase.created_at.desc())
    )
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 200)).all()
    return total, rows


def serialize_purchase(p: SkillPurchase) -> dict:
    now = datetime.utcnow()
    refundable = bool(
        p.status == "active"
        and (
            refund_window_days() == 0
            or (p.created_at and now - p.created_at <= timedelta(days=refund_window_days()))
        )
    )
    return {
        "id": p.id,
        "skill_token": p.skill_token,
        "buyer_user_id": p.buyer_user_id,
        "author_user_id": p.author_user_id,
        "pricing_model": p.pricing_model,
        "gross_amount": p.gross_amount,
        "platform_fee": p.platform_fee,
        "author_payout": p.author_payout,
        "status": p.status,
        "refundable": refundable,
        "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        "refunded_at": p.refunded_at.isoformat() if p.refunded_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
