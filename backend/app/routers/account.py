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
)
from app.security import get_current_user

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
    return {
        "user_id": user.id,
        "username": user.username,
        "credits": getattr(user, "credits", 0) or 0,
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
