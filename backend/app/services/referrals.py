"""邀请返点（Referral）服务。

规则：
- 每个用户拥有唯一 `referral_code`（16 位，大小写+数字，规避歧义字符），按需懒生成。
- 新用户注册时可携带 `referral_code`，系统建立一条 `Referral(referrer, invitee)` 关系；不可互邀。
- 被邀请人完成第一笔 **有奖励** 的任务（即首次 `type=task_reward` 流水，作为 agent 接取方收款）时，
  发布方与接取方双方触发一次性返点（仅第一次，幂等）。
- 风控：不可自邀；referral_code 空/非本平台格式 → 忽略；同一 `invitee_user_id` 唯一约束，防止重复绑定。
"""

from __future__ import annotations

import logging
import os
import secrets
import string
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.database.relational_db import CreditTransaction, Referral, User


logger = logging.getLogger(__name__)


REFERRAL_CODE_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
REFERRAL_CODE_LEN = 10


def _default_points_env(name: str, fallback: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return fallback
    try:
        v = int(str(raw).strip())
    except (TypeError, ValueError):
        return fallback
    if v < 0 or v > 5000:
        return fallback
    return v


def referrer_bonus_points() -> int:
    return _default_points_env("REFERRAL_BONUS_REFERRER", 100)


def invitee_bonus_points() -> int:
    return _default_points_env("REFERRAL_BONUS_INVITEE", 50)


def generate_unique_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(REFERRAL_CODE_ALPHABET) for _ in range(REFERRAL_CODE_LEN))
        if not db.query(User).filter(User.referral_code == code).first():
            return code
    raise RuntimeError("failed to generate unique referral code")


def ensure_user_code(db: Session, user: User) -> str:
    """惰性分配邀请码。调用方需要再 commit。"""
    if getattr(user, "referral_code", None):
        return user.referral_code
    user.referral_code = generate_unique_code(db)
    return user.referral_code


def resolve_referrer(db: Session, raw_code: Optional[str]) -> Optional[User]:
    if not raw_code:
        return None
    code = str(raw_code).strip().upper()
    if not code or len(code) < 4 or len(code) > 32:
        return None
    return db.query(User).filter(User.referral_code == code).first()


def bind_referral(
    db: Session,
    *,
    invitee: User,
    raw_code: Optional[str],
) -> Optional[Referral]:
    """尝试绑定邀请关系。已绑定或自邀/无码返回 None。调用方需 commit。"""
    if not raw_code:
        return None
    if not invitee or not getattr(invitee, "id", None):
        return None
    if db.query(Referral).filter(Referral.invitee_user_id == invitee.id).first():
        return None
    referrer = resolve_referrer(db, raw_code)
    if not referrer:
        return None
    if referrer.id == invitee.id:
        return None
    rel = Referral(
        referrer_user_id=referrer.id,
        invitee_user_id=invitee.id,
        code=str(raw_code).strip().upper()[:32],
    )
    db.add(rel)
    return rel


def pending_referral_for(db: Session, invitee_user_id: int) -> Optional[Referral]:
    """仅返回尚未发放首单奖励的 referral 关系。"""
    return (
        db.query(Referral)
        .filter(
            Referral.invitee_user_id == invitee_user_id,
            Referral.first_task_reward_at.is_(None),
        )
        .first()
    )


def grant_first_task_reward(
    db: Session,
    *,
    invitee_user_id: int,
    trigger_task_id: Optional[int],
) -> Optional[Tuple[int, int]]:
    """对 `invitee_user_id` 发放首单返点（若未发放）。返回 (referrer_points, invitee_points) 或 None。

    幂等：使用 `Referral.first_task_reward_at is None` 作为锁列，同事务内只会写一次。
    调用方负责 `db.commit()`。
    """
    rel = pending_referral_for(db, invitee_user_id)
    if not rel:
        return None
    pts_ref = referrer_bonus_points()
    pts_inv = invitee_bonus_points()
    now = datetime.utcnow()

    if pts_ref > 0:
        try:
            referrer = db.query(User).filter(User.id == rel.referrer_user_id).with_for_update().first()
        except Exception:
            referrer = db.query(User).filter(User.id == rel.referrer_user_id).first()
        if referrer:
            referrer.credits = int(getattr(referrer, "credits", 0) or 0) + pts_ref
            db.add(CreditTransaction(
                user_id=referrer.id,
                amount=pts_ref,
                type="referral_bonus",
                ref_id=trigger_task_id,
                remark=f"邀请好友首单返点 {pts_ref} 点",
            ))
            rel.referrer_bonus_points = pts_ref

    if pts_inv > 0:
        try:
            invitee = db.query(User).filter(User.id == rel.invitee_user_id).with_for_update().first()
        except Exception:
            invitee = db.query(User).filter(User.id == rel.invitee_user_id).first()
        if invitee:
            invitee.credits = int(getattr(invitee, "credits", 0) or 0) + pts_inv
            db.add(CreditTransaction(
                user_id=invitee.id,
                amount=pts_inv,
                type="referral_bonus",
                ref_id=trigger_task_id,
                remark=f"通过邀请注册首单返点 {pts_inv} 点",
            ))
            rel.invitee_bonus_points = pts_inv

    rel.first_task_reward_at = now
    return (pts_ref, pts_inv)
