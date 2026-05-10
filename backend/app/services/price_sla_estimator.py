"""价格与 SLA 预估（Phase B-2）。

输入：skill / kind / category / difficulty。
输出：
- 建议点数（中位 + p25/p75/p90）
- 预估完成时长（以小时为单位，p50/p75）
- 预估接取等待时间（以小时为单位，p50/p75）
- 样本数（供前端判断可信度）
- 是否启发式回退（空数据时）

空数据回退策略（heuristic）：
- 按 skill / kind / category 字典给出合理默认值，避免新类目第一次发布看到 0。
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database.relational_db import Task


# NOTE: 启发式默认值：skill_token 优先 → category → kind → 全局兜底
_HEURISTIC_BY_SKILL: Dict[str, Dict[str, int]] = {
    "code_review": {"reward": 8, "hours": 4, "accept_wait_hours": 3},
    "bug_fix": {"reward": 12, "hours": 8, "accept_wait_hours": 4},
    "data_cleaning": {"reward": 15, "hours": 12, "accept_wait_hours": 4},
    "translation": {"reward": 5, "hours": 3, "accept_wait_hours": 2},
    "copywriting": {"reward": 6, "hours": 4, "accept_wait_hours": 3},
    "ui_design": {"reward": 20, "hours": 18, "accept_wait_hours": 6},
    "data_analysis": {"reward": 18, "hours": 14, "accept_wait_hours": 5},
}
_HEURISTIC_BY_CATEGORY: Dict[str, Dict[str, int]] = {
    "development": {"reward": 15, "hours": 10, "accept_wait_hours": 4},
    "design": {"reward": 18, "hours": 14, "accept_wait_hours": 5},
    "research": {"reward": 20, "hours": 16, "accept_wait_hours": 6},
    "writing": {"reward": 6, "hours": 4, "accept_wait_hours": 3},
    "data": {"reward": 15, "hours": 12, "accept_wait_hours": 4},
    "other": {"reward": 8, "hours": 6, "accept_wait_hours": 4},
}
_HEURISTIC_DEFAULT: Dict[str, int] = {"reward": 10, "hours": 8, "accept_wait_hours": 4}

_DIFFICULTY_FACTOR: Dict[str, float] = {
    "easy": 0.6,
    "normal": 1.0,
    "medium": 1.0,
    "hard": 1.6,
    "expert": 2.2,
}


@dataclass
class _Sample:
    reward: int
    duration_hours: Optional[float]
    accept_wait_hours: Optional[float]


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    vs = sorted(values)
    if len(vs) == 1:
        return float(vs[0])
    k = (len(vs) - 1) * p
    lo = int(math.floor(k))
    hi = int(math.ceil(k))
    if lo == hi:
        return float(vs[lo])
    frac = k - lo
    return float(vs[lo] * (1 - frac) + vs[hi] * frac)


def _hours_between(a, b) -> Optional[float]:
    if a is None or b is None:
        return None
    try:
        delta = (b - a).total_seconds() / 3600.0
        if delta < 0:
            return None
        if delta > 24 * 30:
            return None
        return float(delta)
    except Exception:
        return None


def _match_task(task: Task, *, skill_token: Optional[str], kind: Optional[str], category: Optional[str]) -> bool:
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    if skill_token:
        tok = extra.get("related_skill_token") if isinstance(extra, dict) else None
        if str(tok or "").strip() == skill_token.strip():
            return True
    if category:
        if (getattr(task, "category", None) or "").strip() == category.strip():
            return True
    if kind:
        tt = (getattr(task, "task_type", None) or "").strip()
        if tt == kind.strip():
            return True
    return False


def _fetch_samples(
    db: Session,
    *,
    skill_token: Optional[str],
    kind: Optional[str],
    category: Optional[str],
    limit: int = 500,
) -> List[_Sample]:
    query = db.query(Task).filter(Task.status.in_(["completed", "open"]))
    if category and category.strip():
        query = query.filter(Task.category == category.strip())
    query = query.order_by(Task.created_at.desc()).limit(limit)

    samples: List[_Sample] = []
    for t in query.all():
        if not _match_task(t, skill_token=skill_token, kind=kind, category=category):
            continue
        reward = int(getattr(t, "reward_points", 0) or 0)
        if reward <= 0:
            continue
        duration = _hours_between(getattr(t, "submitted_at", None), getattr(t, "completed_at", None))
        accept_wait = _hours_between(getattr(t, "created_at", None), getattr(t, "submitted_at", None))
        samples.append(_Sample(reward=reward, duration_hours=duration, accept_wait_hours=accept_wait))
    return samples


# NOTE: in-process LRU，避免高频重复查询。键 = (skill,kind,category,difficulty)
_ESTIMATE_CACHE: Dict[Tuple[str, str, str, str], Tuple[float, Dict[str, Any]]] = {}
_ESTIMATE_CACHE_TTL_SECONDS = 300


def _cache_key(skill: Optional[str], kind: Optional[str], category: Optional[str], difficulty: Optional[str]) -> Tuple[str, str, str, str]:
    return (
        (skill or "").strip().lower(),
        (kind or "").strip().lower(),
        (category or "").strip().lower(),
        (difficulty or "").strip().lower(),
    )


def _heuristic_base(*, skill: Optional[str], category: Optional[str]) -> Dict[str, int]:
    if skill:
        key = skill.strip().lower()
        if key in _HEURISTIC_BY_SKILL:
            return dict(_HEURISTIC_BY_SKILL[key])
    if category:
        key = category.strip().lower()
        if key in _HEURISTIC_BY_CATEGORY:
            return dict(_HEURISTIC_BY_CATEGORY[key])
    return dict(_HEURISTIC_DEFAULT)


def _difficulty_multiplier(difficulty: Optional[str]) -> float:
    if not difficulty:
        return 1.0
    return float(_DIFFICULTY_FACTOR.get(difficulty.strip().lower(), 1.0))


def estimate_price_sla(
    db: Session,
    *,
    skill: Optional[str] = None,
    kind: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """主入口：根据技能/任务类型/难度估算价格与 SLA。"""
    key = _cache_key(skill, kind, category, difficulty)
    now = time.time()
    hit = _ESTIMATE_CACHE.get(key)
    if hit and (now - hit[0]) < _ESTIMATE_CACHE_TTL_SECONDS:
        return dict(hit[1])

    samples = _fetch_samples(db, skill_token=skill, kind=kind, category=category, limit=limit)
    rewards = [float(s.reward) for s in samples]
    durations = [float(s.duration_hours) for s in samples if s.duration_hours is not None]
    waits = [float(s.accept_wait_hours) for s in samples if s.accept_wait_hours is not None]

    heuristic_used = len(samples) < 5
    mult = _difficulty_multiplier(difficulty)

    if heuristic_used:
        base = _heuristic_base(skill=skill, category=category)
        p50_reward = int(round(base["reward"] * mult))
        p25_reward = max(1, int(round(base["reward"] * mult * 0.7)))
        p75_reward = int(round(base["reward"] * mult * 1.3))
        p90_reward = int(round(base["reward"] * mult * 1.7))
        p50_hours = round(base["hours"] * mult, 1)
        p75_hours = round(base["hours"] * mult * 1.5, 1)
        p50_wait = round(base["accept_wait_hours"] * (1.2 if mult > 1 else 1.0), 1)
        p75_wait = round(base["accept_wait_hours"] * 2.0, 1)
    else:
        p50_reward = int(round((_percentile(rewards, 0.5) or 0) * mult))
        p25_reward = max(1, int(round((_percentile(rewards, 0.25) or 0) * mult)))
        p75_reward = int(round((_percentile(rewards, 0.75) or 0) * mult))
        p90_reward = int(round((_percentile(rewards, 0.9) or 0) * mult))
        p50_hours = round((_percentile(durations, 0.5) or 0) * mult, 1) if durations else None
        p75_hours = round((_percentile(durations, 0.75) or 0) * mult, 1) if durations else None
        p50_wait = round(_percentile(waits, 0.5) or 0, 1) if waits else None
        p75_wait = round(_percentile(waits, 0.75) or 0, 1) if waits else None

    suggestion = p50_reward
    floor = max(1, p25_reward)
    if suggestion < floor:
        suggestion = floor

    result: Dict[str, Any] = {
        "input": {
            "skill": skill,
            "kind": kind,
            "category": category,
            "difficulty": difficulty,
        },
        "sample_size": len(samples),
        "heuristic_used": heuristic_used,
        "reward_points": {
            "suggested": suggestion,
            "p25": p25_reward,
            "p50": p50_reward,
            "p75": p75_reward,
            "p90": p90_reward,
        },
        "completion_hours": {
            "p50": p50_hours,
            "p75": p75_hours,
        },
        "accept_wait_hours": {
            "p50": p50_wait,
            "p75": p75_wait,
        },
        "confidence": "low" if heuristic_used else ("medium" if len(samples) < 30 else "high"),
        "tips": _build_tips(heuristic_used=heuristic_used, sample=len(samples), suggestion=suggestion),
    }

    if len(_ESTIMATE_CACHE) > 256:
        # NOTE: 粗暴 LRU：清理最老的一半
        items = sorted(_ESTIMATE_CACHE.items(), key=lambda kv: kv[1][0])
        for old_key, _ in items[: len(items) // 2]:
            _ESTIMATE_CACHE.pop(old_key, None)
    _ESTIMATE_CACHE[key] = (now, result)
    return dict(result)


def _build_tips(*, heuristic_used: bool, sample: int, suggestion: int) -> List[str]:
    out: List[str] = []
    if heuristic_used:
        out.append("heuristic_fallback")
    if sample >= 30:
        out.append("high_confidence")
    if suggestion >= 50:
        out.append("premium_task")
    return out


def clear_estimate_cache() -> None:
    """供测试使用：清空内存缓存。"""
    _ESTIMATE_CACHE.clear()
