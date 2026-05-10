"""
支付渠道注册表：统一维护支持的充值/绑定支付方式，供 account 路由复用。

设计目标：
- 单一数据源：新增渠道只改本文件（及可选的前端 i18n）
- 渠道元信息：显示名、类型族（url/qr/crypto/bank/direct）、币种、限额、费率、图标
- 订单指引生成器：按渠道生成支付 URL / 二维码 / 地址 / 银行信息，并写入 RechargeOrder 已有字段（保持 schema 不变）
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


PaymentKind = str  # url | qr | crypto | bank | direct


@dataclass
class PaymentMethodSpec:
    key: str  # 唯一键，用于 payment_method_type 存储
    display_name: str
    kind: PaymentKind
    currency: str = "credits"  # 展示用；credits=任务点
    min_amount: int = 1
    max_amount: int = 1_000_000
    fee_rate: float = 0.0  # 仅展示，实际扣费在信用点体系外
    icon: str = ""
    enabled: bool = True
    description: str = ""
    tags: list = field(default_factory=list)  # ["popular", "crypto", "wallet"]


# NOTE: 新增渠道请在此数组添加条目。
PAYMENT_METHOD_SPECS: Dict[str, PaymentMethodSpec] = {
    m.key: m
    for m in [
        PaymentMethodSpec(
            key="alipay",
            display_name="支付宝",
            kind="qr",
            icon="alipay",
            fee_rate=0.006,
            description="扫码即付，到账最快。",
            tags=["popular", "wallet"],
        ),
        PaymentMethodSpec(
            key="wechat_pay",
            display_name="微信支付",
            kind="qr",
            icon="wechat",
            fee_rate=0.006,
            description="微信扫码支付。",
            tags=["popular", "wallet"],
        ),
        PaymentMethodSpec(
            key="credit_card",
            display_name="信用卡",
            kind="url",
            icon="credit-card",
            fee_rate=0.029,
            description="Visa / MasterCard / JCB / AmEx。",
            tags=["popular"],
        ),
        PaymentMethodSpec(
            key="stripe",
            display_name="Stripe 付款页",
            kind="url",
            icon="stripe",
            fee_rate=0.029,
            description="国际信用卡收银台。",
            tags=["international"],
        ),
        PaymentMethodSpec(
            key="paypal",
            display_name="PayPal",
            kind="url",
            icon="paypal",
            fee_rate=0.034,
            description="PayPal 账户 / 跨境信用卡。",
            tags=["international"],
        ),
        PaymentMethodSpec(
            key="apple_pay",
            display_name="Apple Pay",
            kind="url",
            icon="apple",
            fee_rate=0.029,
            description="iPhone / Mac 触发原生支付。",
            tags=["wallet"],
        ),
        PaymentMethodSpec(
            key="google_pay",
            display_name="Google Pay",
            kind="url",
            icon="google",
            fee_rate=0.029,
            description="Android 设备原生钱包。",
            tags=["wallet"],
        ),
        PaymentMethodSpec(
            key="bank_transfer",
            display_name="银行转账",
            kind="bank",
            icon="bank",
            fee_rate=0.0,
            min_amount=100,
            description="人工对账，T+1 到账；大额推荐。",
            tags=["large"],
        ),
        PaymentMethodSpec(
            key="bitcoin",
            display_name="Bitcoin",
            kind="crypto",
            icon="btc",
            fee_rate=0.0,
            description="BTC 主网地址。",
            tags=["crypto"],
        ),
        PaymentMethodSpec(
            key="usdt_trc20",
            display_name="USDT (TRC20)",
            kind="crypto",
            icon="usdt",
            fee_rate=0.0,
            description="TRON 网络，手续费最低。",
            tags=["crypto", "stablecoin"],
        ),
        PaymentMethodSpec(
            key="usdt_erc20",
            display_name="USDT (ERC20)",
            kind="crypto",
            icon="usdt",
            fee_rate=0.0,
            description="以太坊主网，适合大额。",
            tags=["crypto", "stablecoin"],
        ),
    ]
}


def list_public_catalog() -> list[dict[str, Any]]:
    """面向前端的渠道目录（仅 enabled）。"""
    out = []
    for m in PAYMENT_METHOD_SPECS.values():
        if not m.enabled:
            continue
        out.append(
            {
                "key": m.key,
                "display_name": m.display_name,
                "kind": m.kind,
                "currency": m.currency,
                "min_amount": m.min_amount,
                "max_amount": m.max_amount,
                "fee_rate": m.fee_rate,
                "icon": m.icon,
                "description": m.description,
                "tags": list(m.tags),
            }
        )
    return out


def is_supported(key: str) -> bool:
    m = PAYMENT_METHOD_SPECS.get((key or "").strip().lower())
    return bool(m and m.enabled)


def validate_amount(key: str, amount: int) -> Optional[str]:
    """返回 None 表示通过，字符串表示错误原因。"""
    m = PAYMENT_METHOD_SPECS.get(key)
    if not m:
        return f"不支持的支付方式：{key}"
    if amount < m.min_amount:
        return f"{m.display_name} 最低充值 {m.min_amount} 点"
    if amount > m.max_amount:
        return f"{m.display_name} 单笔最高 {m.max_amount} 点"
    return None


def build_order_instrument(key: str, amount: int) -> Dict[str, Any]:
    """
    为渠道生成支付指引；返回值可直接塞进 RechargeOrder（复用 payment_url / payment_qr / btc_address 三列）
    以及给前端展示用的 `instructions` 结构。
    """
    spec = PAYMENT_METHOD_SPECS[key]
    gateway_order_id = f"ord_{uuid.uuid4().hex[:16]}"

    payment_url: Optional[str] = None
    payment_qr: Optional[str] = None
    btc_address: Optional[str] = None
    instructions: Dict[str, Any] = {
        "method": key,
        "display_name": spec.display_name,
        "kind": spec.kind,
        "amount": amount,
    }

    if spec.kind == "url":
        base = {
            "credit_card": "https://pay.example.com/card",
            "stripe": "https://checkout.stripe.com/pay",
            "paypal": "https://www.paypal.com/checkoutnow",
            "apple_pay": "https://pay.example.com/apple-pay",
            "google_pay": "https://pay.example.com/google-pay",
        }.get(key, "https://pay.example.com/redirect")
        payment_url = f"{base}?order={gateway_order_id}&amount={amount}"
        instructions["url"] = payment_url
    elif spec.kind == "qr":
        qr_base = {
            "alipay": "https://qr.alipay.com/demo",
            "wechat_pay": "weixin://wxpay/bizpayurl?pr=demo",
        }.get(key, "https://pay.example.com/qr")
        payment_qr = f"{qr_base}_{gateway_order_id}_{amount}"
        instructions["qr_payload"] = payment_qr
        instructions["note"] = "请使用 App 扫码完成支付"
    elif spec.kind == "bank":
        instructions["bank"] = {
            "bank_name": "招商银行",
            "account_name": "ClawJob Platform Ltd.",
            "account_number": "6214 8500 0000 0000",
            "swift_code": "CMBCCNBS",
            "memo": gateway_order_id,  # 重要：必须备注以便对账
        }
        instructions["note"] = "请在转账备注填写订单号，T+1 完成对账后到账"
    elif spec.kind == "crypto":
        prefix = {
            "bitcoin": "bc1q",
            "usdt_trc20": "T",
            "usdt_erc20": "0x",
        }.get(key, "addr_")
        suffix = gateway_order_id[: 34 if key == "bitcoin" else 40]
        addr = f"{prefix}{suffix}"
        btc_address = addr  # 复用列
        instructions["crypto"] = {
            "network": {
                "bitcoin": "Bitcoin mainnet",
                "usdt_trc20": "TRON (TRC20)",
                "usdt_erc20": "Ethereum (ERC20)",
            }.get(key, "unknown"),
            "address": addr,
            "memo": gateway_order_id,
        }
        instructions["note"] = "请务必使用正确的主网转账，错网将导致资产损失"

    return {
        "gateway_order_id": gateway_order_id,
        "payment_url": payment_url,
        "payment_qr": payment_qr,
        "btc_address": btc_address,
        "instructions": instructions,
    }


def instructions_from_order(order: Any) -> Dict[str, Any]:
    """根据 RechargeOrder 存储的三列反推指引（用于订单列表回显）。"""
    key = (getattr(order, "payment_method_type", "") or "").strip().lower()
    spec = PAYMENT_METHOD_SPECS.get(key)
    out: Dict[str, Any] = {
        "method": key,
        "display_name": spec.display_name if spec else key,
        "kind": spec.kind if spec else "url",
        "amount": int(getattr(order, "amount", 0) or 0),
    }
    if getattr(order, "payment_url", None):
        out["url"] = order.payment_url
    if getattr(order, "payment_qr", None):
        out["qr_payload"] = order.payment_qr
    if getattr(order, "btc_address", None):
        out["crypto"] = {"address": order.btc_address}
    return out
