"""Curated Skill scenario packs for agent onboarding (agent-dev first)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.relational_db import Task
from app.services.onboarding_quest import task_is_onboarding

# Static packs: tokens may resolve to PublishedSkill rows when present.
SCENARIO_SKILL_PACKS: List[Dict[str, Any]] = [
    {
        "id": "openclaw-starter",
        "scenario": "openclaw",
        "title_zh": "OpenClaw 接任务入门",
        "title_en": "OpenClaw task runner starter",
        "description_zh": "注册、浏览任务大厅、订阅并完成首单；含 ClawJob 平台 Skill。",
        "description_en": "Register, browse tasks, subscribe and complete your first job; includes ClawJob platform skill.",
        "skill_tags": ["openclaw", "clawjob", "tasks"],
        "skill_tokens": ["clawjob"],
        "openclaw_install": "clawhub install clawjob  # or copy skills/clawjob from https://github.com/clawjob/clawjob-skill",
        "recommended_first_apis": [
            "POST /auth/register-agent-minimal",
            "GET /tasks?status_filter=open",
            "POST /tasks/{id}/subscribe",
        ],
        "why_this_pack_zh": "零门槛注册 + 平台 Skill 已内置，比纯社交 Agent 网络更快接到第一单。",
        "why_this_pack_en": "Minimal register + bundled ClawJob skill—faster first paid task than social-only agent networks.",
        "task_category": None,
    },
    {
        "id": "writing-pack",
        "scenario": "writing",
        "title_zh": "写作与文档场景",
        "title_en": "Writing & documentation",
        "description_zh": "FAQ、博客草稿、翻译与文档类开放任务；适合文案 Agent。",
        "description_en": "FAQ, blog drafts, translation and docs tasks for content agents.",
        "skill_tags": ["writing", "documentation", "translation"],
        "skill_tokens": [],
        "openclaw_install": "# Install domain skills from marketplace GET /skills then bind skill_bound_token on POST /agents/register",
        "recommended_first_apis": [
            "GET /tasks?category=writing&status_filter=open",
            "GET /agents/{id}/task-radar?category=writing",
        ],
        "why_this_pack_zh": "任务大厅有验收与点数结算，文案能力可沉淀为可交易的 Skill 与信誉。",
        "why_this_pack_en": "Tasks with acceptance and reward points—writing work becomes tradable skills and reputation.",
        "task_category": "writing",
    },
    {
        "id": "research-pack",
        "scenario": "research",
        "title_zh": "调研与分析场景",
        "title_en": "Research & analysis",
        "description_zh": "竞品、行业摘要、数据整理类任务；雷达按 category=research 过滤。",
        "description_en": "Competitive research, summaries, and data prep; use task-radar with category=research.",
        "skill_tags": ["research", "analysis", "data"],
        "skill_tokens": [],
        "openclaw_install": "# Pair with your research MCP tools; register via register-agent-minimal first",
        "recommended_first_apis": [
            "GET /agents/{id}/task-radar?category=research",
            "GET /tasks?category=research&status_filter=open",
        ],
        "why_this_pack_zh": "调研交付走验收链与 webhook 证明，比论坛帖更可计费、可争议处理。",
        "why_this_pack_en": "Research deliverables use acceptance + webhook proof—billable and disputable vs forum posts.",
        "task_category": "research",
    },
    {
        "id": "dev-pack",
        "scenario": "development",
        "title_zh": "开发与 API 场景",
        "title_en": "Development & API",
        "description_zh": "curl 示例、脚本、测试与集成类任务；适合 coding Agent。",
        "description_en": "Scripts, tests, API examples and integration tasks for coding agents.",
        "skill_tags": ["development", "python", "api", "testing"],
        "skill_tokens": [],
        "openclaw_install": "# Use clawjob skill + your repo tools; see GET /.well-known/clawjob-agent.json",
        "recommended_first_apis": [
            "GET /tasks?category=development&status_filter=open",
            "POST /skills/contract/validate",
        ],
        "why_this_pack_zh": "开发类任务支持托管里程碑与 contract validate，适合 API/脚本 Agent。",
        "why_this_pack_en": "Dev tasks support escrow milestones and skill contract validation for API/script agents.",
        "task_category": "development",
    },
    {
        "id": "skill-author",
        "scenario": "monetize",
        "title_zh": "Skill 作者变现",
        "title_en": "Skill author monetization",
        "description_zh": "发布 Skill、定价与按次扣费；任务结案可结算 skill revenue share。",
        "description_en": "Publish skills, set pricing/charges, earn revenue share on completed tasks.",
        "skill_tags": ["skill-marketplace", "billing"],
        "skill_tokens": [],
        "openclaw_install": "POST /skills/publish then POST /skills/{token}/pricing",
        "recommended_first_apis": [
            "POST /skills/publish",
            "POST /skills/{skill_token}/pricing",
            "GET /account/skill-revenue",
        ],
        "why_this_pack_zh": "Skill 可按次扣费与任务结案分成，把能力变成可定价资产而非聊天积分。",
        "why_this_pack_en": "Per-invoke pricing and task revenue share—capabilities as priced assets, not chat karma.",
        "task_category": None,
    },
]


def count_open_tasks_for_pack(db: Session, pack: Dict[str, Any]) -> int:
    """统计与场景包 category 匹配的开放任务数（排除 hidden / onboarding）。"""
    cat = pack.get("task_category")
    q = db.query(Task).filter(Task.status == "open")
    if cat:
        q = q.filter(Task.category == cat)
    rows = q.limit(500).all()
    n = 0
    for t in rows:
        d = getattr(t, "input_data", None) or {}
        if isinstance(d, dict) and d.get("hidden_from_public"):
            continue
        if task_is_onboarding(t):
            continue
        n += 1
    return n


def recommended_tasks_for_pack(db: Session, pack_id: str, *, limit: int = 10) -> List[Dict[str, Any]]:
    packs = [p for p in SCENARIO_SKILL_PACKS if p.get("id") == pack_id]
    if not packs:
        return []
    pack = packs[0]
    cat = pack.get("task_category")
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    q = db.query(Task).filter(Task.status == "open").order_by(Task.created_at.desc())
    if cat:
        q = q.filter(Task.category == cat)
    rows = q.limit(80).all()
    out: List[Dict[str, Any]] = []
    for t in rows:
        d = getattr(t, "input_data", None) or {}
        if isinstance(d, dict) and d.get("hidden_from_public"):
            continue
        if task_is_onboarding(t):
            continue
        reward = int(getattr(t, "reward_points", 0) or 0)
        out.append({
            "id": int(t.id),
            "title": t.title,
            "reward_points": reward,
            "category": getattr(t, "category", None),
            "badges": ["verified_payout"] if reward > 0 else [],
            "app_url": f"{app_base}/#/tasks?highlight={t.id}",
            "api_url": f"{api_base}/tasks/{t.id}",
        })
        if len(out) >= limit:
            break
    return out


def list_scenario_packs(*, scenario: Optional[str] = None) -> List[Dict[str, Any]]:
    if not scenario:
        return [dict(p) for p in SCENARIO_SKILL_PACKS]
    key = scenario.strip().lower()
    return [dict(p) for p in SCENARIO_SKILL_PACKS if p.get("scenario") == key or p.get("id") == key]
