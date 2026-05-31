"""任务点 → 现金提现：可提现余额、冻结与驳回回退。"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.database.relational_db import CreditTransaction, User, UserCommissionRecord, WithdrawalRequest
from app.services import kyc as _kyc

HOLD_PREFIX = "__hold__:"


def processing_time_hint_zh() -> str:
    return os.getenv("WITHDRAWAL_PROCESSING_HINT", "T+3 工作日，人工审核后打款至收款账户")


def withdrawal_fee_bp() -> int:
    raw = os.getenv("WITHDRAWAL_FEE_BP", "0").strip() or "0"
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def withdrawable_balance(user: User) -> int:
    credits = int(getattr(user, "credits", 0) or 0)
    commission = int(getattr(user, "commission_balance", 0) or 0)
    return max(0, credits + commission)


def split_deduction(user: User, amount: int) -> Tuple[int, int]:
    """优先扣任务点 credits（含任务奖励），不足部分扣 commission_balance。"""
    credits = int(getattr(user, "credits", 0) or 0)
    from_credits = min(credits, amount)
    from_commission = amount - from_credits
    return from_credits, from_commission


def encode_hold(from_credits: int, from_commission: int) -> str:
    return f"{HOLD_PREFIX}{json.dumps({'from_credits': from_credits, 'from_commission': from_commission})}"


def parse_hold(remark: Optional[str]) -> Optional[Dict[str, int]]:
    if not remark or not remark.startswith(HOLD_PREFIX):
        return None
    try:
        data = json.loads(remark[len(HOLD_PREFIX) :])
        if isinstance(data, dict):
            return {
                "from_credits": int(data.get("from_credits", 0) or 0),
                "from_commission": int(data.get("from_commission", 0) or 0),
            }
    except Exception:
        return None
    return None


def apply_withdrawal_hold(user: User, amount: int) -> Tuple[int, int]:
    from_credits, from_commission = split_deduction(user, amount)
    user.credits = int(getattr(user, "credits", 0) or 0) - from_credits
    user.commission_balance = int(getattr(user, "commission_balance", 0) or 0) - from_commission
    return from_credits, from_commission


def record_withdrawal_hold(
    db: Session,
    user: User,
    *,
    withdrawal_id: int,
    from_credits: int,
    from_commission: int,
) -> None:
    if from_credits:
        db.add(
            CreditTransaction(
                user_id=user.id,
                amount=-from_credits,
                type="withdrawal_hold",
                ref_id=withdrawal_id,
                remark=f"提现申请 #{withdrawal_id} 冻结 -{from_credits} 任务点",
            )
        )
    if from_commission:
        db.add(
            UserCommissionRecord(
                user_id=user.id,
                amount=-from_commission,
                remark=f"提现申请 #{withdrawal_id} 冻结佣金 -{from_commission}",
            )
        )


def refund_withdrawal_hold(
    db: Session,
    user: User,
    *,
    withdrawal_id: int,
    hold: Dict[str, int],
) -> None:
    from_credits = int(hold.get("from_credits", 0) or 0)
    from_commission = int(hold.get("from_commission", 0) or 0)
    if from_credits:
        user.credits = int(getattr(user, "credits", 0) or 0) + from_credits
        db.add(
            CreditTransaction(
                user_id=user.id,
                amount=from_credits,
                type="withdrawal_refund",
                ref_id=withdrawal_id,
                remark=f"提现申请 #{withdrawal_id} 驳回，任务点退回 +{from_credits}",
            )
        )
    if from_commission:
        user.commission_balance = int(getattr(user, "commission_balance", 0) or 0) + from_commission
        db.add(
            UserCommissionRecord(
                user_id=user.id,
                amount=from_commission,
                remark=f"提现申请 #{withdrawal_id} 驳回，佣金退回 +{from_commission}",
            )
        )


def compute_payout_eligibility(db: Session, user: User) -> Dict[str, Any]:
    credits = int(getattr(user, "credits", 0) or 0)
    commission = int(getattr(user, "commission_balance", 0) or 0)
    withdrawable = credits + commission
    min_amt = _kyc.withdrawal_min_balance()
    kyc_status = getattr(user, "kyc_status", "none") or "none"
    kyc_ok = _kyc.is_approved(user)
    recv_ok = bool(user.receiving_account_type and user.receiving_account_number)

    pending_wd = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.user_id == user.id, WithdrawalRequest.status == "pending")
        .count()
    )

    task_reward_earned = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user.id, CreditTransaction.type == "task_reward")
        .with_entities(CreditTransaction.amount)
        .all()
    )
    task_earnings = sum(int(r[0] or 0) for r in task_reward_earned)

    blockers: List[str] = []
    if not kyc_ok:
        if kyc_status == "pending":
            blockers.append("kyc_pending")
        elif kyc_status == "rejected":
            blockers.append("kyc_rejected")
        else:
            blockers.append("kyc_required")
    if not recv_ok:
        blockers.append("receiving_account_required")
    if withdrawable < min_amt:
        blockers.append("below_min_balance")

    eligible = not blockers and withdrawable >= min_amt

    return {
        "credits_balance": credits,
        "commission_balance": commission,
        "withdrawable_balance": withdrawable,
        "task_reward_earned": task_earnings,
        "min_withdraw_amount": min_amt,
        "withdrawal_fee_bp": withdrawal_fee_bp(),
        "processing_time_hint_zh": processing_time_hint_zh(),
        "kyc_status": kyc_status,
        "kyc_approved": kyc_ok,
        "receiving_account_configured": recv_ok,
        "receiving_account_type": getattr(user, "receiving_account_type", None),
        "pending_withdrawals": int(pending_wd),
        "eligible": eligible,
        "blockers": blockers,
        "manual_review": True,
    }
