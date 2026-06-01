"""KYC / KYB 服务（C-14）。

职责：
- 提交个人 / 企业 KYC 资料并写入审计记录；
- 管理员审核（通过 / 拒绝），更新用户主表 kyc_status；
- 提现闸门：未通过 KYC 的用户禁止发起提现申请。

身份证 / Tax ID 等敏感字段在数据库存「脱敏 + 密文」，明文不会落库。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

import base64

from app.database.relational_db import KycRecord, User
from app.security import SECRET_KEY


def encrypt_secret(plain: str) -> str:
    """轻量 XOR 加密：用 SECRET_KEY 做 keystream，base64 编码。
    线上等效用 KMS / Vault 替换；这里仅保证 DB dump 不直读出明文。
    """
    p = (plain or "").encode("utf-8")
    k = (SECRET_KEY or "clawjob-secret").encode("utf-8") or b"clawjob-secret"
    out = bytes([b ^ k[i % len(k)] for i, b in enumerate(p)])
    return base64.b64encode(out).decode("utf-8")


_PERSONAL_ID_TYPES = {"id_card", "passport", "driver_license", "other"}


def _mask_id(raw: str) -> str:
    s = (raw or "").strip()
    if len(s) <= 4:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def _validate_personal(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not (payload.get("legal_name") or "").strip():
        return False, "legal_name required"
    id_type = (payload.get("id_type") or "").strip().lower()
    if id_type not in _PERSONAL_ID_TYPES:
        return False, f"id_type must be one of {sorted(_PERSONAL_ID_TYPES)}"
    if not (payload.get("id_number") or "").strip():
        return False, "id_number required"
    return True, ""


def _validate_business(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not (payload.get("business_name") or "").strip():
        return False, "business_name required"
    if not (payload.get("business_id") or "").strip():
        return False, "business_id required"
    if not (payload.get("legal_name") or "").strip():
        return False, "legal representative legal_name required"
    return True, ""


def submit_personal(db: Session, user: User, payload: Dict[str, Any]) -> KycRecord:
    ok, err = _validate_personal(payload)
    if not ok:
        raise ValueError(err)
    raw_id = (payload.get("id_number") or "").strip()
    rec = KycRecord(
        user_id=user.id,
        kind="personal",
        status="pending",
        legal_name=(payload.get("legal_name") or "").strip()[:128],
        id_type=(payload.get("id_type") or "").strip().lower()[:32],
        id_number_masked=_mask_id(raw_id)[:64],
        id_number_cipher=encrypt_secret(raw_id),
        country=(payload.get("country") or "").strip()[:64] or None,
        contact_email=(payload.get("contact_email") or "").strip()[:256] or None,
        contact_phone=(payload.get("contact_phone") or "").strip()[:64] or None,
        attachments=payload.get("attachments") or None,
    )
    db.add(rec)
    user.kyc_status = "pending"
    user.kyc_kind = "personal"
    db.commit()
    db.refresh(rec)
    return rec


def submit_business(db: Session, user: User, payload: Dict[str, Any]) -> KycRecord:
    ok, err = _validate_business(payload)
    if not ok:
        raise ValueError(err)
    raw_id = (payload.get("business_id") or "").strip()
    rec = KycRecord(
        user_id=user.id,
        kind="business",
        status="pending",
        legal_name=(payload.get("legal_name") or "").strip()[:128],
        business_name=(payload.get("business_name") or "").strip()[:256],
        business_id=_mask_id(raw_id)[:128],
        country=(payload.get("country") or "").strip()[:64] or None,
        contact_email=(payload.get("contact_email") or "").strip()[:256] or None,
        contact_phone=(payload.get("contact_phone") or "").strip()[:64] or None,
        attachments=payload.get("attachments") or None,
        id_number_cipher=encrypt_secret(raw_id),
    )
    db.add(rec)
    user.kyc_status = "pending"
    user.kyc_kind = "business"
    db.commit()
    db.refresh(rec)
    return rec


def latest_for_user(db: Session, user_id: int) -> Optional[KycRecord]:
    return (
        db.query(KycRecord)
        .filter(KycRecord.user_id == user_id)
        .order_by(KycRecord.submitted_at.desc())
        .first()
    )


def approve(db: Session, rec: KycRecord, reviewer_id: int) -> KycRecord:
    rec.status = "approved"
    rec.reviewed_at = datetime.utcnow()
    rec.reviewer_id = reviewer_id
    rec.rejection_reason = None
    user = db.query(User).filter(User.id == rec.user_id).first()
    if user is not None:
        user.kyc_status = "approved"
        user.kyc_kind = rec.kind
        user.kyc_approved_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec


def reject(db: Session, rec: KycRecord, reviewer_id: int, reason: str) -> KycRecord:
    rec.status = "rejected"
    rec.reviewed_at = datetime.utcnow()
    rec.reviewer_id = reviewer_id
    rec.rejection_reason = (reason or "").strip()[:512]
    user = db.query(User).filter(User.id == rec.user_id).first()
    if user is not None:
        user.kyc_status = "rejected"
    db.commit()
    db.refresh(rec)
    return rec


def serialize(rec: KycRecord) -> Dict[str, Any]:
    return {
        "id": rec.id,
        "user_id": rec.user_id,
        "kind": rec.kind,
        "status": rec.status,
        "legal_name": rec.legal_name,
        "id_type": rec.id_type,
        "id_number_masked": rec.id_number_masked,
        "country": rec.country,
        "business_name": rec.business_name,
        "business_id": rec.business_id,
        "contact_email": rec.contact_email,
        "contact_phone": rec.contact_phone,
        "attachments": rec.attachments or [],
        "submitted_at": rec.submitted_at.isoformat() if rec.submitted_at else None,
        "reviewed_at": rec.reviewed_at.isoformat() if rec.reviewed_at else None,
        "rejection_reason": rec.rejection_reason,
    }


def is_approved(user: Optional[User]) -> bool:
    if user is None:
        return False
    if os.getenv("KYC_ENFORCE", "1").strip() in ("0", "false", "False"):
        return True
    return getattr(user, "kyc_status", "none") == "approved"


def sandbox_mode_enabled() -> bool:
    return os.getenv("KYC_SANDBOX_MODE", "").strip().lower() in ("1", "true", "yes")


def sandbox_skip(db: Session, user: User) -> KycRecord:
    """沙盒模式：跳过实名审核，仅当 KYC_SANDBOX_MODE=1 时可用。"""
    if not sandbox_mode_enabled():
        raise ValueError("sandbox mode disabled")
    rec = KycRecord(
        user_id=user.id,
        kind="personal",
        status="approved",
        legal_name=(user.username or "sandbox")[:128],
        id_type="sandbox",
        id_number_masked="**sandbox**",
        country="CN",
        reviewed_at=datetime.utcnow(),
        rejection_reason=None,
    )
    db.add(rec)
    user.kyc_status = "approved"
    user.kyc_kind = "sandbox"
    user.kyc_approved_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec


def withdrawal_min_balance() -> int:
    raw = os.getenv("WITHDRAWAL_MIN_AMOUNT", "10").strip() or "10"
    try:
        return max(1, int(raw))
    except ValueError:
        return 10
