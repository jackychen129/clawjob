"""Platform clearing account (admin key)."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    PlatformClearingAccount, PlatformCommissionRecord, get_db,
)
from app.domain.task_helpers import get_or_create_clearing_account
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["Admin · 平台账户"])

PLATFORM_ADMIN_KEY = os.getenv("PLATFORM_ADMIN_KEY", "").strip()


def _require_platform_admin(x_platform_admin_key: str = Header(None, alias="X-Platform-Admin-Key")):
    if not PLATFORM_ADMIN_KEY:
        raise HTTPException(status_code=503, detail="未配置 PLATFORM_ADMIN_KEY，无法管理中转账户")
    if x_platform_admin_key != PLATFORM_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="需要平台管理员密钥")


class ClearingAccountUpdateBody(BaseModel):
    alipay_account: str = None
    alipay_name: str = None


@router.get("/platform/clearing-account")
def get_clearing_account(
    db: Session = Depends(get_db),
    _admin=Depends(_require_platform_admin),
):
    """查询平台中转账户：余额与支付宝信息（需管理员密钥）"""
    acc = db.query(PlatformClearingAccount).filter(PlatformClearingAccount.id == 1).first()
    if not acc:
        acc = get_or_create_clearing_account(db)
        db.commit()
    return {
        "balance": acc.balance or 0,
        "alipay_account": acc.alipay_account or "",
        "alipay_name": acc.alipay_name or "",
    }


@router.patch("/platform/clearing-account")
def update_clearing_account(
    body: ClearingAccountUpdateBody,
    db: Session = Depends(get_db),
    _admin=Depends(_require_platform_admin),
):
    """设置中转账户关联支付宝（需管理员密钥或超级用户）"""
    acc = get_or_create_clearing_account(db)
    if body.alipay_account is not None:
        acc.alipay_account = body.alipay_account.strip() or None
    if body.alipay_name is not None:
        acc.alipay_name = body.alipay_name.strip() or None
    db.commit()
    db.refresh(acc)
    return {"balance": acc.balance or 0, "alipay_account": acc.alipay_account or "", "alipay_name": acc.alipay_name or ""}


@router.get("/platform/clearing-account/records")
def list_clearing_commission_records(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin=Depends(_require_platform_admin),
):
    """平台佣金流水（需管理员密钥）"""
    acc = db.query(PlatformClearingAccount).filter(PlatformClearingAccount.id == 1).first()
    if not acc:
        return {"records": [], "total": 0}
    rows = (
        db.query(PlatformCommissionRecord)
        .filter(PlatformCommissionRecord.clearing_account_id == acc.id)
        .order_by(PlatformCommissionRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "records": [
            {"id": r.id, "amount": r.amount, "task_id": r.task_id, "remark": r.remark or "", "created_at": iso_utc(r.created_at)}
            for r in rows
        ],
        "total": len(rows),
    }
