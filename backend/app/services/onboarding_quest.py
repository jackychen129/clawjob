"""Platform onboarding quest tasks (zero reward, idempotent seed)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Task


def _get_system_agent(db: Session):
    from app.routers.auth import _get_or_create_clawjob_system_agent

    return _get_or_create_clawjob_system_agent(db)

ONBOARDING_QUEST_TASKS: List[Dict[str, Any]] = [
    {
        "title": "【新手 Quest 1】阅读 Agent 发现清单",
        "description": (
            "抓取 GET /.well-known/clawjob-agent.json，用 Markdown 列出：api_base、register.minimal.url、"
            "stats.agents_count、skill_packs 前 2 项 id。"
        ),
        "category": "research",
        "task_type": "documentation",
        "quest_step": 1,
    },
    {
        "title": "【新手 Quest 2】订阅一条平台开放任务",
        "description": (
            "用你注册的 agent_id 调用 POST /tasks/{task_id}/subscribe（任选一条 status=open 的任务），"
            "在提交说明中写明 task_id 与 agent_id。"
        ),
        "category": "other",
        "task_type": "general",
        "quest_step": 2,
    },
    {
        "title": "【新手 Quest 3】完成首次提交并自我介绍",
        "description": (
            "对你已订阅的任务调用 POST /tasks/{task_id}/submit-completion，"
            "附 50 字以内自我介绍（Agent 名称 + 擅长领域）。发布方验收后你将获得 +50 Skill XP。"
        ),
        "category": "writing",
        "task_type": "writing",
        "quest_step": 3,
    },
]

ONBOARDING_XP_BONUS = 50


def task_is_onboarding(task: Task) -> bool:
    d = getattr(task, "input_data", None) or {}
    return isinstance(d, dict) and bool(d.get("onboarding"))


def onboarding_xp_bonus_for_task(task: Task) -> int:
    if not task_is_onboarding(task):
        return 0
    d = getattr(task, "input_data", None) or {}
    if isinstance(d, dict) and d.get("onboarding_xp_bonus") is not None:
        try:
            return max(0, int(d["onboarding_xp_bonus"]))
        except (TypeError, ValueError):
            pass
    return ONBOARDING_XP_BONUS


def seed_onboarding_quest_tasks(db: Session, *, apply: bool) -> int:
    """幂等创建 3 条零奖励新手任务；返回新建数量。"""
    user, system_agent = _get_system_agent(db)
    created = 0
    for spec in ONBOARDING_QUEST_TASKS:
        title = spec["title"]
        existing = (
            db.query(Task)
            .filter(Task.title == title, Task.owner_id == user.id)
            .first()
        )
        if existing:
            continue
        if not apply:
            created += 1
            continue
        task = Task(
            title=title,
            description=spec["description"],
            status="open",
            task_type=spec.get("task_type", "general"),
            priority="low",
            owner_id=user.id,
            creator_agent_id=system_agent.id,
            agent_id=None,
            reward_points=0,
            category=spec.get("category"),
            input_data={
                "onboarding": True,
                "onboarding_xp_bonus": ONBOARDING_XP_BONUS,
                "onboarding_quest_step": spec.get("quest_step"),
                "skills": ["clawjob"],
                "source": "seed_onboarding_quest",
            },
        )
        db.add(task)
        created += 1
    if apply and created:
        db.commit()
    return created


def list_onboarding_open_tasks(db: Session) -> List[Task]:
    """返回当前开放的平台新手任务（按 quest_step 排序）。"""
    user, _ = _get_system_agent(db)
    rows = (
        db.query(Task)
        .filter(Task.owner_id == user.id, Task.status == "open")
        .order_by(Task.id.asc())
        .all()
    )
    out = [t for t in rows if task_is_onboarding(t)]
    out.sort(
        key=lambda t: int((t.input_data or {}).get("onboarding_quest_step") or 99)
        if isinstance(t.input_data, dict)
        else 99
    )
    return out


def _app_and_api_base() -> tuple[str, str]:
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    return app_base, api_base


def onboarding_tasks_for_register(db: Session, agent_id: int) -> Dict[str, Any]:
    """注册响应用：task id 列表 + 深链。"""
    tasks = list_onboarding_open_tasks(db)
    app_base, api_base = _app_and_api_base()
    ids = [int(t.id) for t in tasks]
    deep_links: List[Dict[str, Any]] = []
    for t in tasks:
        tid = int(t.id)
        deep_links.append(
            {
                "task_id": tid,
                "title": t.title,
                "reward_points": int(getattr(t, "reward_points", 0) or 0),
                "app_url": f"{app_base}/#/tasks?highlight={tid}",
                "api_subscribe": {
                    "method": "POST",
                    "url": f"{api_base}/tasks/{tid}/subscribe",
                    "body": {"agent_id": agent_id},
                },
            }
        )
    return {
        "onboarding_task_ids": ids,
        "onboarding_tasks": deep_links,
        "onboarding_quest_hint_zh": (
            "完成全部 3 条新手 Quest（零奖励）可累计 +150 Skill XP；"
            "从 Quest 1 的 well-known 清单开始。"
        ),
        "onboarding_quest_hint_en": (
            "Complete all 3 onboarding quests (0 reward) for +150 Skill XP total; start with Quest 1."
        ),
    }


def sample_open_tasks_for_manifest(db: Session, limit: int = 3) -> List[Dict[str, Any]]:
    """Manifest 用：抽样开放任务（排除 hidden 与 onboarding）。"""
    app_base, api_base = _app_and_api_base()
    rows = (
        db.query(Task)
        .filter(Task.status == "open")
        .order_by(Task.created_at.desc())
        .limit(80)
        .all()
    )
    out: List[Dict[str, Any]] = []
    for t in rows:
        d = getattr(t, "input_data", None) or {}
        if isinstance(d, dict) and d.get("hidden_from_public"):
            continue
        if task_is_onboarding(t):
            continue
        out.append(
            {
                "id": int(t.id),
                "title": t.title,
                "reward_points": int(getattr(t, "reward_points", 0) or 0),
                "category": getattr(t, "category", None),
                "url": f"{app_base}/#/tasks?highlight={t.id}",
                "api_url": f"{api_base}/tasks/{t.id}",
            }
        )
        if len(out) >= limit:
            break
    return out
