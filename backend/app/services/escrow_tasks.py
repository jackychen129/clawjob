"""
托管（Escrow）MVP：里程碑分阶段验收与放款计划。

计划存于 Task.input_data['escrow']，与现有 6 小时自动验收逻辑对齐：
每个里程碑提交后进入 pending_verification，超时自动确认该里程碑并放款。
"""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.relational_db import Agent, CreditTransaction, Task, User, UserCommissionRecord


PLATFORM_COMMISSION_RATE = 0.01  # 与 main.py 保持一致，分阶段按点数计提


def get_escrow(task: Task) -> Optional[Dict[str, Any]]:
    d = task.input_data if isinstance(getattr(task, "input_data", None), dict) else {}
    esc = d.get("escrow")
    return esc if isinstance(esc, dict) and esc.get("milestones") else None


def build_escrow_plan(milestones_in: List[Dict[str, Any]], reward_points: int) -> Dict[str, Any]:
    """根据权重拆分里程碑点数，权重之和须为 1。"""
    if reward_points <= 0:
        raise ValueError("托管任务须设置大于 0 的奖励点")
    if not milestones_in or len(milestones_in) < 2:
        raise ValueError("托管模式至少需要 2 个里程碑（否则请使用普通单阶段任务）")
    if len(milestones_in) > 10:
        raise ValueError("里程碑数量不能超过 10")

    titles: List[str] = []
    weights: List[float] = []
    acceptance_criteria: List[str] = []
    for m in milestones_in:
        title = (m.get("title") or "").strip()
        if not title:
            raise ValueError("里程碑标题不能为空")
        w = float(m.get("weight", 0) or 0)
        criteria = (m.get("acceptance_criteria") or "").strip()
        weights.append(w)
        titles.append(title[:200])
        acceptance_criteria.append(criteria[:2000])

    s = sum(weights)
    if abs(s - 1.0) > 0.001:
        raise ValueError(f"里程碑权重之和须为 1，当前为 {s:.4f}")

    points: List[int] = []
    allocated = 0
    for i, w in enumerate(weights[:-1]):
        p = int(round(reward_points * w))
        points.append(p)
        allocated += p
    points.append(max(0, reward_points - allocated))

    ms = []
    for i, title in enumerate(titles):
        ms.append({
            "title": title,
            "weight": weights[i],
            "points": points[i],
            "acceptance_criteria": acceptance_criteria[i],
        })

    return {
        "milestones": ms,
        "current_index": 0,
        "released_points": 0,
        "disputed": False,
        "dispute_reason": None,
    }


def escrow_milestone_points_at(escrow: Dict[str, Any], index: int) -> int:
    ms = escrow.get("milestones") or []
    if index < 0 or index >= len(ms):
        return 0
    return int(ms[index].get("points", 0) or 0)


def save_escrow_to_task(task: Task, escrow: Dict[str, Any]) -> None:
    base = copy.deepcopy(task.input_data) if isinstance(task.input_data, dict) else {}
    base["escrow"] = copy.deepcopy(escrow)
    task.input_data = base
    try:
        flag_modified(task, "input_data")
    except Exception:
        pass


def credit_executor_points(
    task: Task,
    db: Session,
    points: int,
    remark: str,
) -> Tuple[int, int]:
    """
    向接取方发放指定点数（扣佣金）。返回 (amount_to_executor, commission).
    """
    if points <= 0 or not task.agent_id:
        return 0, 0
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
    if not agent:
        return 0, 0
    receiver = db.query(User).filter(User.id == agent.owner_id).first()
    if not receiver:
        return 0, 0
    commission = int(points * PLATFORM_COMMISSION_RATE)
    amount_to_receiver = points - commission
    receiver.credits = (getattr(receiver, "credits", 0) or 0) + amount_to_receiver
    db.add(
        CreditTransaction(
            user_id=agent.owner_id,
            amount=amount_to_receiver,
            type="task_reward",
            ref_id=task.id,
            remark=remark,
        )
    )
    if commission > 0 and task.owner_id:
        publisher = db.query(User).filter(User.id == task.owner_id).first()
        if publisher:
            publisher.commission_balance = (getattr(publisher, "commission_balance", 0) or 0) + commission
            db.add(
                UserCommissionRecord(
                    user_id=task.owner_id,
                    amount=commission,
                    task_id=task.id,
                    remark=f"任务 #{task.id} 托管里程碑佣金",
                )
            )
    return amount_to_receiver, commission


def apply_escrow_milestone_confirm(
    task: Task,
    db: Session,
    *,
    auto: bool = False,
) -> Dict[str, Any]:
    """
    在 pending_verification 状态下确认当前里程碑：部分放款或整单完成。
    调用方须已校验任务为 escrow 且状态为 pending_verification。
    """
    escrow = get_escrow(task)
    if not escrow:
        raise RuntimeError("非托管任务")

    idx = int(escrow.get("current_index", 0) or 0)
    ms = escrow.get("milestones") or []
    if idx >= len(ms):
        raise RuntimeError("里程碑索引异常")

    pts = escrow_milestone_points_at(escrow, idx)
    remark = (
        f"任务 #{task.id} 托管里程碑 {idx + 1}/{len(ms)} 放款 {pts} 点"
        + ("（超时自动验收）" if auto else "")
    )
    amount_ex, commission = credit_executor_points(task, db, pts, remark)

    escrow["released_points"] = int(escrow.get("released_points", 0) or 0) + pts

    if idx >= len(ms) - 1:
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.submitted_at = None
        task.verification_deadline_at = None
    else:
        escrow["current_index"] = idx + 1
        task.status = "in_progress"
        task.submitted_at = None
        task.verification_deadline_at = None
        base = task.output_data if isinstance(task.output_data, dict) else {}
        task.output_data = {
            **base,
            "last_milestone_confirmed_at": datetime.utcnow().isoformat() + "Z",
            "milestone_confirmed_index": idx,
        }

    save_escrow_to_task(task, escrow)

    return {
        "milestone_index": idx,
        "reward_paid": amount_ex,
        "commission": commission,
        "escrow_finished": idx >= len(ms) - 1,
    }
