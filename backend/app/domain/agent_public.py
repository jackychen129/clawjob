"""公开列表 / 统计用的 Agent 可见性规则（排除系统、探活、演示等非真实 Agent）。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.database.relational_db import Agent, Task, TaskSubscription, User
from app.domain.task_helpers import CLAWJOB_SYSTEM_AGENT_NAME, CLAWJOB_SYSTEM_USERNAME

# 探活 / 部署验证 / 监控脚本常用命名前缀（大小写不敏感）
PROBE_NAME_RE = re.compile(
    r"^(probe_|test_|deploy_|verify_|monitor_|deployprobe)",
    re.IGNORECASE,
)

DEMO_SEED_USERNAMES = frozenset({"alice", "bob", "carol"})
DEMO_SEED_EMAIL_SUFFIX = "@example.com"


def agent_name_is_probe_pattern(name: Optional[str]) -> bool:
    n = (name or "").strip()
    if not n:
        return False
    if PROBE_NAME_RE.match(n):
        return True
    lower = n.lower()
    if "registration handshake" in lower:
        return True
    return False


def owner_is_guest(username: Optional[str]) -> bool:
    return bool(username and str(username).startswith("guest_"))


def owner_is_system(username: Optional[str]) -> bool:
    return (username or "") == CLAWJOB_SYSTEM_USERNAME


def agent_is_system_agent(agent: Agent, owner: Optional[User]) -> bool:
    if owner_is_system(getattr(owner, "username", None) if owner else None):
        return True
    return (getattr(agent, "name", "") or "").strip() == CLAWJOB_SYSTEM_AGENT_NAME


def agent_config_flag(cfg: Optional[dict], key: str) -> bool:
    if not isinstance(cfg, dict):
        return False
    return bool(cfg.get(key))


def agent_is_seed_demo(agent: Agent, owner: Optional[User]) -> bool:
    if not owner:
        return False
    uname = (getattr(owner, "username", "") or "").strip()
    email = (getattr(owner, "email", "") or "").strip().lower()
    if uname in DEMO_SEED_USERNAMES and email.endswith(DEMO_SEED_EMAIL_SUFFIX):
        return True
    cfg = agent.config if isinstance(agent.config, dict) else {}
    return (cfg.get("created_by") or "") == "seed_demo_data"


def agent_has_hidden_config(agent: Agent) -> bool:
    cfg = agent.config if isinstance(agent.config, dict) else {}
    if cfg.get("hidden_from_public"):
        return True
    if cfg.get("internal_probe"):
        return True
    return False


def agent_completed_stats(db: Session, agent_id: int) -> Tuple[int, int]:
    """返回 (completed_count, earned_points)。"""
    row = (
        db.query(
            func.count(Task.id),
            func.coalesce(func.sum(Task.reward_points), 0),
        )
        .filter(Task.agent_id == agent_id, Task.status == "completed")
        .first()
    )
    if not row:
        return 0, 0
    return int(row[0] or 0), int(row[1] or 0)


def agent_subscription_count(db: Session, agent_id: int) -> int:
    return (
        db.query(TaskSubscription)
        .filter(TaskSubscription.agent_id == agent_id)
        .count()
    )


def audit_agent_flags(
    agent: Agent,
    owner: Optional[User],
    *,
    completed_count: int = 0,
    earned_points: int = 0,
    subscription_count: int = 0,
) -> Dict[str, bool]:
    cfg = agent.config if isinstance(agent.config, dict) else {}
    owner_name = getattr(owner, "username", None) if owner else None
    return {
        "system": agent_is_system_agent(agent, owner),
        "guest_owner": owner_is_guest(owner_name),
        "probe_name_pattern": agent_name_is_probe_pattern(getattr(agent, "name", None)),
        "zero_tasks": completed_count == 0,
        "never_subscribed": subscription_count == 0,
        "created_by_script": bool(
            agent_has_hidden_config(agent)
            or agent_is_seed_demo(agent, owner)
            or (cfg.get("created_by") in ("script", "verify-deployed", "monitor_probe"))
        ),
        "inactive": not bool(getattr(agent, "is_active", True)),
        "has_real_earnings": earned_points > 0,
        "has_completions": completed_count > 0,
    }


def agent_is_public(agent: Agent, owner: Optional[User]) -> bool:
    """是否应出现在公开统计 / 候选 / 排行榜 / 动态流。"""
    if not getattr(agent, "is_active", True):
        return False
    if owner and not getattr(owner, "is_active", True):
        return False
    if agent_is_system_agent(agent, owner):
        return False
    if agent_has_hidden_config(agent):
        return False
    if agent_name_is_probe_pattern(getattr(agent, "name", None)):
        return False
    if owner_is_guest(getattr(owner, "username", None) if owner else None):
        return False
    if agent_is_seed_demo(agent, owner):
        return False
    return True


def apply_public_agent_filters(q: Query, *, AgentModel=Agent, UserModel=User) -> Query:
    """SQL 层预过滤：活跃 + 非系统账号 owner（探活名等仍在 Python 层二次过滤）。"""
    return (
        q.filter(AgentModel.is_active == True)  # noqa: E712
        .filter(UserModel.is_active == True)  # noqa: E712
        .filter(UserModel.username != CLAWJOB_SYSTEM_USERNAME)
    )


def filter_public_agent_rows(
    rows: Iterable[Tuple[Any, ...]],
    *,
    agent_index: int = 0,
    owner_index: int = 1,
) -> List[Tuple[Any, ...]]:
    out: List[Tuple[Any, ...]] = []
    for row in rows:
        agent = row[agent_index]
        owner = row[owner_index] if len(row) > owner_index else None
        if agent_is_public(agent, owner):
            out.append(row)
    return out


def count_public_agents(db: Session, *, since: Optional[datetime] = None) -> int:
    q = db.query(Agent, User).join(User, Agent.owner_id == User.id)
    q = apply_public_agent_filters(q)
    if since is not None:
        q = q.filter(Agent.created_at >= since)
    n = 0
    for agent, owner in q.all():
        if agent_is_public(agent, owner):
            n += 1
    return n


def count_total_agents(db: Session, *, since: Optional[datetime] = None) -> int:
    q = db.query(Agent)
    if since is not None:
        q = q.filter(Agent.created_at >= since)
    return q.count()


def cleanup_should_hide(
    agent: Agent,
    owner: Optional[User],
    flags: Dict[str, bool],
) -> Tuple[bool, str]:
    """是否应在 cleanup 中隐藏/停用（不含有真实完成或收益的保护）。"""
    if flags.get("has_completions") or flags.get("has_real_earnings"):
        return False, "protected: real completions/earnings"

    reasons: List[str] = []
    if flags.get("system"):
        reasons.append("system")
    if flags.get("probe_name_pattern"):
        reasons.append("probe_name")
    if flags.get("guest_owner"):
        reasons.append("guest_owner")
    if flags.get("created_by_script") and (
        flags.get("probe_name_pattern") or agent_has_hidden_config(agent)
    ):
        reasons.append("created_by_script")
    if agent_is_seed_demo(agent, owner):
        reasons.append("seed_demo")

    if not reasons:
        return False, ""
    return True, "+".join(reasons)


def cleanup_apply_hide(agent: Agent, reason: str, *, deactivate: bool) -> None:
    cfg = dict(agent.config or {}) if isinstance(agent.config, dict) else {}
    cfg["hidden_from_public"] = True
    cfg["hidden_reason"] = reason
    cfg["hidden_at"] = datetime.utcnow().isoformat() + "Z"
    agent.config = cfg
    if deactivate and not agent_is_system_agent(agent, None):
        agent.is_active = False
