"""
ClawJob - 账户：信用点余额、充值、支付方式绑定、流水
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    get_db,
    User,
    PaymentMethod,
    CreditTransaction,
    RechargeOrder,
    Task,
    Agent,
    UserCommissionRecord,
    UserApiCredential,
)
from app.security import get_current_user, SECRET_KEY
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


def _mask_secret(secret: str) -> str:
    s = (secret or "").strip()
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}***{s[-4:]}"


def _xor_encrypt(plain: str) -> str:
    # 轻量密文存储（避免明文落库）；后续可替换为 KMS/专业密钥管理。
    p = (plain or "").encode("utf-8")
    k = (SECRET_KEY or "clawjob-secret").encode("utf-8") or b"clawjob-secret"
    out = bytes([b ^ k[i % len(k)] for i, b in enumerate(p)])
    return base64.b64encode(out).decode("utf-8")


# ---------- API 密钥托管 ----------
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


# ---------- 收款账户（用户配置的佣金收款）----------
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


# ---------- 佣金（发布方可选配置，任务完成后计入）----------
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


# ---------- 当前用户信息（含余额）----------
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
    }


# ---------- 余额与流水 ----------
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
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    credits = getattr(user, "credits", 0) or 0
    user.credits = credits + body.amount
    tx = CreditTransaction(
        user_id=uid,
        amount=body.amount,
        type="recharge",
        remark=f"充值 +{body.amount} 任务点",
    )
    db.add(tx)
    db.commit()
    db.refresh(user)
    return {"credits": user.credits, "message": f"充值成功，当前余额 {user.credits}"}


# ---------- 充值订单（信用卡/支付宝/比特币渠道）----------
@router.post("/recharge/orders")
def create_recharge_order(
    body: CreateRechargeOrderBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建充值订单，按支付方式返回支付链接/二维码/比特币地址（生产环境对接真实网关）"""
    t = (body.payment_method_type or "").strip().lower()
    if t not in ("alipay", "credit_card", "bitcoin"):
        raise HTTPException(status_code=400, detail="payment_method_type 须为 alipay / credit_card / bitcoin")
    if body.amount <= 0 or body.amount > 1000000:
        raise HTTPException(status_code=400, detail="充值数量需在 1～1000000 之间")
    uid = int(current_user["user_id"])
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 生产环境此处应调用支付网关生成真实 payment_url / payment_qr / btc_address
    import uuid
    gateway_order_id = f"ord_{uuid.uuid4().hex[:16]}"
    payment_url = payment_qr = btc_address = None
    if t == "credit_card":
        payment_url = f"https://pay.example.com/card?order={gateway_order_id}&amount={body.amount}"
    elif t == "alipay":
        payment_qr = f"https://qr.alipay.com/demo_{gateway_order_id}_{body.amount}"
    else:  # bitcoin
        btc_address = f"bc1q{gateway_order_id[:34]}"
    order = RechargeOrder(
        user_id=uid,
        amount=body.amount,
        payment_method_type=t,
        status="pending",
        gateway_order_id=gateway_order_id,
        payment_url=payment_url,
        payment_qr=payment_qr,
        btc_address=btc_address,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return {
        "order_id": order.id,
        "amount": order.amount,
        "payment_method_type": order.payment_method_type,
        "status": order.status,
        "payment_url": order.payment_url,
        "payment_qr": order.payment_qr,
        "btc_address": order.btc_address,
        "message": "订单已创建，请完成支付后点击「确认到账」或等待网关回调",
    }


@router.post("/recharge/confirm")
def confirm_recharge(
    body: ConfirmRechargeBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """确认充值到账（用户点击「已支付」或支付网关 webhook 回调）；仅待支付订单可确认"""
    uid = int(current_user["user_id"])
    order = db.query(RechargeOrder).filter(
        RechargeOrder.id == body.order_id,
        RechargeOrder.user_id == uid,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"订单状态为 {order.status}，无法确认")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    credits = getattr(user, "credits", 0) or 0
    user.credits = credits + order.amount
    tx = CreditTransaction(
        user_id=uid,
        amount=order.amount,
        type="recharge",
        ref_id=order.id,
        remark=f"充值订单 #{order.id}（{order.payment_method_type}）到账 +{order.amount} 任务点",
    )
    db.add(tx)
    db.commit()
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
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "paid_at": r.paid_at.isoformat() if r.paid_at else None,
            }
            for r in rows
        ]
    }


# ---------- 支付方式 ----------
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
    """绑定支付方式（仅保存脱敏展示信息，不存储真实卡号/账号）"""
    t = body.type.strip().lower()
    if t not in ("alipay", "credit_card", "bitcoin"):
        raise HTTPException(status_code=400, detail="type 须为 alipay / credit_card / bitcoin")
    uid = int(current_user["user_id"])
    pm = PaymentMethod(
        user_id=uid,
        type=t,
        masked_info=body.masked_info.strip() or f"{t} ***",
        is_default=False,
    )
    db.add(pm)
    db.commit()
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
