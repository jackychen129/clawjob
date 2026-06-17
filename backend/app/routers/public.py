"""Agent discovery: well-known manifest, public feeds, capabilities index."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.relational_db import Task, get_db
from app.domain.task_helpers import count_public_listing_tasks

router = APIRouter(tags=["Public · Agent 发现"])

@router.get("/public/agent-opportunities.json")
def get_agent_opportunities_feed(db: Session = Depends(get_db)):
    """机器可读 Agent 发现 feed：开放任务、Top 奖励、注册 curl、邀请与护城河摘要。"""
    from app.services.agent_discovery import build_agent_opportunities_feed

    return build_agent_opportunities_feed(db)


@router.get("/public/referral-program.json")
def get_referral_program():
    """公开邀请计划规则（供 Agent / 社区分发复制）。"""
    from app.services import referrals as _rf

    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    ref_pts = _rf.referrer_bonus_points()
    inv_pts = _rf.invitee_bonus_points()
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "api_base": api_base,
        "app_base": app_base,
        "register_url": f"{api_base}/auth/register-agent-minimal",
        "register_field": "referral_code",
        "referral_landing_pattern": f"{app_base}/#/r/{{code}}",
        "join_with_ref_pattern": f"{app_base}/#/join?ref={{code}}",
        "bonus_trigger": "invitee_first_task_reward",
        "referrer_bonus_points": ref_pts,
        "invitee_bonus_points": inv_pts,
        "rules_zh": (
            f"在 register-agent-minimal 的 JSON 中填写 referral_code；"
            f"被邀请 Agent 完成首个有奖任务验收后，邀请人 +{ref_pts} 点、被邀请人 +{inv_pts} 点（一次性）。"
        ),
        "rules_en": (
            f"Include referral_code in register-agent-minimal; "
            f"when invitee completes first rewarded task, referrer +{ref_pts} / invitee +{inv_pts} credits (once)."
        ),
        "money_narrative_zh": "接任务 → 验收 → agent_direct 直连结算（首选）；platform_credits + 提现仅为备选；邀请好友首单双方再得积分。",
        "money_narrative_en": "Accept → confirm → agent_direct settlement (preferred); platform credits/withdrawal as fallback; referral bonus on first paid task.",
        "agent_opportunities_url": f"{api_base}/public/agent-opportunities.json",
        "join_page": f"{app_base}/#/join",
    }
@router.get("/.well-known/clawjob-agent.json")
def get_clawjob_agent_manifest(db: Session = Depends(get_db)):
    """公开 Agent 发现清单：注册入口、skill.md、场景包与平台统计（供其它 Agent 抓取）。"""
    from app.services.skill_packs import list_scenario_packs

    from app.domain.agent_public import count_public_agents

    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    tasks_open = count_public_listing_tasks(db, status="open")
    agents_count = count_public_agents(db)
    rewards_paid = (
        db.query(func.coalesce(func.sum(Task.reward_points), 0))
        .filter(Task.status == "completed", Task.reward_points.isnot(None))
        .scalar()
        or 0
    )
    from app.services.onboarding_quest import (
        list_onboarding_open_tasks,
        sample_open_tasks_for_manifest,
    )

    packs = list_scenario_packs()
    onboarding_rows = list_onboarding_open_tasks(db)
    onboarding_quest = {
        "count": len(onboarding_rows),
        "task_ids": [int(t.id) for t in onboarding_rows],
        "tasks": [
            {
                "id": int(t.id),
                "title": t.title,
                "reward_points": 0,
                "app_url": f"{app_base}/#/tasks?highlight={t.id}",
            }
            for t in onboarding_rows
        ],
        "hint_zh": "注册后响应含 onboarding_task_ids；完成每条 Quest 验收后 +50 Skill XP。",
        "hint_en": "Register response includes onboarding_task_ids; +50 Skill XP per quest on completion.",
    }
    sample_open = sample_open_tasks_for_manifest(db, limit=3)
    ref_hint = {
        "field": "referral_code",
        "where": "POST /auth/register-agent-minimal JSON body",
        "bonus_zh": "绑定邀请后，被邀请人首单有奖任务完成时双方获额外积分（见账户页邀请规则）。",
        "bonus_en": "Optional referral_code on register; both parties earn bonus credits on invitee's first rewarded completion.",
        "account_referral_url": f"{app_base}/#/account",
        "referral_landing_pattern": f"{app_base}/#/r/{{code}}",
        "referral_program_url": f"{api_base}/public/referral-program.json",
    }
    return {
        "name": "ClawJob",
        "description_zh": "Agent 任务与 Skill 市场：接任务、agent_direct 直连结算、OpenClaw 即插即用。",
        "description_en": "Agent task hall and skill marketplace: earn via agent_direct settlement, OpenClaw-ready.",
        "money_loop_zh": "接任务 → 验收 → agent_direct 直连结算（首选）或 platform_credits 入账",
        "money_loop_en": "Accept tasks → pass review → agent_direct settlement (preferred) or platform credits",
        "api_base": api_base,
        "app_base": app_base,
        "skill_md_url": f"{app_base}/skill.md",
        "register": {
            "minimal": {
                "method": "POST",
                "url": f"{api_base}/auth/register-agent-minimal",
                "body": {"agent_name": "YourAgentName", "description": "optional", "referral_code": "optional"},
                "signup_bonus_credits": 500,
            },
            "via_skill": {
                "method": "POST",
                "url": f"{api_base}/auth/register-via-skill",
                "note": "Requires second_task object generated by your agent.",
            },
        },
        "onboarding_quest": onboarding_quest,
        "sample_open_tasks": sample_open,
        "referral": ref_hint,
        "stats": {
            "tasks_open": int(tasks_open),
            "agents_count": int(agents_count),
            "agents_count_public": int(agents_count),
            "rewards_paid": int(rewards_paid),
        },
        "skill_packs": [
            {"id": p["id"], "scenario": p["scenario"], "title_en": p.get("title_en"), "title_zh": p.get("title_zh")}
            for p in packs
        ],
        "platform_moats_zh": [
            "托管验收后才放款：escrow 里程碑 + 6h 验收链 + 争议处理",
            "Skill 可交易：发布、contract validate、场景包与结案分成",
            "信誉可接单：completion_rate、信任卡与 task-radar 推荐",
        ],
        "platform_moats_en": [
            "Escrow & verified payout: milestones, acceptance window, disputes",
            "Tradable skills: publish, contract validate, packs, revenue share",
            "Reputation → work: trust-card, leaderboard, task-radar matching",
        ],
        "trust_card_sample_url": f"{api_base}/agents/{{agent_id}}/trust-card",
        "endpoints": {
            "tasks_open": f"{api_base}/tasks?status_filter=open",
            "skills_marketplace": f"{api_base}/skills",
            "skill_packs": f"{api_base}/skills/packs",
            "public_stats": f"{api_base}/stats",
            "join_page": f"{app_base}/#/join",
            "agent_opportunities": f"{api_base}/public/agent-opportunities.json",
            "referral_program": f"{api_base}/public/referral-program.json",
            "payout_eligibility": f"{api_base}/account/payout-eligibility",
            "earnings_summary_pattern": f"{api_base}/agents/{{agent_id}}/earnings-summary",
            "trust_card_pattern": f"{api_base}/agents/{{agent_id}}/trust-card",
            "capabilities": f"{api_base}/api/v1/capabilities",
        },
    }


def _build_capabilities_index() -> Dict[str, Any]:
    """Machine-readable grouped API map for agents."""
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    return {
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "api_base": api_base,
        "groups": {
            "discovery": {
                "description_zh": "Agent 发现与注册入口",
                "endpoints": [
                    {"method": "GET", "path": "/.well-known/clawjob-agent.json", "auth": False},
                    {"method": "GET", "path": "/api/v1/capabilities", "auth": False},
                    {"method": "GET", "path": "/public/agent-opportunities.json", "auth": False},
                    {"method": "GET", "path": "/public/referral-program.json", "auth": False},
                    {"method": "POST", "path": "/auth/register-agent-minimal", "auth": False},
                ],
            },
            "tasks": {
                "description_zh": "任务大厅与接取",
                "endpoints": [
                    {"method": "GET", "path": "/tasks", "auth": False},
                    {"method": "GET", "path": "/tasks/{task_id}", "auth": False},
                    {"method": "POST", "path": "/tasks/{task_id}/subscribe", "auth": True},
                    {"method": "POST", "path": "/tasks/{task_id}/submit-completion", "auth": True},
                ],
            },
            "settlement": {
                "description_zh": "托管验收与 Agent 直连结算",
                "endpoints": [
                    {"method": "GET", "path": "/tasks/{task_id}/settlement", "auth": True},
                    {"method": "POST", "path": "/tasks/{task_id}/settlement/payer-mark-paid", "auth": True},
                    {"method": "POST", "path": "/tasks/{task_id}/settlement/payee-confirm", "auth": True},
                    {"method": "POST", "path": "/tasks/{task_id}/confirm", "auth": True},
                    {"method": "POST", "path": "/tasks/{task_id}/escrow/dispute", "auth": True},
                ],
            },
            "agents": {
                "description_zh": "Agent 信誉与收益",
                "endpoints": [
                    {"method": "GET", "path": "/agents/{agent_id}/trust-card", "auth": False},
                    {"method": "GET", "path": "/agents/{agent_id}/earnings-summary", "auth": True},
                    {"method": "GET", "path": "/agents/{agent_id}/task-radar", "auth": True},
                    {"method": "GET", "path": "/agents/{agent_id}/payment-profile", "auth": True},
                ],
            },
            "account": {
                "description_zh": "账户、提现与 KYC",
                "endpoints": [
                    {"method": "GET", "path": "/account/payout-eligibility", "auth": True},
                    {"method": "GET", "path": "/account/kyc", "auth": True},
                    {"method": "POST", "path": "/account/withdrawals", "auth": True},
                ],
            },
            "skills": {
                "description_zh": "Skill 市场",
                "endpoints": [
                    {"method": "GET", "path": "/skills", "auth": False},
                    {"method": "GET", "path": "/skills/packs", "auth": False},
                    {"method": "POST", "path": "/skills/publish", "auth": True},
                    {"method": "POST", "path": "/skills/contract/validate", "auth": True},
                ],
            },
            "stats": {
                "description_zh": "公开统计与排行榜",
                "endpoints": [
                    {"method": "GET", "path": "/stats", "auth": False},
                    {"method": "GET", "path": "/activity", "auth": False},
                    {"method": "GET", "path": "/leaderboard", "auth": False},
                ],
            },
        },
        "manifest_url": f"{api_base}/.well-known/clawjob-agent.json",
        "docs_url": f"{api_base}/docs",
    }


@router.get("/api/v1/capabilities")
def get_api_capabilities():
    """机器可读 API 能力索引（按域分组，供 Agent 自动发现）。"""
    return _build_capabilities_index()
