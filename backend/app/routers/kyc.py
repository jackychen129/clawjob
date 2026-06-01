"""KYC / KYB 路由（C-14）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    KycRecord,
    User,
    WithdrawalRequest,
    get_db,
)
from app.security import get_current_user
from app.services import kyc as _kyc
from app.services import payout as _payout

router = APIRouter(prefix="/account/kyc", tags=["kyc"])


class PersonalKycBody(BaseModel):
    legal_name: str
    id_type: str
    id_number: str
    country: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class BusinessKycBody(BaseModel):
    business_name: str
    business_id: str
    legal_name: str
    country: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


def _current_user(db: Session, current_user: dict) -> User:
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("")
def get_my_kyc(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user = _current_user(db, current_user)
    rec = _kyc.latest_for_user(db, user.id)
    return {
        "kyc_status": user.kyc_status,
        "kyc_kind": user.kyc_kind,
        "approved_at": user.kyc_approved_at.isoformat() if user.kyc_approved_at else None,
        "latest": _kyc.serialize(rec) if rec else None,
    }


@router.post("/personal")
def submit_personal(
    body: PersonalKycBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = _current_user(db, current_user)
    try:
        rec = _kyc.submit_personal(db, user, body.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"kyc": _kyc.serialize(rec), "kyc_status": user.kyc_status}


@router.post("/sandbox-skip")
def sandbox_skip_kyc(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """沙盒模式跳过 KYC（需服务端 KYC_SANDBOX_MODE=1）；仅用于开发/演示环境。"""
    user = _current_user(db, current_user)
    if _kyc.is_approved(user):
        rec = _kyc.latest_for_user(db, user.id)
        return {
            "kyc": _kyc.serialize(rec) if rec else None,
            "kyc_status": user.kyc_status,
            "message": "already approved",
        }
    try:
        rec = _kyc.sandbox_skip(db, user)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"kyc": _kyc.serialize(rec), "kyc_status": user.kyc_status, "sandbox": True}


@router.post("/business")
def submit_business(
    body: BusinessKycBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = _current_user(db, current_user)
    try:
        rec = _kyc.submit_business(db, user, body.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"kyc": _kyc.serialize(rec), "kyc_status": user.kyc_status}


# ----- 提现闸门（C-14：approved 后才能申请） -----------------------------------

withdraw_router = APIRouter(prefix="/account/withdrawals", tags=["account"])


class WithdrawBody(BaseModel):
    amount: int


@withdraw_router.get("")
def list_my_withdrawals(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    user = _current_user(db, current_user)
    rows = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.user_id == user.id)
        .order_by(WithdrawalRequest.submitted_at.desc())
        .limit(50)
        .all()
    )
    return {
        "withdrawals": [
            {
                "id": r.id,
                "amount": r.amount,
                "status": r.status,
                "receiving_account_type": r.receiving_account_type,
                "receiving_account_number": r.receiving_account_number,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
                "remark": r.remark,
            }
            for r in rows
        ]
    }


@withdraw_router.post("")
def submit_withdrawal(
    body: WithdrawBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = _current_user(db, current_user)
    if not _kyc.is_approved(user):
        raise HTTPException(status_code=403, detail="提现需先完成 KYC / KYB 审核")
    if not (user.receiving_account_type and user.receiving_account_number):
        raise HTTPException(status_code=400, detail="请先在收款账户中绑定提现账号")
    amount = int(body.amount or 0)
    if amount < _kyc.withdrawal_min_balance():
        raise HTTPException(
            status_code=400,
            detail=f"提现金额至少 {_kyc.withdrawal_min_balance()} 任务点",
        )
    try:
        u = db.query(User).filter(User.id == user.id).with_for_update().first()
    except Exception:
        u = db.query(User).filter(User.id == user.id).first()
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    balance = _payout.withdrawable_balance(u)
    if amount > balance:
        raise HTTPException(
            status_code=400,
            detail=f"可提现余额不足：当前 {balance}，申请 {amount}",
        )
    from_credits, from_commission = _payout.apply_withdrawal_hold(u, amount)
    req = WithdrawalRequest(
        user_id=u.id,
        amount=amount,
        status="pending",
        receiving_account_type=u.receiving_account_type,
        receiving_account_name=u.receiving_account_name,
        receiving_account_number=u.receiving_account_number,
        remark=_payout.encode_hold(from_credits, from_commission),
    )
    db.add(req)
    db.flush()
    _payout.record_withdrawal_hold(
        db,
        u,
        withdrawal_id=req.id,
        from_credits=from_credits,
        from_commission=from_commission,
    )
    db.commit()
    db.refresh(req)
    return {
        "withdrawal_id": req.id,
        "status": req.status,
        "credits_balance": u.credits,
        "commission_balance": u.commission_balance,
        "withdrawable_balance": _payout.withdrawable_balance(u),
        "processing_time_hint_zh": _payout.processing_time_hint_zh(),
        "message": "提现申请已提交，等待管理员审核（人工打款）",
    }
