"""任务雷达（Task Radar）：面向 Agent 的实时撮合评分服务。

语义：给定一个 Agent，聚合出一批「值得接取」的开放任务，按综合匹配度打分并返回 Top-K。

评分因子（0-100 基线 + 可调权重）：
- skill_match：Agent 绑定的 Skill 与任务 `related_skill_token` 相同 → 满分；否则看任务 `skills` ∩ Agent 最近擅长的 top_skills。
- reward_fit：任务奖励相对同类中位数的百分位（价位越接近或更高 → 分越高）。
- freshness：任务发布时间越新分越高（24h 内满分，指数衰减）。
- history_affinity：Agent 完成过该 `skill_token` / `category` 的任务数。
- invited_boost：若是被邀请的定向任务 → +20 绝对分，强曝光。

最终分 = Σ(w_i * factor_i) / Σ(w_i)；clamp 到 [0, 100]，并输出 breakdown 供前端展示。

排除规则：
- 任务状态必须是 `open`；`agent_id` 为空；未提交验收。
- 发布者 ≠ Agent 拥有者（禁止左手倒右手）。
- 若任务是 `invitees_only`，Agent 必须在 `invited_agent_ids`。
- Agent 必须 `is_active`。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task, User
from app.services.reputation import compute_agent_reputation


DEFAULT_WEIGHTS: Dict[str, float] = {
    "skill_match": 0.40,
    "reward_fit": 0.25,
    "freshness": 0.15,
    "history_affinity": 0.20,
}


@dataclass
class _TaskSnapshot:
    task: Task
    title: str
    skills: List[str]
    skill_token: Optional[str]
    category: Optional[str]
    reward_points: int
    created_at: Optional[datetime]
    is_invited: bool


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _normalize_weights(user_weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    w = dict(DEFAULT_WEIGHTS)
    if user_weights:
        for k in list(w.keys()):
            v = user_weights.get(k)
            if v is None:
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if fv < 0:
                fv = 0.0
            if fv > 5.0:
                fv = 5.0
            w[k] = fv
    total = sum(w.values()) or 1.0
    return {k: v / total for k, v in w.items()}


def _task_extra(task: Task) -> Dict[str, Any]:
    return task.input_data if isinstance(task.input_data, dict) else {}


def _task_skills(task: Task) -> List[str]:
    out: List[str] = []
    extra = _task_extra(task)
    if isinstance(extra.get("skills"), list):
        for s in extra["skills"]:
            s_str = str(s).strip()
            if s_str:
                out.append(s_str)
    cat = getattr(task, "category", None)
    if cat and str(cat).strip():
        out.append(str(cat).strip())
    return out


def _task_skill_token(task: Task) -> Optional[str]:
    extra = _task_extra(task)
    tok = extra.get("related_skill_token") if isinstance(extra, dict) else None
    return str(tok).strip() or None if tok else None


def _agent_skill_token(agent: Agent) -> Optional[str]:
    cfg = agent.config if isinstance(agent.config, dict) else {}
    tok = cfg.get("skill_bound_token") if isinstance(cfg, dict) else None
    return str(tok).strip() or None if tok else None


def _median(values: Iterable[int]) -> Optional[float]:
    vs = sorted([v for v in values if v is not None and v > 0])
    if not vs:
        return None
    n = len(vs)
    mid = n // 2
    if n % 2:
        return float(vs[mid])
    return (vs[mid - 1] + vs[mid]) / 2.0


def _score_skill_match(snap: _TaskSnapshot, *, agent_token: Optional[str], top_skills: List[str]) -> float:
    if snap.skill_token and agent_token and snap.skill_token == agent_token:
        return 1.0
    if not snap.skills:
        return 0.1 if agent_token is None else 0.05
    top_lc = {s.lower() for s in top_skills if s}
    hits = sum(1 for s in snap.skills if s.lower() in top_lc)
    if hits == 0:
        return 0.0
    return _clamp01(0.5 + hits * 0.15)


def _score_reward_fit(snap: _TaskSnapshot, *, category_median: Optional[float]) -> float:
    if snap.reward_points <= 0:
        return 0.1
    if category_median is None or category_median <= 0:
        return 0.6
    ratio = snap.reward_points / category_median
    if ratio >= 1.2:
        return 1.0
    if ratio >= 1.0:
        return 0.85
    if ratio >= 0.8:
        return 0.7
    if ratio >= 0.6:
        return 0.5
    return 0.3


def _score_freshness(snap: _TaskSnapshot, *, now: datetime) -> float:
    if not isinstance(snap.created_at, datetime):
        return 0.3
    delta_h = (now - snap.created_at).total_seconds() / 3600.0
    if delta_h < 0:
        return 1.0
    if delta_h <= 24:
        return 1.0 - (delta_h / 24) * 0.25
    if delta_h <= 72:
        return 0.75 - ((delta_h - 24) / 48) * 0.25
    if delta_h <= 168:
        return 0.50 - ((delta_h - 72) / 96) * 0.25
    return 0.2


def _score_history_affinity(snap: _TaskSnapshot, *, agent_token_completed: int, agent_category_completed: int) -> float:
    tok_bonus = 0.0
    if snap.skill_token:
        tok_bonus = min(1.0, agent_token_completed / 5.0)
    cat_bonus = 0.0
    if snap.category:
        cat_bonus = min(1.0, agent_category_completed / 5.0)
    if snap.skill_token and snap.category:
        return _clamp01((tok_bonus * 0.7) + (cat_bonus * 0.3))
    if snap.skill_token:
        return tok_bonus
    if snap.category:
        return cat_bonus
    return 0.4


def _build_reason(breakdown: Dict[str, float], snap: _TaskSnapshot) -> List[str]:
    out: List[str] = []
    if breakdown.get("skill_match", 0) >= 0.95:
        out.append("skill_token_exact_match")
    elif breakdown.get("skill_match", 0) >= 0.5:
        out.append("skill_overlap_high")
    if breakdown.get("reward_fit", 0) >= 0.85:
        out.append("reward_above_market")
    if breakdown.get("freshness", 0) >= 0.85:
        out.append("fresh_within_24h")
    if breakdown.get("history_affinity", 0) >= 0.8:
        out.append("domain_expert")
    if snap.is_invited:
        out.append("invited_by_publisher")
    return out


def compute_task_radar(
    db: Session,
    agent_id: int,
    *,
    k: int = 10,
    weights: Optional[Dict[str, float]] = None,
    reward_min: Optional[int] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """主入口：对一个 Agent 计算 Task Radar 排名。

    返回：
    {
        "agent_id": int,
        "weights": 归一化后的权重,
        "total_pool": int,      # 进入评分的任务数
        "radar": [ {task:{...}, score, breakdown:{...}, reasons:[...], suggested_bid:int} ]
    }

    若 Agent 不存在 → ValueError('agent_not_found')。
    """
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        raise ValueError("agent_not_found")

    owner_id = int(agent.owner_id)
    effective_weights = _normalize_weights(weights)
    k = max(1, min(50, int(k or 10)))
    agent_token = _agent_skill_token(agent)

    # NOTE: Agent 的 top_skills 依赖信誉卡（失败时退化为空）
    try:
        rep = compute_agent_reputation(db, agent.id) or {}
    except Exception:
        rep = {}
    top_skills = list((rep.get("stats") or {}).get("top_skills") or [])
    reputation_score = int(rep.get("reputation_score") or 60)

    # NOTE: Agent 历史契合度基数
    agent_token_completed = 0
    agent_category_completed: Dict[str, int] = {}
    if agent_token:
        try:
            # NOTE: 使用 raw SQL JSON 过滤不便，这里走 Python 过滤已完成任务
            done_tasks = (
                db.query(Task)
                .filter(Task.agent_id == agent.id, Task.status == "completed")
                .limit(500)
                .all()
            )
        except Exception:
            done_tasks = []
        for t in done_tasks:
            tok = _task_skill_token(t)
            if tok and tok == agent_token:
                agent_token_completed += 1
            cat = getattr(t, "category", None)
            if cat:
                key = str(cat).strip()
                if key:
                    agent_category_completed[key] = agent_category_completed.get(key, 0) + 1

    # NOTE: 拉取候选任务池；限制 300 条上限防超时
    query = db.query(Task).filter(
        Task.status == "open",
        Task.agent_id.is_(None),
        Task.submitted_at.is_(None),
        Task.owner_id != owner_id,
    )
    if reward_min is not None and reward_min > 0:
        query = query.filter(Task.reward_points >= int(reward_min))
    if category:
        query = query.filter(Task.category == category.strip()[:64])
    tasks: List[Task] = query.order_by(Task.created_at.desc()).limit(300).all()

    # NOTE: 相似任务的奖励中位数（按 category 聚合一次）
    category_medians: Dict[str, float] = {}
    try:
        for cat in {getattr(t, "category", None) for t in tasks if getattr(t, "category", None)}:
            rows = (
                db.query(Task.reward_points)
                .filter(
                    Task.status == "completed",
                    Task.category == cat,
                    Task.reward_points.isnot(None),
                    Task.reward_points > 0,
                )
                .order_by(Task.completed_at.desc())
                .limit(80)
                .all()
            )
            m = _median(int(r[0]) for r in rows)
            if m is not None:
                category_medians[cat] = m
    except Exception:
        pass

    now = datetime.utcnow()

    scored: List[Dict[str, Any]] = []
    for t in tasks:
        # NOTE: 可见性（定向任务）
        extra = _task_extra(t)
        visibility = extra.get("visibility") if isinstance(extra, dict) else None
        invited = [int(x) for x in (getattr(t, "invited_agent_ids", None) or []) if x is not None]
        is_invited = agent.id in invited
        if visibility == "invitees_only" and not is_invited:
            continue

        snap = _TaskSnapshot(
            task=t,
            title=t.title or "",
            skills=_task_skills(t),
            skill_token=_task_skill_token(t),
            category=(getattr(t, "category", None) or None),
            reward_points=int(getattr(t, "reward_points", 0) or 0),
            created_at=getattr(t, "created_at", None),
            is_invited=is_invited,
        )
        cat_median = category_medians.get(snap.category) if snap.category else None
        tok_done = agent_token_completed
        cat_done = agent_category_completed.get(snap.category or "", 0)

        breakdown = {
            "skill_match": round(_score_skill_match(snap, agent_token=agent_token, top_skills=top_skills), 4),
            "reward_fit": round(_score_reward_fit(snap, category_median=cat_median), 4),
            "freshness": round(_score_freshness(snap, now=now), 4),
            "history_affinity": round(_score_history_affinity(snap, agent_token_completed=tok_done, agent_category_completed=cat_done), 4),
        }
        weighted = sum(breakdown[k_] * effective_weights.get(k_, 0) for k_ in breakdown)
        score = round(weighted * 100.0, 2)
        if snap.is_invited:
            score = min(100.0, score + 20.0)

        suggested_bid = snap.reward_points
        if cat_median:
            suggested_bid = max(1, int(round(min(snap.reward_points, cat_median))))

        scored.append({
            "task": {
                "id": t.id,
                "title": snap.title,
                "description": (t.description or "")[:200],
                "category": snap.category,
                "skills": snap.skills,
                "skill_token": snap.skill_token,
                "reward_points": snap.reward_points,
                "created_at": snap.created_at.isoformat() if isinstance(snap.created_at, datetime) else None,
                "owner_id": t.owner_id,
                "invited_for_me": snap.is_invited,
                "visibility": visibility or "public",
            },
            "score": score,
            "breakdown": breakdown,
            "reasons": _build_reason(breakdown, snap),
            "suggested_bid": suggested_bid,
        })

    scored.sort(key=lambda x: (-(x["task"]["invited_for_me"]), -x["score"]))
    top = scored[:k]

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "agent_reputation_score": reputation_score,
        "weights": effective_weights,
        "total_pool": len(scored),
        "radar": top,
    }
