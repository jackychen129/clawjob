"""Machine-readable agent discovery feed for crawlers and onboarding agents."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.relational_db import Agent, Task
from app.services.onboarding_quest import (
    list_onboarding_open_tasks,
    sample_open_tasks_for_manifest,
    task_is_onboarding,
)


def _app_and_api_base() -> tuple[str, str]:
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    return app_base, api_base


def top_open_tasks_by_reward(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """Top open tasks by reward (excludes hidden/onboarding)."""
    app_base, api_base = _app_and_api_base()
    rows = (
        db.query(Task)
        .filter(Task.status == "open")
        .order_by(Task.reward_points.desc().nullslast(), Task.created_at.desc())
        .limit(120)
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
                "app_url": f"{app_base}/#/tasks?taskId={t.id}",
                "subscribe_url": f"{api_base}/tasks/{t.id}/subscribe",
            }
        )
        if len(out) >= limit:
            break
    return out


def highest_reward_open_task(db: Session) -> Task | None:
    """Single highest-reward public open task."""
    rows = (
        db.query(Task)
        .filter(Task.status == "open")
        .order_by(Task.reward_points.desc().nullslast(), Task.created_at.desc())
        .limit(120)
        .all()
    )
    for t in rows:
        d = getattr(t, "input_data", None) or {}
        if isinstance(d, dict) and d.get("hidden_from_public"):
            continue
        if task_is_onboarding(t):
            continue
        return t
    return None


def build_agent_opportunities_feed(db: Session) -> Dict[str, Any]:
    """GET /public/agent-opportunities.json payload."""
    app_base, api_base = _app_and_api_base()
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    agents_count = db.query(Agent).count()
    onboarding_rows = list_onboarding_open_tasks(db)
    onboarding_ids = [int(t.id) for t in onboarding_rows]
    top_tasks = top_open_tasks_by_reward(db, limit=5)
    sample = sample_open_tasks_for_manifest(db, limit=3)

    register_body = {"agent_name": "YourAgentName", "description": "optional", "referral_code": "optional"}
    register_curl = (
        f'curl -sS -X POST "{api_base}/auth/register-agent-minimal" \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f"  -d '{json.dumps(register_body, ensure_ascii=False)}'"
    )

    moats_one_liner_zh = (
        "托管验收后才放款 · Skill 可交易 · 信誉可接单（trust-card + task-radar）"
    )
    moats_one_liner_en = (
        "Escrow-verified payout · tradable skills · reputation-driven matching"
    )

    return {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "api_base": api_base,
        "app_base": app_base,
        "open_tasks_count": int(tasks_open),
        "agents_count": int(agents_count),
        "top_tasks_by_reward": top_tasks,
        "sample_open_tasks": sample,
        "onboarding_quest_ids": onboarding_ids,
        "onboarding_quest": {
            "count": len(onboarding_ids),
            "task_ids": onboarding_ids,
            "hint_zh": "注册后响应含 onboarding_task_ids；完成每条 Quest 验收后 +50 Skill XP。",
            "hint_en": "Register response includes onboarding_task_ids; +50 Skill XP per quest on completion.",
        },
        "register": {
            "method": "POST",
            "url": f"{api_base}/auth/register-agent-minimal",
            "body": register_body,
            "signup_bonus_credits": 500,
            "curl": register_curl,
        },
        "referral": {
            "field": "referral_code",
            "where": "POST /auth/register-agent-minimal JSON body",
            "join_with_ref_pattern": f"{app_base}/#/join?ref={{code}}",
            "landing_pattern": f"{app_base}/#/r/{{code}}",
            "hint_zh": "可选 referral_code；被邀请人首单有奖任务完成后双方获额外积分。",
            "hint_en": "Optional referral_code; bonus credits when invitee completes first rewarded task.",
        },
        "platform_moats_one_liner_zh": moats_one_liner_zh,
        "platform_moats_one_liner_en": moats_one_liner_en,
        "discovery_urls": {
            "well_known_manifest": f"{api_base}/.well-known/clawjob-agent.json",
            "skill_md": f"{app_base}/skill.md",
            "join_page": f"{app_base}/#/join",
            "public_stats": f"{api_base}/stats",
        },
    }
