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

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.database.relational_db import (
    CreditTransaction,
    PlatformClearingAccount,
    PlatformCommissionRecord,
    PublishedSkill,
    SkillRevenueShare,
    User,
    UserCommissionRecord,
)


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
