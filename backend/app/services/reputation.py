"""Agent 信誉卡（Reputation Card）聚合服务。

对外暴露 `compute_agent_reputation(db, agent_id)`，不写库，不引入新表；
所有指标都基于已有 `Task` / `CreditTransaction` 等模型即时计算。

输出字段定义详见 `compute_agent_reputation` 文档字符串。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task, User


_DISPUTE_KEY = "disputed"  # Task.input_data["escrow"]["disputed"]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _agent_skill_token(agent: Agent) -> Optional[str]:
    cfg = agent.config or {}
    if not isinstance(cfg, dict):
        return None
    tok = cfg.get("skill_bound_token")
    if not tok:
        return None
    return str(tok).strip() or None


def _collect_top_skills(tasks: List[Task], limit: int = 3) -> List[str]:
    bag: Counter[str] = Counter()
    for t in tasks:
        extra = t.input_data if isinstance(t.input_data, dict) else {}
        skills = extra.get("skills") if isinstance(extra, dict) else None
        if isinstance(skills, list):
            for s in skills:
                s_str = str(s).strip()
                if s_str:
                    bag[s_str] += 1
        cat = getattr(t, "category", None)
        if cat:
            bag[str(cat).strip()] += 1
    return [name for name, _ in bag.most_common(limit)]


def _reputation_score(
    *,
    completed: int,
    accepted: int,
    rejection_count: int,
    dispute_count: int,
    first_pass_confirm_rate: Optional[float],
    avg_completion_hours: Optional[float],
    recent_30d_completed: int,
) -> int:
    """综合评分：0–100。无完成记录时保持 60 中位数，避免新人被压到底。

    公式（设计目标：给验收通过率 + 活跃度 + 争议率权重）：
    - 基础：60
    - 首过验收率：+ up to 30（100% → +30）
    - 近 30 天活跃：+ up to 10（5 单以上 +10，线性缩放）
    - 争议扣分：- dispute_rate * 25
    - 拒绝扣分：- rejection_rate * 15
    - 速度加分：完成均值 < 24h +5，<72h +3
    最终 clamp 到 [0, 100]。
    """
    if accepted == 0:
        return 60
    score = 60.0
    if first_pass_confirm_rate is not None:
        score += first_pass_confirm_rate * 30.0
    active_bonus = min(10.0, (recent_30d_completed / 5.0) * 10.0)
    score += active_bonus
    denom = max(accepted, 1)
    dispute_rate = dispute_count / denom
    rejection_rate = rejection_count / denom
    score -= dispute_rate * 25.0
    score -= rejection_rate * 15.0
    if avg_completion_hours is not None:
        if avg_completion_hours < 24:
            score += 5.0
        elif avg_completion_hours < 72:
            score += 3.0
    return max(0, min(100, int(round(score))))


def compute_agent_reputation(db: Session, agent_id: int) -> Optional[Dict[str, Any]]:
    """计算 Agent 信誉卡。若 Agent 不存在返回 None。

    返回结构（JSON 友好）：
    {
        "agent": {id, name, description, agent_type, category, skill_token, owner: {...}, created_at},
        "stats": {
            "accepted_task_count",
            "completed_task_count",
            "rejection_count",
            "dispute_count",
            "rejection_rate", "dispute_rate", "first_pass_confirm_rate",
            "reward_points_total",
            "avg_completion_hours",
            "recent_30d_completed_count",
            "recent_90d_completed_count",
            "last_active_at",
            "top_skills": [...],
        },
        "reputation_score": 0-100,
    }
    """
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        return None

    owner: Optional[User] = db.query(User).filter(User.id == agent.owner_id).first()

    # NOTE: 所有被该 agent 接取的任务（无论状态）
    accepted_tasks: List[Task] = (
        db.query(Task).filter(Task.agent_id == agent.id).all()
    )
    accepted_count = len(accepted_tasks)

    completed_tasks = [t for t in accepted_tasks if t.status == "completed"]
    completed_count = len(completed_tasks)

    # NOTE: 通过 timeline 事件中的 rejected 关键字累计拒绝次数；
    # 若没有 timeline 或缺少事件，则保留 0，避免误判。
    rejection_count = 0
    dispute_count = 0
    completion_durations_hours: List[float] = []
    last_active_at: Optional[datetime] = None
    reward_points_total = 0

    for t in accepted_tasks:
        extra = t.input_data if isinstance(t.input_data, dict) else {}
        if isinstance(extra, dict):
            escrow = extra.get("escrow") if isinstance(extra.get("escrow"), dict) else None
            if escrow and escrow.get(_DISPUTE_KEY):
                dispute_count += 1
            timeline = extra.get("timeline") if isinstance(extra.get("timeline"), list) else []
            for ev in timeline:
                if not isinstance(ev, dict):
                    continue
                kind = str(ev.get("kind") or ev.get("event") or "").lower()
                if kind in {"rejected", "reject", "verification_rejected"}:
                    rejection_count += 1
        if t.status == "completed":
            reward_points_total += _safe_int(getattr(t, "reward_points", 0))
            created = getattr(t, "created_at", None)
            completed = getattr(t, "completed_at", None)
            if isinstance(created, datetime) and isinstance(completed, datetime):
                delta = completed - created
                if delta.total_seconds() > 0:
                    completion_durations_hours.append(delta.total_seconds() / 3600.0)
            ts = completed or getattr(t, "updated_at", None) or getattr(t, "created_at", None)
            if isinstance(ts, datetime) and (last_active_at is None or ts > last_active_at):
                last_active_at = ts
        else:
            ts = getattr(t, "updated_at", None) or getattr(t, "created_at", None)
            if isinstance(ts, datetime) and (last_active_at is None or ts > last_active_at):
                last_active_at = ts

    avg_completion_hours: Optional[float] = None
    if completion_durations_hours:
        avg_completion_hours = round(sum(completion_durations_hours) / len(completion_durations_hours), 2)

    now = datetime.utcnow()
    d30 = now - timedelta(days=30)
    d90 = now - timedelta(days=90)
    recent_30 = sum(1 for t in completed_tasks if isinstance(t.completed_at, datetime) and t.completed_at >= d30)
    recent_90 = sum(1 for t in completed_tasks if isinstance(t.completed_at, datetime) and t.completed_at >= d90)

    denom = max(completed_count, 1)
    first_pass_rate: Optional[float] = None
    if completed_count > 0:
        first_pass_rate = round(max(0.0, (completed_count - rejection_count) / denom), 4)

    accepted_denom = max(accepted_count, 1)
    rejection_rate = round(rejection_count / accepted_denom, 4) if accepted_count else 0.0
    dispute_rate = round(dispute_count / accepted_denom, 4) if accepted_count else 0.0

    top_skills = _collect_top_skills(completed_tasks or accepted_tasks)

    score = _reputation_score(
        completed=completed_count,
        accepted=accepted_count,
        rejection_count=rejection_count,
        dispute_count=dispute_count,
        first_pass_confirm_rate=first_pass_rate,
        avg_completion_hours=avg_completion_hours,
        recent_30d_completed=recent_30,
    )

    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description or "",
            "agent_type": agent.agent_type or "general",
            "category": getattr(agent, "category", None) or "api",
            "skill_token": _agent_skill_token(agent),
            "owner": {
                "id": owner.id if owner else None,
                "username": owner.username if owner else None,
                "joined_at": owner.created_at.isoformat() if owner and getattr(owner, "created_at", None) else None,
            },
            "is_active": bool(agent.is_active),
            "created_at": agent.created_at.isoformat() if getattr(agent, "created_at", None) else None,
        },
        "stats": {
            "accepted_task_count": accepted_count,
            "completed_task_count": completed_count,
            "rejection_count": rejection_count,
            "dispute_count": dispute_count,
            "rejection_rate": rejection_rate,
            "dispute_rate": dispute_rate,
            "first_pass_confirm_rate": first_pass_rate,
            "reward_points_total": reward_points_total,
            "avg_completion_hours": avg_completion_hours,
            "recent_30d_completed_count": recent_30,
            "recent_90d_completed_count": recent_90,
            "last_active_at": last_active_at.isoformat() if isinstance(last_active_at, datetime) else None,
            "top_skills": top_skills,
        },
        "reputation_score": score,
    }


def compute_bulk_reputations(db: Session, agent_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """为多个 Agent 计算信誉卡，返回 {agent_id: card}。未命中的 agent 自动跳过。"""
    out: Dict[int, Dict[str, Any]] = {}
    for aid in agent_ids:
        try:
            card = compute_agent_reputation(db, int(aid))
        except Exception:
            card = None
        if card is not None:
            out[int(aid)] = card
    return out
