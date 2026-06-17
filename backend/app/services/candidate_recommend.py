"""任务候选人推荐：基于技能匹配 + 信誉分 + 历史价位相近度。

入口 `recommend_candidates_for_task(db, task_id, k)`：
- 仅用 `tasks`、`agents`、`published_skills` 三张已有表，不引入新模型。
- 评分纯本地计算，可在秒级返回（一次 SQL 拉候选池，再逐个打分）。
- 与 `reputation.compute_agent_reputation` 共享指标计算，信誉分可直接复用。
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task, User
from app.services.reputation import compute_agent_reputation


_MAX_POOL = 200  # 候选池上限，避免 O(N*M) 拖慢响应


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
    """Agent 自身最近完成任务的中位奖励价；样本不足返回 None（不蹭全局价）。"""
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
    """优先用 Agent 自身历史中位价（≥3 单），否则回退同类目/全局中位，再回退任务 reward。"""
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
    """历史价位相近度（0–20）：任务奖励与 Agent 历史中位价越接近分越高。

    任务无奖励或 Agent 无历史价位时返回 0（中性，不加不减），避免无经验 Agent 蹭分。
    """
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
    """基础分：信誉分 0–100；加成 skill_token 50 + skill_overlap 20 + recent 10 + price_fit 20；总分 0–200。"""
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
    """返回 `{task_id, candidates: [...]}`；若任务不存在抛 ValueError。

    candidates 每个元素包含：`agent`（基本信息 + 归属 + 信誉分）+ `stats`（核心指标）+
    `match: {total_score, breakdown}` + `suggested_price`（点数）。
    """
    task = db.query(Task).filter(Task.id == int(task_id)).first()
    if not task:
        raise ValueError("task_not_found")

    k = max(1, min(20, int(k or 5)))
    task_token = _task_skill_token(task)
    task_skills = _task_skills(task)

    # NOTE: 过滤候选池：active Agent，非发布者自己的 Agent，未被该任务接取者独占
    query = db.query(Agent).filter(Agent.is_active == True)  # noqa: E712
    if exclude_owner_id is not None:
        query = query.filter(Agent.owner_id != int(exclude_owner_id))
    # NOTE: 若是定向任务（指定 invited_agent_ids），将候选限制在其中
    invited = getattr(task, "invited_agent_ids", None)
    if invited and isinstance(invited, list) and invited:
        invited_ids = [int(x) for x in invited if x is not None]
        if invited_ids:
            query = query.filter(Agent.id.in_(invited_ids))
    # NOTE: 优先推倾向完成过相似任务的 Agent：通过技能 token 先筛一批，再补余量
    candidates_primary: List[Agent] = []
    if task_token:
        # NOTE: SQLite JSON 存储场景下难以直接 JSON 查询，采用 Python 过滤
        rough = query.limit(_MAX_POOL).all()
        for a in rough:
            if _agent_skill_token(a) == task_token:
                candidates_primary.append(a)
    candidates_all = query.limit(_MAX_POOL).all() if not candidates_primary else list({a.id: a for a in (candidates_primary + query.limit(_MAX_POOL).all())}.values())

    reward_points = int(getattr(task, "reward_points", 0) or 0)
    cards: List[Dict[str, Any]] = []
    for a in candidates_all:
        try:
            card = compute_agent_reputation(db, a.id)
        except Exception:
            card = None
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

    # NOTE: 首过验收率 > 80% 的候选人自然排前；否则按总分降序
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
