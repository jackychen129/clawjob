"""Extracted from main.py — API paths unchanged."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.systems import runtime_guard, task_system
from app.database.relational_db import (
    Agent, CreditTransaction, ExecutionRun, ExecutionStep, PublishedAgentTemplate,
    PublishedSkill, SystemLog, Task, TaskBid, TaskComment, TaskSubscription, User, get_db,
)
from app.domain.agent_helpers import (
    RegisterAgentBody, SendMessageBody, ensure_agents_category_column,
    get_my_agent, norm_capabilities, published_skill_ids_by_token,
)
from app.domain.skill_xp import agent_skill_xp_map, level_from_xp
from app.domain.task_helpers import (
    CLAWJOB_SYSTEM_AGENT_NAME, CLAWJOB_SYSTEM_USERNAME, FRONTEND_URL,
    a2a_can_access_task, append_task_status_update_comment, award_bid_impl,
    can_view_task_runs, compute_publish_fee, get_or_create_clawjob_system_agent,
    intent_rate_check, maybe_auto_confirm, maybe_settle_skill_revenue, owner_display_name,
    pay_task_reward, push_task_to_discord, require_auction_task, serialize_auction_state,
    task_extra, task_is_public_listing, task_is_visible_to, task_payment_breakdown,
    task_verification_hours, validate_verification_submission,
)
from app.domain.task_models import (
    A2AMessageBody, BatchConfirmBody, CloseAuctionBody, ConfirmTaskBody, EscrowDisputeBody,
    PaymentProfileBody, PlaceBidBody, PostCommentBody, PublishTaskBody, RejectCompletionBody,
    SubscribeTaskBody, SubmitCompletionBody, WorkflowPlanBody,
)
from app.security import get_current_user, get_current_user_optional
from app.services import execution_sandbox as _sandbox, reverse_auction as _ra
from app.services import safety_pipeline as _safety, step_replay as _replay
from app.services.escrow_tasks import apply_escrow_milestone_confirm, build_escrow_plan, get_escrow, save_escrow_to_task
from app.services.preflight import enforce_preflight, run_preflight
from app.services import payout as _payout
from app.services import settlement as _settlement
from app.services.task_timeline import append_timeline_event as _append_timeline_event
from app.services.workflow_dag import predecessors, validate_workflow_dag
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["agents"])

@router.post("/agents/register")
def register_agent(
    body: RegisterAgentBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """注册我的 Agent（需登录），用于接取/订阅他人任务。调用方须提供：当前使用的 token（请求头 Authorization: Bearer <token>）与 Agent 名称（Body 的 name）。参数对齐 OpenClaw/Clawl agent。"""
    preflight = enforce_preflight("agent_register")
    ensure_agents_category_column()
    uid = int(current_user["user_id"])
    primary_type = (body.agent_type or "general").strip() or "general"
    if body.types and len(body.types) > 0:
        primary_type = (body.types[0] or primary_type).strip() or primary_type
    capabilities = norm_capabilities(body.capabilities) if body.capabilities else []
    config = {}
    if body.token and body.token.strip():
        config["agent_token"] = body.token.strip()
    if getattr(body, "skill_bound_token", None) and str(body.skill_bound_token).strip():
        config["skill_bound_token"] = str(body.skill_bound_token).strip()
    if body.avatar_url and body.avatar_url.strip():
        config["avatar_url"] = body.avatar_url.strip()
    if body.profile_url and body.profile_url.strip():
        config["profile_url"] = body.profile_url.strip()
    if body.webhook_url and body.webhook_url.strip():
        config["webhook_url"] = body.webhook_url.strip()
    is_active = (body.status or "active").strip().lower() != "inactive"
    category = (body.category or "api").strip().lower() or "api"
    if category not in ("skill", "mcp", "web", "api"):
        category = "api"
    agent = Agent(
        name=body.name.strip(),
        description=(body.description or "").strip(),
        agent_type=primary_type,
        category=category,
        owner_id=uid,
        capabilities=capabilities,
        config=config,
        is_active=is_active,
    )
    db.add(agent)
    try:
        db.commit()
        db.refresh(agent)
        try:
            db.add(SystemLog(
                level="info",
                category="agent",
                message="agent_registered",
                user_id=uid,
                extra={"agent_id": agent.id, "agent_name": agent.name, "category": category},
            ))
            db.commit()
        except Exception:
            db.rollback()
    except Exception as e:
        db.rollback()
        err_msg = str(e).lower()
        # NOTE: translated comment in English.
        if "category" in err_msg or "does not exist" in err_msg or "column" in err_msg:
            ensure_agents_category_column()
            agent_retry = Agent(
                name=body.name.strip(),
                description=(body.description or "").strip(),
                agent_type=primary_type,
                category=category,
                owner_id=uid,
                capabilities=capabilities,
                config=config,
                is_active=is_active,
            )
            db.add(agent_retry)
            db.commit()
            db.refresh(agent_retry)
            agent = agent_retry
            try:
                db.add(SystemLog(
                    level="info",
                    category="agent",
                    message="agent_registered",
                    user_id=uid,
                    extra={"agent_id": agent.id, "agent_name": agent.name, "category": category, "note": "retry_after_schema_fix"},
                ))
                db.commit()
            except Exception:
                db.rollback()
        else:
            raise
    return {
        "id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "category": getattr(agent, "category", None) or "api",
        "capabilities": agent.capabilities or [],
        "status": "active" if agent.is_active else "inactive",
        "preflight": preflight,
    }


def published_skill_ids_by_token(db: Session, agents: List[Agent]) -> dict:
    """skill_bound_token -> PublishedSkill.id，用于前端展示「Skill 已上架」。"""
    tokens = set()
    for a in agents:
        cfg = a.config or {}
        tok = (cfg.get("skill_bound_token") or "").strip()
        if tok:
            tokens.add(tok)
    if not tokens:
        return {}
    rows = db.query(PublishedSkill).filter(PublishedSkill.skill_token.in_(list(tokens))).all()
    return {r.skill_token: r.id for r in rows}


@router.get("/agents/mine")
def list_my_agents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我注册的 Agent 列表（需登录），按积分（完成任务获得）降序。线上容错：查询失败时补列并重试或返回空列表。"""
    ensure_agents_category_column()
    uid = int(current_user["user_id"])

    def _build_agent_item(
        a: Agent,
        points: int = 0,
        published_template_id: Optional[int] = None,
        completed_task_count: int = 0,
        published_skill_id: Optional[int] = None,
    ) -> dict:
        cfg = a.config or {}
        return {
            "id": a.id,
            "name": a.name,
            "description": a.description or "",
            "agent_type": a.agent_type or "general",
            "category": getattr(a, "category", None) or "api",
            "capabilities": a.capabilities or [],
            "status": "active" if a.is_active else "inactive",
            "config": cfg,
            "has_skill_token": bool(cfg.get("skill_bound_token")),
            "points": int(points),
            "published_template_id": published_template_id,
            "published_skill_id": published_skill_id,
            "completed_task_count": completed_task_count,
        }

    try:
        points_subq = (
            db.query(Task.agent_id, func.coalesce(func.sum(Task.reward_points), 0).label("points"))
            .filter(Task.status == "completed", Task.agent_id.isnot(None))
            .group_by(Task.agent_id)
            .subquery()
        )
        completed_subq = (
            db.query(Task.agent_id, func.count(Task.id).label("completed_count"))
            .filter(Task.status == "completed", Task.agent_id.isnot(None))
            .group_by(Task.agent_id)
            .subquery()
        )
        agent_ids = [r[0] for r in db.query(Agent.id).filter(Agent.owner_id == uid).all()]
        published_by_agent = {t.agent_id: t.id for t in db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.agent_id.in_(agent_ids)).all()} if agent_ids else {}
        rows = (
            db.query(Agent, func.coalesce(points_subq.c.points, 0).label("points"), func.coalesce(completed_subq.c.completed_count, 0).label("completed_count"))
            .outerjoin(points_subq, Agent.id == points_subq.c.agent_id)
            .outerjoin(completed_subq, Agent.id == completed_subq.c.agent_id)
            .filter(Agent.owner_id == uid)
            .order_by(points_subq.c.points.desc().nullslast(), Agent.id.desc())
            .all()
        )
        agents_only = [a for a, _, _ in rows]
        skill_id_by_token = published_skill_ids_by_token(db, agents_only)

        def _skill_pub_id(agent: Agent) -> Optional[int]:
            cfg = agent.config or {}
            tok = (cfg.get("skill_bound_token") or "").strip()
            return skill_id_by_token.get(tok) if tok else None

        return {
            "agents": [
                _build_agent_item(a, points, published_by_agent.get(a.id), int(completed_count), _skill_pub_id(a))
                for a, points, completed_count in rows
            ]
        }
    except Exception as e:
        db.rollback()
        err_msg = str(e).lower()
        if "column" in err_msg or "does not exist" in err_msg or "category" in err_msg:
            ensure_agents_category_column()
        try:
            agents = db.query(Agent).filter(Agent.owner_id == uid).order_by(Agent.id.desc()).all()
            aid_list = [a.id for a in agents]
            pub = {t.agent_id: t.id for t in db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.agent_id.in_(aid_list)).all()} if aid_list else {}
            completed_map = {r[0]: r[1] for r in db.query(Task.agent_id, func.count(Task.id)).filter(Task.status == "completed", Task.agent_id.in_(aid_list)).group_by(Task.agent_id).all()} if aid_list else {}
            skill_id_by_token = published_skill_ids_by_token(db, agents)

            def _skill_pub_id_fb(agent: Agent) -> Optional[int]:
                cfg = agent.config or {}
                tok = (cfg.get("skill_bound_token") or "").strip()
                return skill_id_by_token.get(tok) if tok else None

            return {
                "agents": [
                    _build_agent_item(a, 0, pub.get(a.id), completed_map.get(a.id, 0), _skill_pub_id_fb(a))
                    for a in agents
                ]
            }
        except Exception:
            db.rollback()
            return {"agents": []}


def get_my_agent(agent_id: int, db: Session, user_id: int) -> Optional[Agent]:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.owner_id != user_id:
        return None
    return agent


@router.get("/agents/{agent_id}/ping")
def agent_ping(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """探测 Agent 是否存活：对配置的 webhook_url 发 GET 请求，仅 Agent 所有者可调用。"""
    uid = int(current_user["user_id"])
    agent = get_my_agent(agent_id, db, uid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or not yours")
    config = agent.config or {}
    webhook_url = (config.get("webhook_url") or "").strip()
    if not webhook_url:
        return {"alive": False, "reason": "no_webhook", "message": "未配置 Webhook URL"}
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(webhook_url)
            return {"alive": 200 <= r.status_code < 400, "status_code": r.status_code}
    except Exception as e:
        return {"alive": False, "reason": "request_failed", "message": str(e)}


@router.post("/agents/{agent_id}/send-message")
def agent_send_message(
    agent_id: int,
    body: SendMessageBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """向 Agent 发送消息：POST 到 webhook_url，仅 Agent 所有者可调用。"""
    uid = int(current_user["user_id"])
    agent = get_my_agent(agent_id, db, uid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or not yours")
    config = agent.config or {}
    webhook_url = (config.get("webhook_url") or "").strip()
    if not webhook_url:
        raise HTTPException(status_code=400, detail="未配置 Webhook URL，无法发送消息")
    try:
        payload = {"type": "message", "content": (body.content or "").strip(), "agent_id": agent_id}
        with httpx.Client(timeout=10.0) as client:
            r = client.post(webhook_url, json=payload)
            return {"sent": 200 <= r.status_code < 400, "status_code": r.status_code, "response": r.text[:500] if r.text else None}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"发送失败: {str(e)}")


@router.get("/candidates")
def list_candidates(
    skip: int = 0,
    limit: int = 100,
    sort: str = "points",  # points | recent（最近注册优先）
    db: Session = Depends(get_db),
):
    """候选者列表（公开）：已注册的 Agent、所属用户（游客显示「待注册」）、具备的 Skill（capabilities）、发布任务数。"""
    from app.domain.agent_public import apply_public_agent_filters, filter_public_agent_rows

    points_subq = (
        db.query(Task.agent_id, func.coalesce(func.sum(Task.reward_points), 0).label("points"))
        .filter(Task.status == "completed", Task.agent_id.isnot(None))
        .group_by(Task.agent_id)
        .subquery()
    )
    published_subq = (
        db.query(Task.creator_agent_id, func.count(Task.id).label("published_count"))
        .filter(Task.creator_agent_id.isnot(None))
        .group_by(Task.creator_agent_id)
        .subquery()
    )
    q = (
        db.query(Agent, User, func.coalesce(points_subq.c.points, 0).label("points"), func.coalesce(published_subq.c.published_count, 0).label("published_count"))
        .join(User, Agent.owner_id == User.id)
        .outerjoin(points_subq, Agent.id == points_subq.c.agent_id)
        .outerjoin(published_subq, Agent.id == published_subq.c.creator_agent_id)
    )
    q = apply_public_agent_filters(q)
    if (sort or "").strip().lower() == "recent":
        q = q.order_by(Agent.id.desc())
    else:
        q = q.order_by(points_subq.c.points.desc().nullslast(), Agent.id.desc())
    fetch_n = max(limit * 3, limit + 20)
    rows = filter_public_agent_rows(q.offset(skip).limit(fetch_n).all())[:limit]
    skill_tokens = set()
    for row in rows:
        a = row[0]
        cfg = a.config or {}
        tok = (cfg.get("skill_bound_token") or "").strip()
        if tok:
            skill_tokens.add(tok)
    published_skill_by_token = {}
    if skill_tokens:
        ps = db.query(PublishedSkill).filter(PublishedSkill.skill_token.in_(list(skill_tokens))).all()
        published_skill_by_token = {x.skill_token: x.id for x in ps}
    out = []
    for row in rows:
        a, owner, points, published_count = row
        cfg = a.config or {}
        skill_token = (cfg.get("skill_bound_token") or "").strip()
        xp_map = agent_skill_xp_map(db, a.id)
        skills = []
        for name, xp in sorted(xp_map.items(), key=lambda kv: (-kv[1], kv[0]))[:5]:
            lv = level_from_xp(int(xp))
            skills.append({"name": name, "xp": int(xp), "level": int(lv.get("level", 1))})
        app_base = os.getenv("CLAWJOB_APP_URL", FRONTEND_URL or "https://app.clawjob.com.cn").rstrip("/")
        owner_username = owner.username if owner else None
        out.append({
            "id": a.id,
            "type": "agent",
            "name": a.name,
            "description": (a.description or "")[:300],
            "agent_type": a.agent_type or "general",
            "capabilities": a.capabilities or [],
            "status": "active" if a.is_active else "inactive",
            "avatar_url": cfg.get("avatar_url"),
            "profile_url": cfg.get("profile_url"),
            "agent_profile_url": f"{app_base}/#/agents/{a.id}",
            "owner_profile_url": f"{app_base}/#/u/{owner_username}" if owner_username else None,
            "owner_id": a.owner_id,
            "owner_name": owner_display_name(owner.username if owner else None),
            "owner_username": owner.username if owner else None,
            "points": int(points),
            "published_count": int(published_count),
            "has_skill_token": bool(skill_token),
            "skill_bound_token": skill_token if skill_token else None,
            "published_skill_id": published_skill_by_token.get(skill_token),
            "skills": skills,
        })
    return {"candidates": out, "total": len(out)}
@router.get("/agents/{agent_id}/tasks")
def list_agent_tasks(
    agent_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """指定 Agent 接取的任务列表（需登录且为该 Agent 的拥有者）"""
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == uid).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在或无权查看")
    q = (
        db.query(Task)
        .filter(Task.agent_id == agent_id)
        .order_by(Task.created_at.desc())
    )
    tasks = q.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **task_extra(t, db),
        })
    return {"tasks": out, "total": len(out), "agent_name": agent.name}


@router.get("/agents/{agent_id}/trust-card")
def get_agent_trust_card(
    agent_id: int,
    db: Session = Depends(get_db),
):
    """Agent 信任卡（公开只读）：完成率、托管单、累计收益、认证 Skill、徽章等，供 Agent 与爬虫读取。"""
    from app.services.trust_card import compute_agent_trust_card

    card = compute_agent_trust_card(db, agent_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return JSONResponse(
        content=card,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/agents/{agent_id}/reputation")
def get_agent_reputation(
    agent_id: int,
    db: Session = Depends(get_db),
):
    """Agent 信誉卡（公开只读）：聚合接取/完成/拒绝/争议/速度/活跃度并给出综合评分。

    - 无需登录；匿名访问任何 Agent 都可。
    - 数据来源：`tasks` 表即时聚合 + `input_data.timeline` 事件 + `input_data.escrow.disputed`。
    - 响应头加 `Cache-Control: public, max-age=300`，5 分钟缓存保护。
    """
    from app.services.reputation import compute_agent_reputation

    card = compute_agent_reputation(db, agent_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return JSONResponse(
        content=card,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/agents/{agent_id}/cases")
def get_agent_case_studies(
    agent_id: int,
    limit: int = 8,
    db: Session = Depends(get_db),
):
    """Agent 公开案例库：返回最近完成的任务摘要，供公开主页 SEO 展示。

    - 公开访问；`Cache-Control: public, max-age=600`。
    - 仅返回 `status=completed` 且非定向（`invitees_only` / 有 invited_agent_ids）任务。
    """
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    limit = max(1, min(int(limit or 8), 20))
    q = (
        db.query(Task)
        .filter(Task.agent_id == agent_id)
        .filter(Task.status == "completed")
        .order_by(desc(Task.completed_at), desc(Task.updated_at))
    )
    rows = q.limit(limit).all()
    cases = []
    for t in rows:
        invited = getattr(t, "invited_agent_ids", None) or []
        if invited:
            continue
        owner = db.query(User).filter(User.id == t.owner_id).first()
        out = t.output_data if isinstance(getattr(t, "output_data", None), dict) else {}
        summary = (out.get("result_summary") or (t.description or "")).strip()
        if len(summary) > 320:
            summary = summary[:317] + "..."
        cases.append({
            "task_id": t.id,
            "title": t.title,
            "category": getattr(t, "category", None),
            "reward_points": int(getattr(t, "reward_points", 0) or 0),
            "publisher_name": owner.username if owner else "",
            "completed_at": iso_utc(getattr(t, "completed_at", None)),
            "summary": summary,
        })
    return JSONResponse(
        content={"agent_id": agent_id, "agent_name": agent.name, "cases": cases, "total": len(cases)},
        headers={"Cache-Control": "public, max-age=600"},
    )


@router.get("/u/{username}")
def get_public_user_profile(
    username: str,
    db: Session = Depends(get_db),
):
    """公开用户主页：按 username 返回 owner + 其公开 Agents + 信誉摘要。

    主要用于 `/@:username` 页面的 SEO 流量入口。不包含邮箱、credits、佣金等敏感信息。
    """
    uname = (username or "").strip().lstrip("@")
    if not uname:
        raise HTTPException(status_code=404, detail="用户不存在")
    user = db.query(User).filter(User.username == uname).first()
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=404, detail="用户不存在")
    from app.services.reputation import compute_agent_reputation

    agents = (
        db.query(Agent)
        .filter(Agent.owner_id == user.id, Agent.is_active == True)  # noqa: E712
        .order_by(Agent.created_at.asc())
        .limit(20)
        .all()
    )
    agent_cards = []
    total_completed = 0
    total_earned = 0
    best_score = 0
    from app.services.trust_card import compute_agent_trust_card

    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    for a in agents:
        card = compute_agent_reputation(db, a.id) or {}
        trust = compute_agent_trust_card(db, a.id) or {}
        score = int(card.get("reputation_score", 0) or 0)
        stats = card.get("stats") or {}
        completed = int(stats.get("completed_task_count", 0) or 0)
        earned = int(stats.get("reward_points_total", 0) or 0)
        total_completed += completed
        total_earned += earned
        best_score = max(best_score, score)
        agent_cards.append({
            "agent_id": a.id,
            "id": a.id,
            "name": a.name,
            "description": (a.description or "")[:400],
            "agent_type": a.agent_type,
            "category": getattr(a, "category", None),
            "capabilities": a.capabilities if isinstance(a.capabilities, list) else [],
            "reputation_score": score,
            "tasks_completed": completed,
            "completed_tasks": completed,
            "top_skills": stats.get("top_skills") or [],
            "trust_card_url": f"{api_base}/agents/{a.id}/trust-card",
            "trust_one_liner_zh": trust.get("one_liner_zh"),
            "badges": trust.get("badges") or [],
        })
    rep_avg = round(best_score, 1) if agent_cards else None
    return JSONResponse(
        content={
            "username": user.username,
            "user_id": user.id,
            "joined_at": iso_utc(user.created_at),
            "agents": agent_cards,
            "summary": {
                "agents_count": len(agent_cards),
                "tasks_completed": total_completed,
                "total_completed_tasks": total_completed,
                "total_rewards_earned": total_earned,
                "total_earned_points": total_earned,
                "reputation_avg": rep_avg,
                "best_reputation_score": best_score,
            },
        },
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/agents/{agent_id}/earnings-summary")
def get_agent_earnings_summary(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Agent 收益摘要：完成单、已赚点数、待验收、账户余额与平台开放任务数（仅拥有者可读）。"""
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    if int(agent.owner_id) != uid:
        raise HTTPException(status_code=403, detail="仅 Agent 拥有者可查看收益摘要")

    completed_q = db.query(Task).filter(Task.agent_id == agent.id, Task.status == "completed")
    tasks_completed = completed_q.count()
    points_earned = (
        db.query(func.coalesce(func.sum(Task.reward_points), 0))
        .filter(Task.agent_id == agent.id, Task.status == "completed")
        .scalar()
        or 0
    )
    pending_verification = (
        db.query(Task)
        .filter(Task.agent_id == agent.id, Task.status == "pending_verification")
        .count()
    )
    in_progress = (
        db.query(Task).filter(Task.agent_id == agent.id, Task.status == "in_progress").count()
    )
    need_submit = (
        db.query(Task)
        .filter(Task.agent_id == agent.id, Task.status.in_(("open", "in_progress")))
        .count()
    )
    user = db.query(User).filter(User.id == uid).first()
    credits = int(getattr(user, "credits", 0) or 0) if user else 0
    commission = int(getattr(user, "commission_balance", 0) or 0) if user else 0
    withdrawable = credits + commission
    payout = _payout.compute_payout_eligibility(db, user) if user else None
    tasks_open_platform = db.query(Task).filter(Task.status == "open").count()

    from app.services.reputation import compute_agent_reputation

    rep = compute_agent_reputation(db, agent.id) or {}
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "tasks_completed": int(tasks_completed),
        "reward_points_earned": int(points_earned),
        "pending_verification": int(pending_verification),
        "in_progress": int(in_progress),
        "need_submit": int(need_submit),
        "credits_balance": credits,
        "commission_balance": commission,
        "withdrawable_balance": withdrawable,
        "payout": payout,
        "reputation_score": int(rep.get("score", 0) or 0),
        "platform_tasks_open": int(tasks_open_platform),
        "money_path_hint_zh": "接取开放任务 → 提交完成 → 发布方验收 → Agent 间直接打款（settlement_mode=agent_direct）或平台 credits 入账 → 配置收款方式",
        "money_path_hint_en": "Subscribe → submit → confirm → agent_direct settlement (P2P) or platform credits → configure payment profile.",
        "settlement_api": {
            "payment_profile": f"{api_base}/agents/{agent.id}/payment-profile",
            "settlement_flow": "GET/POST /tasks/{{task_id}}/settlement/*",
        },
        "links": {
            "task_radar": f"{api_base}/agents/{agent.id}/task-radar",
            "browse_open_tasks": f"{api_base}/tasks?status_filter=open&limit=20",
            "tasks_hall": f"{app_base}/#/tasks",
            "skill_packs": f"{api_base}/skills/packs",
            "agent_manifest": f"{api_base}/.well-known/clawjob-agent.json",
            "payout_eligibility": f"{api_base}/account/payout-eligibility",
            "account_payout": f"{app_base}/#/account",
        },
    }


@router.get("/agents/{agent_id}/task-radar")
def get_agent_task_radar(
    agent_id: int,
    k: int = 10,
    w_skill: Optional[float] = None,
    w_reward: Optional[float] = None,
    w_fresh: Optional[float] = None,
    w_history: Optional[float] = None,
    reward_min: Optional[int] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """任务雷达：面向 Agent 拥有者的实时撮合排名。

    - 仅 Agent 的拥有者可调用（避免别人的雷达视角泄露）。
    - 通过 `w_skill/w_reward/w_fresh/w_history` 调节四个因子权重（未传则用默认值）。
    - `reward_min` / `category` 可进一步过滤候选池。
    - 返回 Top-K 任务 + 每项的 breakdown 与理由；若任务是定向任务但 Agent 是被邀请方，
      会自动纳入雷达并获得 +20 曝光加成。
    """
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    if int(agent.owner_id) != uid:
        raise HTTPException(status_code=403, detail="仅 Agent 拥有者可查看任务雷达")
    if getattr(agent, "is_active", True) is False:
        raise HTTPException(status_code=400, detail="已停用的 Agent 不支持任务雷达")

    weights: Dict[str, float] = {}
    if w_skill is not None:
        weights["skill_match"] = float(w_skill)
    if w_reward is not None:
        weights["reward_fit"] = float(w_reward)
    if w_fresh is not None:
        weights["freshness"] = float(w_fresh)
    if w_history is not None:
        weights["history_affinity"] = float(w_history)

    from app.services.task_radar import compute_task_radar

    try:
        result = compute_task_radar(
            db,
            agent.id,
            k=k,
            weights=weights or None,
            reward_min=reward_min,
            category=category,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "private, max-age=30"},
    )


@router.get("/agents/{agent_id}/payment-profile")
def get_agent_payment_profile(
    agent_id: int,
    task_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取 Agent 收款方式。拥有者始终可读；交易对手在 subscribe 后或待验收/结算阶段可读。"""
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    task = None
    if task_id is not None:
        task = db.query(Task).filter(Task.id == int(task_id)).first()
    if int(agent.owner_id) != uid:
        if task is None:
            raise HTTPException(status_code=403, detail="须提供 task_id 以验证交易对手身份")
        if not _settlement.can_view_agent_payment_profile(task, agent, uid, db):
            raise HTTPException(status_code=403, detail="无权查看该 Agent 收款方式")
    profile = _settlement.get_payment_profile(agent)
    return {"agent_id": agent.id, "payment_profile": profile}


@router.put("/agents/{agent_id}/payment-profile")
def put_agent_payment_profile(
    agent_id: int,
    body: PaymentProfileBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """配置 Agent 收款方式（仅拥有者可写）。"""
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == int(agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    if int(agent.owner_id) != uid:
        raise HTTPException(status_code=403, detail="仅 Agent 拥有者可配置收款方式")
    profile = _settlement.validate_payment_profile({"methods": [m.model_dump() for m in body.methods]})
    _settlement.set_agent_payment_profile(agent, profile)
    db.commit()
    return {"ok": True, "agent_id": agent.id, "payment_profile": profile}
