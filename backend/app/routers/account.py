"""
ClawJob - 账户：信用点余额、充值、支付方式绑定、流水
"""
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.relational_db import (
    get_db,
    User,
    Agent,
    Task,
    PaymentMethod,
    CreditTransaction,
    RechargeOrder,
    Task,
    Agent,
    UserCommissionRecord,
    UserApiCredential,
    Referral,
)
from app.security import get_current_user, SECRET_KEY
from app.services.payment_methods import (
    PAYMENT_METHOD_SPECS,
    build_order_instrument,
    instructions_from_order,
    is_supported,
    list_public_catalog,
    validate_amount,
)
from app.services import payout as _payout
import base64

router = APIRouter(prefix="/account", tags=["account"])


class RechargeBody(BaseModel):
    amount: int  # 充值任务点数量
    payment_method_id: int = None  # 可选，用哪张卡/方式


class BindPaymentBody(BaseModel):
    type: str  # alipay | credit_card | bitcoin
    masked_info: str  # 脱敏信息，如 支付宝 ***@a.com、卡尾号1234、bc1q***


class CreateRechargeOrderBody(BaseModel):
    amount: int  # 充值任务点数量
    payment_method_type: str  # credit_card | alipay | bitcoin


class ConfirmRechargeBody(BaseModel):
    order_id: int


class ReceivingAccountBody(BaseModel):
    """收款账户（用于接收发布方配置的佣金）"""
    account_type: str  # alipay, bank_card
    account_name: str  # 户名/实名
    account_number: str  # 账号/卡号（可脱敏，如 ***1234）


class ApiKeyCreateBody(BaseModel):
    provider: str
    label: str
    secret: str


def _task_pulse_for_user(db: Session, uid: int) -> dict:
    """当前用户与任务相关的待办计数：验收、交付、等对方确认、争议。"""
    agent_ids = [r[0] for r in db.query(Agent.id).filter(Agent.owner_id == uid).all()]
    awaiting_verify_as_owner = (
        db.query(Task)
        .filter(Task.owner_id == uid, Task.status == "pending_verification")
        .count()
    )
    need_submit = 0
    awaiting_confirm_as_assignee = 0
    if agent_ids:
        need_submit = (
            db.query(Task)
            .filter(Task.agent_id.in_(agent_ids), Task.status.in_(("open", "in_progress")))
            .count()
        )
        awaiting_confirm_as_assignee = (
            db.query(Task)
            .filter(Task.agent_id.in_(agent_ids), Task.status == "pending_verification")
            .count()
        )
    if agent_ids:
        disputes = (
            db.query(Task)
            .filter(
                Task.status == "disputed",
                or_(Task.owner_id == uid, Task.agent_id.in_(agent_ids)),
            )
            .count()
        )
    else:
        disputes = db.query(Task).filter(Task.status == "disputed", Task.owner_id == uid).count()
    total = awaiting_verify_as_owner + awaiting_confirm_as_assignee + need_submit + disputes
    return {
        "awaiting_verify_as_owner": int(awaiting_verify_as_owner),
        "awaiting_confirm_as_assignee": int(awaiting_confirm_as_assignee),
        "need_submit": int(need_submit),
        "disputes": int(disputes),
        "total_actionable": int(total),
    }


def _mask_secret(secret: str) -> str:
    s = (secret or "").strip()
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}***{s[-4:]}"


def _xor_encrypt(plain: str) -> str:
    # NOTE: translated comment in English.
    p = (plain or "").encode("utf-8")
    k = (SECRET_KEY or "clawjob-secret").encode("utf-8") or b"clawjob-secret"
    out = bytes([b ^ k[i % len(k)] for i, b in enumerate(p)])
    return base64.b64encode(out).decode("utf-8")


class WithdrawRequestBody(BaseModel):
    amount: int


@router.get("/payout-eligibility")
def get_payout_eligibility(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Agent 拥有者提现资格：任务点余额、KYC、收款账户、最低门槛。"""
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _payout.compute_payout_eligibility(db, user)


@router.post("/withdraw/request")
def request_withdraw_alias(
    body: WithdrawRequestBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """提现申请别名路由，逻辑同 POST /account/withdrawals。"""
    from app.routers.kyc import submit_withdrawal, WithdrawBody

    return submit_withdrawal(WithdrawBody(amount=body.amount), db=db, current_user=current_user)


# NOTE: translated comment in English.
@router.get("/api-keys")
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    rows = (
        db.query(UserApiCredential)
        .filter(UserApiCredential.user_id == uid)
        .order_by(UserApiCredential.updated_at.desc(), UserApiCredential.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "provider": r.provider,
                "label": r.label,
                "secret_masked": r.secret_masked,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    }


@router.post("/api-keys")
def create_api_key(
    body: ApiKeyCreateBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    provider = (body.provider or "").strip().lower()[:64]
    label = (body.label or "").strip()[:128]
    secret = (body.secret or "").strip()
    if not provider:
        raise HTTPException(status_code=400, detail="provider 不能为空")
    if not label:
        raise HTTPException(status_code=400, detail="label 不能为空")
    if len(secret) < 8:
        raise HTTPException(status_code=400, detail="secret 长度不能少于 8")
    row = UserApiCredential(
        user_id=uid,
        provider=provider,
        label=label,
        secret_cipher=_xor_encrypt(secret),
        secret_masked=_mask_secret(secret),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "provider": row.provider,
        "label": row.label,
        "secret_masked": row.secret_masked,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.delete("/api-keys/{key_id}")
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    row = db.query(UserApiCredential).filter(UserApiCredential.id == key_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="API key 不存在")
    if row.user_id != uid:
        raise HTTPException(status_code=403, detail="无权删除该 API key")
    db.delete(row)
    db.commit()
    return {"ok": True, "id": key_id}


# NOTE: translated comment in English.
@router.get("/receiving-account")
def get_receiving_account(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取当前用户的收款账户配置"""
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "account_type": getattr(user, "receiving_account_type", None) or "",
        "account_name": getattr(user, "receiving_account_name", None) or "",
        "account_number": getattr(user, "receiving_account_number", None) or "",
    }


@router.patch("/receiving-account")
def update_receiving_account(
    body: ReceivingAccountBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新当前用户的收款账户（用于接收发布方配置的佣金）"""
    t = (body.account_type or "").strip().lower()
    if t not in ("alipay", "bank_card"):
        raise HTTPException(status_code=400, detail="account_type 须为 alipay 或 bank_card")
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.receiving_account_type = t
    user.receiving_account_name = (body.account_name or "").strip()[:64]
    user.receiving_account_number = (body.account_number or "").strip()[:128]
    db.commit()
    db.refresh(user)
    return {
        "account_type": user.receiving_account_type,
        "account_name": user.receiving_account_name or "",
        "account_number": user.receiving_account_number or "",
    }


# NOTE: translated comment in English.
@router.get("/commission")
def get_commission(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """当前用户佣金余额与流水"""
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    balance = getattr(user, "commission_balance", 0) or 0
    rows = (
        db.query(UserCommissionRecord)
        .filter(UserCommissionRecord.user_id == uid)
        .order_by(UserCommissionRecord.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "commission_balance": balance,
        "records": [
            {
                "id": r.id,
                "amount": r.amount,
                "task_id": r.task_id,
                "remark": r.remark,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


# NOTE: translated comment in English.
@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """当前登录用户信息与信用点余额"""
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    is_guest = (getattr(user, "username", "") or "").startswith("guest_")
    return {
        "user_id": user.id,
        "username": user.username,
        "credits": getattr(user, "credits", 0) or 0,
        "commission_balance": getattr(user, "commission_balance", 0) or 0,
        "is_guest": is_guest,
        "task_pulse": _task_pulse_for_user(db, uid),
    }


# NOTE: translated comment in English.
@router.get("/publish-fee-estimate")
def estimate_publish_fee(
    reward_points: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布任务前的费用预估：奖励点、平台佣金、执行方到手、发布方余额剩余。

    用于前端发布页在用户输入奖励点时实时预估，保持前后端算法一致（运行时读取平台佣金比例）。
    """
    from app.main import _compute_publish_fee, MAX_TASK_REWARD_POINTS

    rp = max(0, int(reward_points or 0))
    if rp > MAX_TASK_REWARD_POINTS:
        raise HTTPException(
            status_code=400,
            detail=f"单任务奖励点数不能超过 {MAX_TASK_REWARD_POINTS}",
        )
    fee = _compute_publish_fee(rp)
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    credits = int(getattr(user, "credits", 0) or 0) if user else 0
    remaining = credits - rp
    return {
        **fee,
        "publisher_credits": credits,
        "publisher_credits_after": remaining,
        "sufficient": remaining >= 0,
    }


@router.get("/balance")
def get_balance(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我的信用点余额"""
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"credits": getattr(user, "credits", 0) or 0}


@router.get("/transactions")
def list_transactions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """信用点流水"""
    uid = int(current_user["user_id"])
    rows = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == uid)
        .order_by(CreditTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "transactions": [
            {
                "id": r.id,
                "amount": r.amount,
                "type": r.type,
                "ref_id": r.ref_id,
                "remark": r.remark,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.post("/recharge")
def recharge(
    body: RechargeBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """充值信用点（模拟：直接增加余额，兼容旧前端；推荐使用 /recharge/orders + /recharge/confirm 按支付渠道充值）"""
    if body.amount <= 0 or body.amount > 1000000:
        raise HTTPException(status_code=400, detail="充值数量需在 1～1000000 之间")
    uid = int(current_user["user_id"])
    try:
        user = db.query(User).filter(User.id == uid).with_for_update().first()
    except Exception:
        user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    credits = int(getattr(user, "credits", 0) or 0)
    user.credits = credits + int(body.amount)
    tx = CreditTransaction(
        user_id=uid,
        amount=int(body.amount),
        type="recharge",
        remark=f"充值 +{body.amount} 任务点",
    )
    db.add(tx)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="充值失败，请稍后重试")
    db.refresh(user)
    return {"credits": user.credits, "message": f"充值成功，当前余额 {user.credits}"}


@router.get("/recharge/methods")
def recharge_methods_catalog():
    """支付渠道目录：供前端渲染充值面板 / 绑卡页面。"""
    return {"methods": list_public_catalog()}


# NOTE: translated comment in English.
@router.post("/recharge/orders")
def create_recharge_order(
    body: CreateRechargeOrderBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建充值订单，按支付渠道返回支付指引（URL / 二维码 / 银行账号 / 加密地址等）。"""
    t = (body.payment_method_type or "").strip().lower()
    if not is_supported(t):
        supported = ", ".join(sorted(PAYMENT_METHOD_SPECS.keys()))
        raise HTTPException(status_code=400, detail=f"payment_method_type 须为 {supported}")
    amount = int(body.amount)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="充值数量需大于 0")
    err = validate_amount(t, amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    inst = build_order_instrument(t, amount)
    order = RechargeOrder(
        user_id=uid,
        amount=amount,
        payment_method_type=t,
        status="pending",
        gateway_order_id=inst["gateway_order_id"],
        payment_url=inst["payment_url"],
        payment_qr=inst["payment_qr"],
        btc_address=inst["btc_address"],
    )
    db.add(order)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="创建充值订单失败，请稍后重试")
    db.refresh(order)
    return {
        "order_id": order.id,
        "amount": order.amount,
        "payment_method_type": order.payment_method_type,
        "status": order.status,
        "payment_url": order.payment_url,
        "payment_qr": order.payment_qr,
        "btc_address": order.btc_address,
        "instructions": inst["instructions"],
        "message": "订单已创建，请按指引完成支付后确认到账或等待网关回调",
    }


@router.post("/recharge/confirm")
def confirm_recharge(
    body: ConfirmRechargeBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """确认充值到账（用户点击「已支付」或支付网关 webhook 回调）。

    幂等与并发安全：
    - 对订单与用户行加 FOR UPDATE，避免并发确认双倍加款；
    - 若订单已是 paid，直接返回当前状态（不再加款）。
    """
    uid = int(current_user["user_id"])
    try:
        order = (
            db.query(RechargeOrder)
            .filter(RechargeOrder.id == body.order_id, RechargeOrder.user_id == uid)
            .with_for_update()
            .first()
        )
    except Exception:
        order = (
            db.query(RechargeOrder)
            .filter(RechargeOrder.id == body.order_id, RechargeOrder.user_id == uid)
            .first()
        )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    try:
        user = db.query(User).filter(User.id == uid).with_for_update().first()
    except Exception:
        user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if order.status == "paid":
        return {
            "credits": getattr(user, "credits", 0) or 0,
            "message": "订单已到账（幂等）",
            "order_id": order.id,
            "idempotent": True,
        }
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"订单状态为 {order.status}，无法确认")
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    credits = int(getattr(user, "credits", 0) or 0)
    user.credits = credits + int(order.amount or 0)
    tx = CreditTransaction(
        user_id=uid,
        amount=int(order.amount or 0),
        type="recharge",
        ref_id=order.id,
        remark=f"充值订单 #{order.id}（{order.payment_method_type}）到账 +{order.amount} 任务点",
    )
    db.add(tx)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="充值到账失败，请稍后重试")
    db.refresh(user)
    return {"credits": user.credits, "message": "充值已到账", "order_id": order.id}


@router.get("/recharge/orders")
def list_recharge_orders(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我的充值订单列表"""
    uid = int(current_user["user_id"])
    rows = (
        db.query(RechargeOrder)
        .filter(RechargeOrder.user_id == uid)
        .order_by(RechargeOrder.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "orders": [
            {
                "id": r.id,
                "amount": r.amount,
                "payment_method_type": r.payment_method_type,
                "status": r.status,
                "payment_url": r.payment_url,
                "payment_qr": r.payment_qr,
                "btc_address": r.btc_address,
                "instructions": instructions_from_order(r),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "paid_at": r.paid_at.isoformat() if r.paid_at else None,
            }
            for r in rows
        ]
    }


# NOTE: translated comment in English.
@router.get("/payment-methods")
def list_payment_methods(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我绑定的支付方式"""
    uid = int(current_user["user_id"])
    rows = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.user_id == uid)
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.id.desc())
        .all()
    )
    return {
        "payment_methods": [
            {
                "id": r.id,
                "type": r.type,
                "masked_info": r.masked_info,
                "is_default": r.is_default,
            }
            for r in rows
        ]
    }


@router.post("/payment-methods")
def bind_payment_method(
    body: BindPaymentBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """绑定支付方式（仅保存脱敏展示信息，不存储真实卡号/账号）。"""
    t = (body.type or "").strip().lower()
    if not is_supported(t):
        supported = ", ".join(sorted(PAYMENT_METHOD_SPECS.keys()))
        raise HTTPException(status_code=400, detail=f"type 须为 {supported}")
    uid = int(current_user["user_id"])
    spec = PAYMENT_METHOD_SPECS[t]
    masked = (body.masked_info or "").strip() or f"{spec.display_name} ***"
    pm = PaymentMethod(
        user_id=uid,
        type=t,
        masked_info=masked[:200],
        is_default=False,
    )
    db.add(pm)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="绑定支付方式失败，请稍后重试")
    db.refresh(pm)
    return {"id": pm.id, "type": pm.type, "masked_info": pm.masked_info}


@router.delete("/payment-methods/{pm_id}")
def unbind_payment_method(
    pm_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """解绑支付方式"""
    uid = int(current_user["user_id"])
    pm = db.query(PaymentMethod).filter(PaymentMethod.id == pm_id, PaymentMethod.user_id == uid).first()
    if not pm:
        raise HTTPException(status_code=404, detail="支付方式不存在")
    db.delete(pm)
    db.commit()
    return {"message": "已解绑"}


@router.get("/referral")
def get_my_referral(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """个人邀请中心：返回邀请码、邀请链接样本、累计邀请人数、累计发放返点。"""
    from app.services import referrals as _rf

    uid = int(current_user["user_id"])
    try:
        user = db.query(User).filter(User.id == uid).with_for_update().first()
    except Exception:
        user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    code = _rf.ensure_user_code(db, user)
    try:
        db.commit()
    except Exception:
        db.rollback()
    rels = db.query(Referral).filter(Referral.referrer_user_id == uid).all()
    total_invited = len(rels)
    rewarded = [r for r in rels if r.first_task_reward_at is not None]
    total_reward_points = int(sum(r.referrer_bonus_points or 0 for r in rewarded))
    pending = total_invited - len(rewarded)
    frontend_url = (os.getenv("FRONTEND_URL", "") or "").rstrip("/")
    share_link = f"{frontend_url}/register?ref={code}" if frontend_url else f"/register?ref={code}"
    return {
        "user_id": uid,
        "referral_code": code,
        "share_link": share_link,
        "total_invited": total_invited,
        "completed_first_task": len(rewarded),
        "pending_first_task": pending,
        "total_reward_points": total_reward_points,
        "bonus_policy": {
            "referrer_points": _rf.referrer_bonus_points(),
            "invitee_points": _rf.invitee_bonus_points(),
            "trigger": "invitee_first_task_reward",
        },
    }


@router.get("/referral/records")
def list_my_referral_records(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """邀请明细：谁在什么时候被邀请，是否已触发首单返点。"""
    uid = int(current_user["user_id"])
    rels = (
        db.query(Referral)
        .filter(Referral.referrer_user_id == uid)
        .order_by(Referral.signup_at.desc())
        .limit(200)
        .all()
    )
    out = []
    for r in rels:
        invitee = db.query(User).filter(User.id == r.invitee_user_id).first()
        out.append({
            "id": r.id,
            "invitee_user_id": r.invitee_user_id,
            "invitee_username": invitee.username if invitee else None,
            "signup_at": r.signup_at.isoformat() + "Z" if r.signup_at else None,
            "first_task_reward_at": r.first_task_reward_at.isoformat() + "Z" if r.first_task_reward_at else None,
            "referrer_bonus_points": int(r.referrer_bonus_points or 0),
            "invitee_bonus_points": int(r.invitee_bonus_points or 0),
            "status": "rewarded" if r.first_task_reward_at else "pending",
        })
    return {"records": out, "total": len(out)}
