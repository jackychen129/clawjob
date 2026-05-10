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


def _suggested_price(
    db: Session,
    *,
    skill_token: Optional[str],
    category: Optional[str],
    reward_points: int,
    agent_id: int,
) -> int:
    """基于最近相似任务的中位价，回退到任务本身的 reward_points。"""
    from sqlalchemy import func

    q = db.query(Task.reward_points).filter(
        Task.status == "completed",
        Task.reward_points.isnot(None),
        Task.reward_points > 0,
    )
    agent_q = q.filter(Task.agent_id == agent_id).order_by(Task.completed_at.desc()).limit(20)
    prices = [int(p) for (p,) in agent_q.all() if p is not None]
    if len(prices) < 3:
        scope = db.query(Task.reward_points).filter(
            Task.status == "completed",
            Task.reward_points.isnot(None),
            Task.reward_points > 0,
        )
        if category:
            scope = scope.filter(Task.category == category)
        scope = scope.order_by(Task.completed_at.desc()).limit(50)
        prices = [int(p) for (p,) in scope.all() if p is not None] or prices
    if not prices:
        return int(reward_points or 0)
    median = int(statistics.median(prices))
    return max(1, median)


def _score_candidate(
    card: Dict[str, Any],
    *,
    task_skill_token: Optional[str],
    task_skills: List[str],
) -> Dict[str, Any]:
    """基础分：信誉分 0–100；加成部分 0–60；总分 0–160。"""
    base = int(card.get("reputation_score", 60))
    breakdown = {"reputation": base, "skill_token": 0, "skill_overlap": 0, "recent_activity": 0}
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
        match = _score_candidate(card, task_skill_token=task_token, task_skills=task_skills)
        price = _suggested_price(
            db,
            skill_token=task_token,
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
