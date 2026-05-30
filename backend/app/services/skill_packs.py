"""Curated Skill scenario packs for agent onboarding (agent-dev first)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    },
]


def list_scenario_packs(*, scenario: Optional[str] = None) -> List[Dict[str, Any]]:
    if not scenario:
        return [dict(p) for p in SCENARIO_SKILL_PACKS]
    key = scenario.strip().lower()
    return [dict(p) for p in SCENARIO_SKILL_PACKS if p.get("scenario") == key or p.get("id") == key]
