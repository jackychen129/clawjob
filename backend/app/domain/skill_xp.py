"""Skill XP helpers."""
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Agent, PublishedSkill, Task


def _env_int(name: str, default: int, *, min_value: Optional[int] = None) -> int:
    raw = os.getenv(name)
    try:
        v = int(raw) if raw not in (None, "") else int(default)
    except (TypeError, ValueError):
        v = int(default)
    if min_value is not None:
        v = max(min_value, v)
    return v


def _env_float(name: str, default: float, *, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
    raw = os.getenv(name)
    try:
        v = float(raw) if raw not in (None, "") else float(default)
    except (TypeError, ValueError):
        v = float(default)
    if min_value is not None:
        v = max(min_value, v)
    if max_value is not None:
        v = min(max_value, v)
    return v


SKILL_DECAY_IDLE_DAYS = _env_int("SKILL_DECAY_IDLE_DAYS", 14, min_value=1)
SKILL_DECAY_WEEKLY_RATIO = _env_float("SKILL_DECAY_WEEKLY_RATIO", 0.02, min_value=0.0, max_value=1.0)
SKILL_DECAY_MAX_RATIO = _env_float("SKILL_DECAY_MAX_RATIO", 0.2, min_value=0.0, max_value=1.0)

def task_skills_for_xp(t: Task) -> List[str]:
    d = getattr(t, "input_data", None) or {}
    out: List[str] = []
    if isinstance(d, dict):
        skills = d.get("skills")
        if isinstance(skills, list):
            out.extend([str(s).strip() for s in skills if str(s).strip()])
    if not out and getattr(t, "category", None):
        out.append(str(getattr(t, "category")).strip())
    return list(dict.fromkeys(out))


def agent_skill_token(db: Session, agent_id: Optional[int]) -> str:
    """Return skill_bound_token from agent config if available."""
    if not agent_id:
        return ""
    a = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not a:
        return ""
    cfg = a.config or {}
    return (cfg.get("skill_bound_token") or "").strip() if isinstance(cfg, dict) else ""


def task_related_skill(db: Session, t: Task, task_input: Optional[dict] = None) -> Optional[dict]:
    """Resolve published skill linked to task by token."""
    d = task_input if isinstance(task_input, dict) else (getattr(t, "input_data", None) or {})
    if not isinstance(d, dict):
        d = {}
    token = (d.get("related_skill_token") or "").strip()
    source = "manual"
    if not token:
        token = agent_skill_token(db, getattr(t, "creator_agent_id", None))
        source = "creator_agent"
    if not token:
        token = agent_skill_token(db, getattr(t, "agent_id", None))
        source = "assigned_agent"
    if not token:
        return None
    ps = db.query(PublishedSkill).filter(PublishedSkill.skill_token == token).first()
    if not ps:
        return {"skill_token": token, "source": source}
    return {
        "skill_id": ps.id,
        "skill_token": token,
        "skill_name": ps.name,
        "download_skill_url": ps.download_skill_url,
        "verified": bool(ps.verified),
        "source": source,
    }


def level_from_xp(xp: int) -> dict:
    # NOTE: translated comment in English.
    level = 1
    remain = max(0, int(xp or 0))
    need = 100
    while remain >= need:
        remain -= need
        level += 1
        need = 100 + (level - 1) * 20
    progress = (remain / need) if need > 0 else 0
    return {"level": level, "xp_current": int(remain), "xp_next": int(need), "progress": round(progress, 4)}


def agent_skill_xp_map(db: Session, agent_id: int) -> dict:
    tasks = db.query(Task).filter(Task.agent_id == agent_id, Task.status == "completed").all()
    xp_map: dict = {}
    for t in tasks:
        reward = int(getattr(t, "reward_points", 0) or 0)
        base_xp = max(10, min(80, reward // 2 if reward > 0 else 10))
        for s in task_skills_for_xp(t):
            xp_map[s] = int(xp_map.get(s, 0) or 0) + base_xp
    return xp_map


def skill_decay_meta(tasks: List[Task]) -> dict:
    """
    惰性技能折旧（P2 最小版）：
    - 最近 SKILL_DECAY_IDLE_DAYS 天内活跃：不折旧
    - 超过后：每周衰减 SKILL_DECAY_WEEKLY_RATIO，上限 SKILL_DECAY_MAX_RATIO
    """
    last_at: Optional[datetime] = None
    for t in tasks:
        ca = getattr(t, "completed_at", None)
        if ca and (last_at is None or ca > last_at):
            last_at = ca
    if not last_at:
        return {"ratio": 0.0, "last_active_at": None}
    idle_days = max(0, int((datetime.utcnow() - last_at).total_seconds() // 86400))
    if idle_days <= SKILL_DECAY_IDLE_DAYS:
        return {"ratio": 0.0, "last_active_at": last_at}
    weeks = max(1, (idle_days - SKILL_DECAY_IDLE_DAYS) // 7)
    ratio = min(SKILL_DECAY_MAX_RATIO, weeks * SKILL_DECAY_WEEKLY_RATIO)
    return {"ratio": float(round(ratio, 4)), "last_active_at": last_at}


def apply_skill_decay(xp_map: dict, ratio: float) -> dict:
    if ratio <= 0:
        return {k: int(v or 0) for k, v in xp_map.items()}
    out: dict = {}
    for k, v in xp_map.items():
        base = max(0, int(v or 0))
        out[k] = int(round(base * (1.0 - ratio)))
    return out
