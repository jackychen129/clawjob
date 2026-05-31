"""Agent-to-agent direct settlement (platform orchestrates, agents pay each other)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.relational_db import Agent, Task

VALID_METHOD_TYPES = frozenset({"alipay", "wechat", "bank", "crypto", "custom"})
VALID_SETTLEMENT_STATUSES = frozenset({"pending", "paid", "disputed"})


def get_settlement_mode(task: Task) -> str:
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    mode = (extra.get("settlement_mode") or "platform_credits").strip()
    return mode if mode in ("platform_credits", "agent_direct") else "platform_credits"


def get_payment_profile(agent: Optional[Agent]) -> dict:
    if agent is None:
        return {"methods": []}
    cfg = agent.config if isinstance(agent.config, dict) else {}
    pp = cfg.get("payment_profile")
    if not isinstance(pp, dict):
        return {"methods": []}
    methods = pp.get("methods")
    if not isinstance(methods, list):
        return {"methods": []}
    return {"methods": [_sanitize_method(m) for m in methods if isinstance(m, dict)]}


def _sanitize_method(m: dict) -> dict:
    t = (m.get("type") or "custom").strip().lower()
    if t not in VALID_METHOD_TYPES:
        t = "custom"
    return {
        "type": t,
        "label": str(m.get("label") or t)[:64],
        "account_masked": str(m.get("account_masked") or "")[:64],
        "details_for_counterparty": str(m.get("details_for_counterparty") or "")[:2000],
        "webhook_url": str(m.get("webhook_url") or "")[:500] or None,
    }


def validate_payment_profile(body: dict) -> dict:
    methods_in = body.get("methods")
    if not isinstance(methods_in, list):
        raise HTTPException(status_code=400, detail="payment_profile.methods 须为数组")
    if len(methods_in) > 10:
        raise HTTPException(status_code=400, detail="最多 10 种收款方式")
    methods: List[dict] = []
    for raw in methods_in:
        if not isinstance(raw, dict):
            continue
        t = (raw.get("type") or "").strip().lower()
        if t not in VALID_METHOD_TYPES:
            raise HTTPException(status_code=400, detail=f"不支持的收款类型: {t}")
        details = str(raw.get("details_for_counterparty") or "").strip()
        if not details:
            raise HTTPException(status_code=400, detail="每种收款方式须提供 details_for_counterparty（对方打款所需信息）")
        methods.append(_sanitize_method({**raw, "type": t, "details_for_counterparty": details}))
    return {"methods": methods}


def set_agent_payment_profile(agent: Agent, profile: dict) -> None:
    cfg = dict(agent.config) if isinstance(agent.config, dict) else {}
    cfg["payment_profile"] = profile
    agent.config = cfg
    flag_modified(agent, "config")


def settlement_parties(task: Task, db: Session) -> Tuple[int, Optional[int]]:
    publisher_uid = int(task.owner_id)
    executor_uid: Optional[int] = None
    if task.agent_id:
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if agent:
            executor_uid = int(agent.owner_id)
    return publisher_uid, executor_uid


def can_view_agent_payment_profile(
    task: Optional[Task],
    agent: Agent,
    viewer_uid: int,
    db: Session,
) -> bool:
    if int(agent.owner_id) == viewer_uid:
        return True
    if task is None:
        return False
    pub_uid, exe_uid = settlement_parties(task, db)
    if viewer_uid == pub_uid and task.status in ("pending_verification", "completed", "in_progress"):
        return True
    if viewer_uid == exe_uid and task.agent_id == agent.id:
        return True
    from app.database.relational_db import TaskSubscription

    if db.query(TaskSubscription).filter(
        TaskSubscription.task_id == task.id,
        TaskSubscription.agent_id == agent.id,
    ).first():
        return viewer_uid in (pub_uid, exe_uid)
    return False


def get_settlement(task: Task) -> Optional[dict]:
    out = task.output_data if isinstance(task.output_data, dict) else {}
    s = out.get("settlement")
    return s if isinstance(s, dict) else None


def _write_settlement(task: Task, settlement: dict) -> None:
    base = dict(task.output_data) if isinstance(task.output_data, dict) else {}
    base["settlement"] = settlement
    task.output_data = base
    flag_modified(task, "output_data")


def create_settlement_on_confirm(task: Task, db: Session) -> dict:
    """After agent_direct confirm: create pending settlement record."""
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first() if task.agent_id else None
    payee_profile = get_payment_profile(agent)
    settlement = {
        "status": "pending",
        "settlement_mode": "agent_direct",
        "reward_points": int(getattr(task, "reward_points", 0) or 0),
        "payee_agent_id": int(task.agent_id) if task.agent_id else None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "payer_confirmed_at": None,
        "payee_confirmed_at": None,
        "method_used": None,
        "proof_links": [],
        "payer_note": None,
        "payee_profile_snapshot": payee_profile,
    }
    _write_settlement(task, settlement)
    return settlement


def require_settlement_party(task: Task, uid: int, db: Session) -> str:
    pub_uid, exe_uid = settlement_parties(task, db)
    if uid == pub_uid:
        return "publisher"
    if exe_uid is not None and uid == exe_uid:
        return "executor"
    raise HTTPException(status_code=403, detail="仅任务发布方或执行方 Agent 拥有者可操作结算")


def serialize_settlement_view(task: Task, db: Session, viewer_uid: int) -> dict:
    settlement = get_settlement(task)
    if settlement is None and get_settlement_mode(task) != "agent_direct":
        raise HTTPException(status_code=404, detail="该任务无 Agent 直接结算记录")
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first() if task.agent_id else None
    payee_profile = get_payment_profile(agent)
    if settlement and settlement.get("payee_profile_snapshot"):
        payee_profile = settlement["payee_profile_snapshot"]
    role = require_settlement_party(task, viewer_uid, db)
    return {
        "task_id": task.id,
        "task_status": task.status,
        "settlement_mode": get_settlement_mode(task),
        "reward_points": int(getattr(task, "reward_points", 0) or 0),
        "settlement": settlement,
        "payee_profile": payee_profile,
        "viewer_role": role,
        "instructions_zh": (
            "发布方 Agent 向执行方配置的收款方式打款后，调用 payer-mark-paid；"
            "执行方确认到账后调用 payee-confirm。"
        ),
    }


def payer_mark_paid(
    task: Task,
    db: Session,
    uid: int,
    *,
    proof_links: Optional[List[str]] = None,
    note: str = "",
    method_used: Optional[str] = None,
) -> dict:
    require_settlement_party(task, uid, db)
    pub_uid, _ = settlement_parties(task, db)
    if uid != pub_uid:
        raise HTTPException(status_code=403, detail="仅发布方可标记已打款")
    settlement = get_settlement(task)
    if settlement is None:
        raise HTTPException(status_code=400, detail="任务尚无结算记录")
    if settlement.get("status") == "paid":
        return settlement
    links = [str(x).strip()[:500] for x in (proof_links or []) if str(x).strip()][:10]
    settlement = {
        **settlement,
        "payer_confirmed_at": datetime.utcnow().isoformat() + "Z",
        "proof_links": links,
        "payer_note": (note or "")[:1000],
        "method_used": (method_used or settlement.get("method_used") or "")[:64] or None,
    }
    _write_settlement(task, settlement)
    return settlement


def payee_confirm_received(task: Task, db: Session, uid: int) -> dict:
    require_settlement_party(task, uid, db)
    _, exe_uid = settlement_parties(task, db)
    if exe_uid is None or uid != exe_uid:
        raise HTTPException(status_code=403, detail="仅执行方 Agent 拥有者可确认收款")
    settlement = get_settlement(task)
    if settlement is None:
        raise HTTPException(status_code=400, detail="任务尚无结算记录")
    if settlement.get("status") == "paid":
        return settlement
    if not settlement.get("payer_confirmed_at"):
        raise HTTPException(status_code=400, detail="请等待发布方标记已打款后再确认收款")
    settlement = {
        **settlement,
        "status": "paid",
        "payee_confirmed_at": datetime.utcnow().isoformat() + "Z",
    }
    _write_settlement(task, settlement)
    return settlement
