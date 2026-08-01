"""任务候选人推荐：基于技能匹配 + 信誉分 + 历史价位相近度。"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task
from app.services.reputation import compute_bulk_reputations


_MAX_POOL = 200


def _collect_candidate_agents(
    db: Session,
    query,
    *,
    task: Task,
    task_token: Optional[str],
    max_pool: int = _MAX_POOL,
) -> List[Agent]:
    """构建候选 Agent 池：优先 skill token / 同类目历史，再按 id 倒序补齐。"""
    seen: Dict[int, Agent] = {}
    category = getattr(task, "category", None)

    if task_token:
        for agent in query.all():
            if _agent_skill_token(agent) == task_token:
                seen[agent.id] = agent

    if category:
        hist_ids = [
            int(aid)
            for (aid,) in (
                db.query(Task.agent_id)
                .filter(
                    Task.status == "completed",
                    Task.category == category,
                    Task.agent_id.isnot(None),
                )
                .distinct()
                .limit(max_pool)
                .all()
            )
            if aid is not None
        ]
        if hist_ids:
            for agent in query.filter(Agent.id.in_(hist_ids)).all():
                seen[agent.id] = agent

    if len(seen) < max_pool:
        for agent in query.order_by(Agent.id.desc()).limit(max_pool).all():
            seen.setdefault(agent.id, agent)
            if len(seen) >= max_pool:
                break

    return list(seen.values())


def _task_skill_token(task: Task) -> Optional[str]:
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    if not isinstance(extra, dict):
        return None
    tok = extra.get("related_skill_token")
    if not tok:
        return None
    return str(tok).strip() or None


def _task_skills(task: Task) -> List[str]:
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    out: List[str] = []
    if isinstance(extra, dict):
        for s in extra.get("skills") or []:
            s = str(s).strip()
            if s:
                out.append(s)
    cat = getattr(task, "category", None)
    if cat:
        out.append(str(cat).strip())
    return out


def _agent_skill_token(agent: Agent) -> Optional[str]:
    cfg = agent.config or {}
    if not isinstance(cfg, dict):
        return None
    tok = cfg.get("skill_bound_token")
    if not tok:
        return None
    return str(tok).strip() or None


def _agent_median_price(db: Session, agent_id: int, *, min_samples: int = 1) -> Optional[int]:
    rows = (
        db.query(Task.reward_points)
        .filter(
            Task.status == "completed",
            Task.agent_id == agent_id,
            Task.reward_points.isnot(None),
            Task.reward_points > 0,
        )
        .order_by(Task.completed_at.desc())
        .limit(20)
        .all()
    )
    prices = [int(p) for (p,) in rows if p is not None]
    if len(prices) < max(1, min_samples):
        return None
    return int(statistics.median(prices))


def _suggested_price(
    db: Session,
    *,
    category: Optional[str],
    reward_points: int,
    agent_id: int,
) -> int:
    own = _agent_median_price(db, agent_id, min_samples=3)
    if own is not None:
        return max(1, own)
    scope = db.query(Task.reward_points).filter(
        Task.status == "completed",
        Task.reward_points.isnot(None),
        Task.reward_points > 0,
    )
    if category:
        scope = scope.filter(Task.category == category)
    scope = scope.order_by(Task.completed_at.desc()).limit(50)
    prices = [int(p) for (p,) in scope.all() if p is not None]
    if not prices:
        return int(reward_points or 0)
    return max(1, int(statistics.median(prices)))


def _price_fit_score(task_reward: int, agent_median_price: Optional[int]) -> int:
    if not task_reward or task_reward <= 0:
        return 0
    if not agent_median_price or agent_median_price <= 0:
        return 0
    lo, hi = sorted((float(task_reward), float(agent_median_price)))
    ratio = lo / hi if hi > 0 else 0.0
    return int(round(20 * ratio))


def _score_candidate(
    card: Dict[str, Any],
    *,
    task_skill_token: Optional[str],
    task_skills: List[str],
    task_reward: int = 0,
    agent_median_price: Optional[int] = None,
) -> Dict[str, Any]:
    base = int(card.get("reputation_score", 60))
    breakdown = {
        "reputation": base,
        "skill_token": 0,
        "skill_overlap": 0,
        "recent_activity": 0,
        "price_fit": 0,
    }
    bonus = 0

    agent_token = card["agent"].get("skill_token")
    if task_skill_token and agent_token and agent_token == task_skill_token:
        breakdown["skill_token"] = 50
        bonus += 50

    if task_skills:
        top = {s.lower() for s in (card["stats"].get("top_skills") or [])}
        overlap = sum(1 for s in task_skills if s and s.lower() in top)
        if overlap:
            v = min(20, overlap * 10)
            breakdown["skill_overlap"] = v
            bonus += v

    recent = int(card["stats"].get("recent_30d_completed_count") or 0)
    if recent > 0:
        v = min(10, recent * 2)
        breakdown["recent_activity"] = v
        bonus += v

    price_fit = _price_fit_score(int(task_reward or 0), agent_median_price)
    if price_fit > 0:
        breakdown["price_fit"] = price_fit
        bonus += price_fit

    return {
        "total_score": base + bonus,
        "breakdown": breakdown,
    }


def recommend_candidates_for_task(
    db: Session,
    task_id: int,
    *,
    k: int = 5,
    exclude_owner_id: Optional[int] = None,
) -> Dict[str, Any]:
    task = db.query(Task).filter(Task.id == int(task_id)).first()
    if not task:
        raise ValueError("task_not_found")

    k = max(1, min(20, int(k or 5)))
    task_token = _task_skill_token(task)
    task_skills = _task_skills(task)

    query = db.query(Agent).filter(Agent.is_active == True, Agent.is_public == True)  # noqa: E712
    if exclude_owner_id is not None:
        query = query.filter(Agent.owner_id != int(exclude_owner_id))
    invited = getattr(task, "invited_agent_ids", None)
    if invited and isinstance(invited, list) and invited:
        invited_ids = [int(x) for x in invited if x is not None]
        if invited_ids:
            query = query.filter(Agent.id.in_(invited_ids))

    candidates_all = _collect_candidate_agents(
        db,
        query,
        task=task,
        task_token=task_token,
        max_pool=_MAX_POOL,
    )

    reward_points = int(getattr(task, "reward_points", 0) or 0)
    agent_ids = [a.id for a in candidates_all]
    rep_map = compute_bulk_reputations(db, agent_ids)

    cards: List[Dict[str, Any]] = []
    for a in candidates_all:
        card = rep_map.get(a.id)
        if not card:
            continue
        agent_median = _agent_median_price(db, a.id, min_samples=1)
        match = _score_candidate(
            card,
            task_skill_token=task_token,
            task_skills=task_skills,
            task_reward=reward_points,
            agent_median_price=agent_median,
        )
        price = _suggested_price(
            db,
            category=getattr(task, "category", None),
            reward_points=reward_points,
            agent_id=a.id,
        )
        cards.append({
            "agent": card["agent"],
            "stats": card["stats"],
            "reputation_score": card["reputation_score"],
            "match": match,
            "suggested_price": price,
            "agent_median_price": agent_median,
        })

    def _sort_key(item: Dict[str, Any]) -> tuple:
        fp = item["stats"].get("first_pass_confirm_rate")
        has_record = item["stats"]["accepted_task_count"] > 0
        tier = 0 if (has_record and (fp or 0) >= 0.8) else 1
        return (tier, -item["match"]["total_score"])

    cards.sort(key=_sort_key)
    top = cards[:k]

    return {
        "task_id": task.id,
        "task": {
            "title": task.title,
            "skill_token": task_token,
            "category": getattr(task, "category", None),
            "reward_points": reward_points,
            "skills": task_skills,
        },
        "candidates": top,
        "total_evaluated": len(cards),
    }
