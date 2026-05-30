"""Extracted from main.py — API paths unchanged."""
from __future__ import annotations

import asyncio
import copy
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.systems import runtime_guard, task_system
from app.database.relational_db import (
    Agent, CreditTransaction, ExecutionRun, ExecutionStep, PublishedSkill, SystemLog, Task, TaskBid,
    TaskComment, TaskSubscription, User, get_db,
)
from app.domain.agent_helpers import ensure_agents_category_column, get_my_agent, norm_capabilities, published_skill_ids_by_token, RegisterAgentBody, SendMessageBody
from app.domain.skill_xp import agent_skill_token, agent_skill_xp_map, level_from_xp
from app.domain.task_helpers import (
    CLAWJOB_SYSTEM_AGENT_NAME, CLAWJOB_SYSTEM_USERNAME, FRONTEND_URL,
    MAX_TASK_REWARD_POINTS, PLATFORM_COMMISSION_RATE,
    VERIFICATION_EXTEND_HOURS, VERIFICATION_HOURS_DEFAULT, VERIFICATION_HOURS_MAX, VERIFICATION_HOURS_MIN,
    a2a_can_access_task, append_task_status_update_comment, award_bid_impl,
    can_view_task_runs, compute_publish_fee, get_or_create_clawjob_system_agent,
    intent_rate_check, maybe_auto_confirm, maybe_settle_skill_revenue, normalize_verification_method, owner_display_name,
    pay_task_reward, push_task_to_discord, require_auction_task, serialize_auction_state,
    task_extra, task_is_platform_seed_listing, task_is_public_listing, task_is_visible_to, task_payment_breakdown,
    task_verification_hours, validate_verification_submission,
)
from app.domain.task_models import (
    A2AMessageBody, BatchConfirmBody, CloseAuctionBody, ConfirmTaskBody, EscrowDisputeBody,
    PlaceBidBody, PostCommentBody, PublishTaskBody, RejectCompletionBody, SubscribeTaskBody,
    SubmitCompletionBody, WorkflowPlanBody,
)
from app.security import get_current_user, get_current_user_optional
from app.services import execution_sandbox as _sandbox, reverse_auction as _ra
from app.services import safety_pipeline as _safety, step_replay as _replay
from app.services.escrow_tasks import apply_escrow_milestone_confirm, build_escrow_plan, get_escrow, save_escrow_to_task
from app.services.preflight import enforce_preflight, run_preflight
from app.services.task_timeline import append_timeline_event as _append_timeline_event
from app.services.workflow_dag import predecessors, validate_workflow_dag
from app.utils.datetime_iso import iso_utc

router = APIRouter()

@router.get("/tasks/mine")
def list_my_accepted_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我接取的任务：当前用户通过其 Agent 接取的任务（需登录）"""
    uid = int(current_user["user_id"])
    my_agent_ids = [a.id for a in db.query(Agent.id).filter(Agent.owner_id == uid).all()]
    if not my_agent_ids:
        return {"tasks": [], "total": 0}
    q = (
        db.query(Task)
        .filter(Task.agent_id.in_(my_agent_ids))
        .order_by(Task.created_at.desc())
    )
    tasks = q.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        agent = db.query(Agent).filter(Agent.id == t.agent_id).first()
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "task_type": t.task_type or "general",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "agent_id": t.agent_id,
            "agent_name": agent.name if agent else "",
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **task_extra(t, db),
        })
    return {"tasks": out, "total": len(out)}
@router.post("/tasks/draft-from-intent")
def draft_task_from_intent(
    body: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """一句话需求 → 任务草稿（Intent-to-Task）。

    - 默认启发式解析（免费、零外部依赖），命中技能/类别/难度/期限/预算等。
    - 设置 `OPENAI_API_KEY` 且传 `use_llm=true` 时调用 LLM 润色；失败自动回退启发式。
    - 每用户限频：默认 30 次/小时（`CLAWJOB_INTENT_RATE_PER_HOUR`）。
    - 返回的草稿带 `draft_source="intent"` 标记，前端落库时应一并写入 `input_data` 做审计。
    """
    from app.services.intent_parser import parse_intent

    uid = int(current_user["user_id"])
    ok, reset_in = intent_rate_check(uid)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail=f"调用过于频繁，请 {reset_in} 秒后重试",
            headers={"Retry-After": str(reset_in)},
        )

    intent = str(body.get("intent") or "").strip()
    if not intent:
        raise HTTPException(status_code=400, detail="intent 不可为空")
    if len(intent) > 2000:
        raise HTTPException(status_code=400, detail="intent 过长（超过 2000 字）")
    use_llm = bool(body.get("use_llm") or False)

    try:
        draft = parse_intent(intent, use_llm=use_llm)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    draft["draft_source"] = "intent"
    draft["user_id"] = uid
    return draft


@router.get("/tasks/estimate")
def estimate_task_price_sla(
    skill: Optional[str] = None,
    kind: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """价格与 SLA 预估（公开）。

    - 依据历史任务（最近 500 单相似样本）聚合出奖励点的中位数与 p25/p75/p90 分位、
      预估完成时长（p50/p75）、预估接取等待时长（p50/p75）。
    - `difficulty` 可选 `easy|normal|hard|expert`，对输出做乘数修正。
    - 样本不足 5 条时自动走启发式回退（按 skill → category → 全局默认表）。
    - 响应头加 5 分钟缓存；服务内部还有 5 分钟 LRU。
    """
    from app.services.price_sla_estimator import estimate_price_sla

    result = estimate_price_sla(
        db,
        skill=skill,
        kind=kind,
        category=category,
        difficulty=difficulty,
    )
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/tasks")
def list_tasks_public(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    category_filter: str = None,
    creator_agent_id: Optional[int] = None,
    q: str = None,
    sort: str = "created_at_desc",
    reward_min: Optional[int] = None,
    reward_max: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """任务大厅：公开列出所有任务（无需登录）；支持分类、关键词、奖励区间、排序；creator_agent_id 可筛选某 Agent 发布的任务。

    若任务是「定向任务」（`input_data.visibility == invitees_only`），仅发布者与被邀请 Agent 的拥有者可见。
    """
    # 内部/握手/平台系统账号任务不进入公开大厅与计数。
    system_owner_ids = [
        int(u.id)
        for u in db.query(User.id).filter(User.username == CLAWJOB_SYSTEM_USERNAME).all()
    ]

    # 尝试在 SQL 层过滤 input_data.hidden_from_public（仅在 PostgreSQL 下生效，
    # SQLite 测试环境继续依赖 Python 层的 task_is_public_listing 过滤）。
    def _apply_hidden_filter(qy):
        try:
            dialect = db.bind.dialect.name if db.bind is not None else ""
        except Exception:
            dialect = ""
        if dialect != "postgresql":
            return qy
        try:
            from sqlalchemy import or_ as _or
            hidden_expr = Task.input_data.op("->>")("hidden_from_public")
            # NULL (字段不存在) 视为未隐藏；仅当显式为 'true'/'1' 时才过滤。
            return qy.filter(
                _or(
                    Task.input_data.is_(None),
                    hidden_expr.is_(None),
                    hidden_expr.notin_(("true", "True", "1")),
                )
            )
        except Exception:
            return qy

    def _apply_public_filters(qy):
        if status_filter:
            qy = qy.filter(Task.status == status_filter)
        else:
            qy = qy.filter(Task.status != "cancelled_refunded")
        if category_filter and category_filter.strip():
            qy = qy.filter(Task.category == category_filter.strip())
        if creator_agent_id is not None:
            qy = qy.filter(Task.creator_agent_id == creator_agent_id)
        if q and q.strip():
            from sqlalchemy import or_
            term = f"%{q.strip()}%"
            qy = qy.filter(or_(Task.title.ilike(term), Task.description.ilike(term)))
        if reward_min is not None:
            qy = qy.filter(Task.reward_points >= reward_min)
        if reward_max is not None:
            qy = qy.filter(Task.reward_points <= reward_max)
        if system_owner_ids:
            try:
                dialect = db.bind.dialect.name if db.bind is not None else ""
            except Exception:
                dialect = ""
            if dialect == "postgresql":
                from sqlalchemy import or_ as _or
                src_expr = Task.input_data.op("->>")("source")
                showcase_expr = Task.input_data.op("->>")("showcase")
                qy = qy.filter(
                    _or(
                        ~Task.owner_id.in_(system_owner_ids),
                        src_expr == "seed_open_tasks",
                        showcase_expr.in_(("true", "True", "1")),
                    )
                )
        qy = _apply_hidden_filter(qy)
        return qy

    query = _apply_public_filters(db.query(Task))
    if sort == "comments_desc":
        query = _apply_public_filters(
            db.query(Task, func.count(TaskComment.id).label("comment_count")).outerjoin(
                TaskComment, Task.id == TaskComment.task_id
            )
        )
        query = query.group_by(Task.id).order_by(func.count(TaskComment.id).desc().nullslast(), Task.created_at.desc())
        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        tasks_with_count = [(row[0], row[1]) for row in rows]
    else:
        if sort == "reward_desc":
            query = query.order_by(Task.reward_points.desc().nullslast(), Task.created_at.desc())
        elif sort == "created_at_asc":
            query = query.order_by(Task.created_at.asc())
        elif sort == "deadline_asc":
            query = query.order_by(Task.verification_deadline_at.asc().nullslast(), Task.created_at.desc())
        else:
            query = query.order_by(Task.created_at.desc())
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        tasks_with_count = [(t, db.query(TaskComment).filter(TaskComment.task_id == t.id).count()) for t in tasks]
    viewer_uid: Optional[int] = None
    viewer_agent_ids: List[int] = []
    if current_user:
        try:
            viewer_uid = int(current_user.get("user_id")) if current_user.get("user_id") is not None else None
        except (TypeError, ValueError):
            viewer_uid = None
        if viewer_uid is not None:
            viewer_agent_ids = [int(a.id) for a in db.query(Agent.id).filter(Agent.owner_id == viewer_uid).all()]

    out = []
    for t, comment_count in tasks_with_count:
        maybe_auto_confirm(t, db)
        db.refresh(t)
        if not task_is_visible_to(t, viewer_uid, viewer_agent_ids):
            continue
        owner = db.query(User).filter(User.id == t.owner_id).first()
        if not task_is_public_listing(t, owner) and viewer_uid != t.owner_id:
            continue
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        invited = getattr(t, "invited_agent_ids", None)
        creator_agent = db.query(Agent).filter(Agent.id == t.creator_agent_id).first() if getattr(t, "creator_agent_id", None) else None
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "task_type": t.task_type or "general",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "agent_id": t.agent_id,
            "creator_agent_id": getattr(t, "creator_agent_id", None),
            "creator_agent_name": creator_agent.name if creator_agent else None,
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "subscription_count": sub_count,
            "comment_count": comment_count,
            "invited_agent_ids": invited if invited else [],
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **task_extra(t, db),
        })
    return JSONResponse(
        content={"tasks": out, "total": total},
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/tasks/created-by-me")
def list_my_created_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """当前用户发布的任务（我创建的任务）。"""
    uid = int(current_user["user_id"])
    query = db.query(Task).filter(Task.owner_id == uid).order_by(Task.created_at.desc())
    tasks = query.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        comment_count = db.query(TaskComment).filter(TaskComment.task_id == t.id).count()
        invited = getattr(t, "invited_agent_ids", None)
        creator_agent = db.query(Agent).filter(Agent.id == t.creator_agent_id).first() if getattr(t, "creator_agent_id", None) else None
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "task_type": t.task_type or "general",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "agent_id": t.agent_id,
            "creator_agent_id": getattr(t, "creator_agent_id", None),
            "creator_agent_name": creator_agent.name if creator_agent else None,
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "subscription_count": sub_count,
            "comment_count": comment_count,
            "invited_agent_ids": invited if invited else [],
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **task_extra(t, db),
        })
    total = db.query(Task).filter(Task.owner_id == uid).count()
    return {"tasks": out, "total": total}


@router.post("/tasks")
def publish_task(
    body: PublishTaskBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布任务（需登录）；若设置 reward_points 则从当前用户信用点扣减"""
    uid = int(current_user["user_id"])
    try:
        safe_title = _safety.sanitize_text(
            None, getattr(body, "title", None), source="publish_task", user_id=uid
        )
        safe_desc = _safety.sanitize_text(
            None, getattr(body, "description", None), source="publish_task", user_id=uid
        )
        safe_requirements = _safety.sanitize_text(
            None, getattr(body, "requirements", None), source="publish_task", user_id=uid
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"内容安全策略：{str(e)}")
    if isinstance(safe_title, str) and safe_title:
        body.title = safe_title
    if safe_desc is not None:
        body.description = safe_desc
    if safe_requirements is not None:
        body.requirements = safe_requirements
    try:
        user = db.query(User).filter(User.id == uid).with_for_update().first()
    except Exception:
        user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    reward_points = max(0, getattr(body, "reward_points", 0) or 0)
    if reward_points > MAX_TASK_REWARD_POINTS:
        raise HTTPException(
            status_code=400,
            detail=f"单任务奖励点数不能超过 {MAX_TASK_REWARD_POINTS}",
        )
    webhook_url = (getattr(body, "completion_webhook_url", None) or "").strip()
    if reward_points > 0:
        if not webhook_url or not webhook_url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="有奖励点的任务必须填写完成回调 URL（completion_webhook_url），用于接取者提交完成时通知发布方验收",
            )
        credits = getattr(user, "credits", 0) or 0
        if credits < reward_points:
            raise HTTPException(
                status_code=400,
                detail=f"信用点不足：当前 {credits}，需要 {reward_points}",
            )
    invited_ids = getattr(body, "invited_agent_ids", None) or []
    invited_ids = [int(x) for x in invited_ids if x is not None] if invited_ids else None
    creator_agent_id = getattr(body, "creator_agent_id", None)
    if creator_agent_id is not None:
        agent = db.query(Agent).filter(Agent.id == int(creator_agent_id), Agent.owner_id == uid).first()
        if not agent:
            raise HTTPException(status_code=400, detail="creator_agent_id 须为当前用户注册的 Agent")
    extra = {}
    if getattr(body, "location", None):
        extra["location"] = (body.location or "").strip()[:200]
    if getattr(body, "duration_estimate", None):
        extra["duration_estimate"] = (body.duration_estimate or "").strip()[:50]
    if getattr(body, "skills", None) and isinstance(body.skills, list):
        extra["skills"] = [str(s).strip()[:50] for s in body.skills if s][:20]
    related_skill_token = (getattr(body, "related_skill_token", None) or "").strip()
    if related_skill_token:
        if not db.query(PublishedSkill).filter(PublishedSkill.skill_token == related_skill_token).first():
            raise HTTPException(status_code=400, detail="related_skill_token 对应的 Skill 尚未发布")
        extra["related_skill_token"] = related_skill_token
    verification_method = normalize_verification_method(getattr(body, "verification_method", "manual_review"))
    verification_requirements = [
        str(x).strip()[:200]
        for x in (getattr(body, "verification_requirements", None) or [])
        if str(x).strip()
    ][:20]
    if verification_method in ("checklist", "hybrid") and not verification_requirements:
        raise HTTPException(status_code=400, detail="checklist/hybrid 验收方式必须提供 verification_requirements")
    extra["verification_method"] = verification_method
    if verification_requirements:
        extra["verification_requirements"] = verification_requirements
    if not related_skill_token and creator_agent_id is not None:
        creator_tok = agent_skill_token(db, int(creator_agent_id))
        if creator_tok:
            extra["related_skill_token"] = creator_tok
    vh_raw = getattr(body, "verification_hours", None)
    if vh_raw is None:
        extra["verification_hours"] = VERIFICATION_HOURS_DEFAULT
    else:
        try:
            vh = int(vh_raw)
            extra["verification_hours"] = max(VERIFICATION_HOURS_MIN, min(VERIFICATION_HOURS_MAX, vh))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="verification_hours 须为整数")
    category = (getattr(body, "category", None) or "").strip()[:64] or None
    requirements = (getattr(body, "requirements", None) or "").strip() or None
    # NOTE: translated comment in English.
    em = getattr(body, "escrow_milestones", None) or []
    if em:
        try:
            plan = build_escrow_plan(
                [{"title": x.title, "weight": x.weight, "acceptance_criteria": getattr(x, "acceptance_criteria", "")} for x in em],
                reward_points,
            )
            extra["escrow"] = plan
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    auction_cfg = getattr(body, "auction", None)
    if auction_cfg and getattr(auction_cfg, "enabled", False):
        if em:
            raise HTTPException(status_code=400, detail="反向竞标与里程碑托管不能同时开启")
        if reward_points <= 0:
            raise HTTPException(status_code=400, detail="开启反向竞标须同时设置 reward_points 作为上限预算")
        if not webhook_url:
            raise HTTPException(status_code=400, detail="开启反向竞标须填写 completion_webhook_url")
        try:
            extra["auction"] = _ra.build_auction_plan(
                max_reward=reward_points,
                min_reward=int(getattr(auction_cfg, "min_reward", 0) or 0),
                deadline=(getattr(auction_cfg, "deadline", None) or None),
                auto_pick=(getattr(auction_cfg, "auto_pick", "manual") or "manual"),
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if bool(getattr(body, "collaborative", False)):
        extra["collaborative"] = True
    task = Task(
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        priority=body.priority,
        status="open",
        owner_id=uid,
        agent_id=None,
        creator_agent_id=int(creator_agent_id) if creator_agent_id is not None else None,
        reward_points=reward_points,
        completion_webhook_url=webhook_url if webhook_url else None,
        invited_agent_ids=invited_ids if invited_ids else None,
        category=category,
        requirements=requirements,
        input_data=extra if extra else None,
    )
    db.add(task)
    try:
        db.flush()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="发布任务失败")
    if reward_points > 0:
        current_credits = int(getattr(user, "credits", 0) or 0)
        if current_credits < reward_points:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"信用点不足：当前 {current_credits}，需要 {reward_points}",
            )
        user.credits = current_credits - reward_points
        db.add(
            CreditTransaction(
                user_id=uid,
                amount=-reward_points,
                type="task_publish",
                ref_id=task.id,
                remark=f"发布任务 #{task.id} 扣除 {reward_points} 任务点",
            )
        )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="发布任务扣款失败，请稍后重试")
    db.refresh(task)
    try:
        vh = task_verification_hours(task)
        _append_timeline_event(task, "published", f"任务已发布（验收窗口 {vh} 小时，超时自动确认发奖）")
        db.commit()
    except Exception:
        db.rollback()
    try:
        db.add(SystemLog(
            level="info",
            category="task",
            message="task_published",
            user_id=uid,
            extra={"task_id": task.id, "reward_points": reward_points, "category": category},
        ))
        db.commit()
    except Exception:
        db.rollback()
    # NOTE: translated comment in English.
    auto_complete_enabled = os.getenv("AUTO_COMPLETE_FIRST_TASK", "").strip().lower() in ("1", "true", "yes", "on")
    # NOTE: translated comment in English.
    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
    if os.getenv("ENV", "").strip().lower() == "production":
        auto_complete_enabled = True
    first_task_count = db.query(Task).filter(Task.owner_id == uid).count()
    if first_task_count == 1 and auto_complete_enabled and not is_pytest and not get_escrow(task):
        try:
            _, clawjob_agent = get_or_create_clawjob_system_agent(db)
            sub = TaskSubscription(task_id=task.id, agent_id=clawjob_agent.id)
            db.add(sub)
            task.agent_id = clawjob_agent.id
            task.status = "completed"
            task.submitted_at = datetime.utcnow()
            task.completed_at = datetime.utcnow()
            base = task.output_data if isinstance(task.output_data, dict) else {}
            task.output_data = {
                **base,
                "result_summary": "首个任务由 ClawJob 引导 Agent 自动完成，便于体验流程。",
                "auto_completed_by": CLAWJOB_SYSTEM_AGENT_NAME,
            }
            if reward_points > 0:
                pay_task_reward(task, db)
            try:
                from app.services import community_task_hooks as _ct_hooks

                _ct_hooks.on_task_completed_community_hooks(db, task)
            except Exception:
                pass
            db.commit()
            db.refresh(task)
        except Exception:
            db.rollback()
    discord_webhook = (getattr(body, "discord_webhook_url", None) or "").strip()
    if discord_webhook:
        push_task_to_discord(task, discord_webhook, FRONTEND_URL)
    return {"id": task.id, "title": task.title, "status": task.status, "reward_points": reward_points}


@router.post("/workflows/plan")
def plan_workflow(
    body: WorkflowPlanBody,
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    ok, message, topo = validate_workflow_dag(body.nodes, body.edges or [])
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "topo_order": topo, "nodes": body.nodes, "edges": body.edges or []}


@router.post("/tasks/{task_id}/workflow")
def attach_task_workflow(
    task_id: int,
    body: WorkflowPlanBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    ok, message, topo = validate_workflow_dag(body.nodes, body.edges or [])
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可绑定工作流")
    if task_id not in [int(n) for n in body.nodes]:
        raise HTTPException(status_code=400, detail="当前 task_id 必须出现在 workflow nodes 中")
    base = dict(task.input_data) if isinstance(task.input_data, dict) else {}
    workflow_dag = {"nodes": [int(x) for x in body.nodes], "edges": body.edges or [], "topo_order": topo}
    task.input_data = {**base, "workflow_dag": workflow_dag}
    db.commit()
    return {"ok": True, "task_id": task_id, "workflow_dag": workflow_dag}


@router.get("/tasks/{task_id}/workflow")
def get_task_workflow(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    dag = extra.get("workflow_dag") if isinstance(extra.get("workflow_dag"), dict) else None
    if not dag:
        return {"task_id": task_id, "workflow_dag": None, "ready": True, "blocked_by": []}
    blocked: List[int] = []
    for pid in predecessors(task_id, dag.get("edges") or []):
        p = db.query(Task).filter(Task.id == pid).first()
        if not p or p.status != "completed":
            blocked.append(pid)
    return {"task_id": task_id, "workflow_dag": dag, "ready": len(blocked) == 0, "blocked_by": blocked}


@router.get("/tasks/{task_id}/recommend-candidates")
def recommend_task_candidates(
    task_id: int,
    k: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布方视角的候选人智能推荐（Top-K）。

    - 仅发布者可调用（避免竞品信息泄露）。
    - 返回候选人信誉卡 + 综合匹配分 + 建议报价（基于相似任务中位价）。
    """
    from app.services.candidate_recommend import recommend_candidates_for_task

    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可查看推荐候选人")
    try:
        result = recommend_candidates_for_task(db, task_id, k=k, exclude_owner_id=uid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/tasks/{task_id}/invite-agent")
def invite_agent_to_task(
    task_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布方一键邀请 Agent 成为任务的候选接取人。

    - 把 `agent_id` 加入 `invited_agent_ids`；一旦有至少一个邀请，任务默认变成定向任务
      （`input_data.visibility = "invitees_only"`），非被邀请人在公开列表中看不到该任务。
    - 仅在 `task.status in {open, pending}` 且尚未被接取时可调用，幂等（重复邀请不报错）。
    """
    uid = int(current_user["user_id"])
    try:
        agent_id = int(body.get("agent_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="agent_id 必填")
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可邀请候选人")
    if task.status not in {"open", "pending"} or task.agent_id is not None:
        raise HTTPException(status_code=400, detail="仅未被接取的任务可邀请候选人")
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    if agent.owner_id == uid:
        raise HTTPException(status_code=400, detail="不可邀请自己的 Agent")

    invited = list(task.invited_agent_ids or [])
    invited_ints = [int(x) for x in invited if x is not None]
    if agent.id not in invited_ints:
        invited_ints.append(agent.id)
    task.invited_agent_ids = invited_ints

    extra = dict(task.input_data) if isinstance(task.input_data, dict) else {}
    extra["visibility"] = "invitees_only"
    task.input_data = extra

    try:
        _append_timeline_event(task, "agent_invited", f"邀请 Agent「{agent.name}」（#{agent.id}）作为候选接取人")
    except Exception:
        pass
    # NOTE: 给被邀请 Agent 的拥有者写一条站内信
    try:
        recipient_id = int(agent.owner_id)
        if recipient_id != uid:
            db.add(InternalMessage(
                sender_user_id=uid,
                recipient_user_id=recipient_id,
                title=f"你被邀请接取任务 #{task.id}",
                content=f"发布者邀请你的 Agent「{agent.name}」接取任务「{task.title}」。",
                related_task_id=task.id,
            ))
    except Exception:
        pass
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="邀请失败，请稍后重试")
    db.refresh(task)
    return {
        "ok": True,
        "task_id": task.id,
        "invited_agent_ids": [int(x) for x in (task.invited_agent_ids or [])],
        "visibility": "invitees_only",
    }


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布方撤单退款：仅当任务尚未被接取（status=open 且无接取人、未提交）时可取消。

    - 原子性：同一事务中把 `task.status` 置为 `cancelled_refunded`，回退已扣信用点，并写 `CreditTransaction(type=task_publish_refund)`。
    - 幂等：若任务已经处于 `cancelled_refunded`，直接返回成功，不重复退款。
    - 安全：对 Task 和 User 加行级锁 `with_for_update()`；异常自动回滚。
    """
    uid = int(current_user["user_id"])
    try:
        task = db.query(Task).filter(Task.id == task_id).with_for_update().first()
    except Exception:
        task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可撤单")

    if task.status == "cancelled_refunded":
        return {
            "ok": True,
            "idempotent": True,
            "task_id": task.id,
            "status": task.status,
            "refunded_points": 0,
        }

    cancellable_statuses = {"open", "pending"}
    if task.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400,
            detail="任务状态不可撤单：仅未被接取且未提交的任务可撤单",
        )
    if task.agent_id is not None:
        raise HTTPException(status_code=400, detail="任务已被接取，无法撤单；请通过协商或争议流程处理")
    if getattr(task, "submitted_at", None) is not None:
        raise HTTPException(status_code=400, detail="任务已提交待验收，无法撤单")

    reward_points = int(getattr(task, "reward_points", 0) or 0)
    refund_points = 0
    if reward_points > 0:
        already_refunded = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.ref_id == task.id,
                CreditTransaction.type == "task_publish_refund",
                CreditTransaction.user_id == uid,
            )
            .first()
        )
        if not already_refunded:
            try:
                user = db.query(User).filter(User.id == uid).with_for_update().first()
            except Exception:
                user = db.query(User).filter(User.id == uid).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            user.credits = int(getattr(user, "credits", 0) or 0) + reward_points
            db.add(
                CreditTransaction(
                    user_id=uid,
                    amount=reward_points,
                    type="task_publish_refund",
                    ref_id=task.id,
                    remark=f"撤销任务 #{task.id}，退还 {reward_points} 任务点",
                )
            )
            refund_points = reward_points

    task.status = "cancelled_refunded"
    try:
        _append_timeline_event(
            task,
            "cancelled_refunded",
            f"发布方撤单，退还 {refund_points} 任务点" if refund_points else "发布方撤单（无奖励点扣款）",
        )
    except Exception:
        pass
    try:
        db.add(SystemLog(
            level="info",
            category="task",
            message="task_cancelled_refunded",
            user_id=uid,
            extra={"task_id": task.id, "refund_points": refund_points},
        ))
    except Exception:
        pass
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="撤单失败，请稍后重试")
    db.refresh(task)
    return {
        "ok": True,
        "idempotent": False,
        "task_id": task.id,
        "status": task.status,
        "refunded_points": refund_points,
    }
@router.post("/tasks/{task_id}/bids")
def place_bid(
    task_id: int,
    body: PlaceBidBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Agent 对任务提交/更新报价（owner 为当前用户的 Agent）。同一 Agent 再次提交会更新既有 active bid。"""
    uid = int(current_user["user_id"])
    task = require_auction_task(db, task_id, lock=True)
    auction = _ra.get_auction(task) or {}
    if not _ra.is_auction_open(auction):
        raise HTTPException(status_code=400, detail="竞标已关闭或已过期")
    if task.owner_id == uid:
        raise HTTPException(status_code=400, detail="发布方不可对自己的任务报价")
    agent = db.query(Agent).filter(Agent.id == int(body.agent_id), Agent.owner_id == uid).first()
    if not agent:
        raise HTTPException(status_code=400, detail="Agent 不存在或不属于当前用户")
    invited = getattr(task, "invited_agent_ids", None)
    if invited and isinstance(invited, list) and len(invited) > 0:
        if int(body.agent_id) not in [int(x) for x in invited]:
            raise HTTPException(status_code=403, detail="该任务仅对指定接取者开放")
    try:
        _ra.validate_bid_price(auction, int(body.price))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    eta = None
    if body.eta_hours is not None:
        try:
            eta = max(1, min(24 * 90, int(body.eta_hours)))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="eta_hours 须为整数")
    proposal = (body.proposal or "").strip()[:4000] or None

    existing = (
        db.query(TaskBid)
        .filter(TaskBid.task_id == task_id, TaskBid.agent_id == int(body.agent_id))
        .first()
    )
    created = False
    if existing:
        if existing.status in ("won", "lost"):
            raise HTTPException(status_code=400, detail="该 Agent 已被判标，无法再提交报价")
        existing.price = int(body.price)
        existing.eta_hours = eta
        existing.proposal = proposal
        existing.status = "active"
        bid = existing
    else:
        bid = TaskBid(
            task_id=task_id,
            agent_id=int(body.agent_id),
            bidder_user_id=uid,
            price=int(body.price),
            eta_hours=eta,
            proposal=proposal,
            status="active",
        )
        db.add(bid)
        created = True

    if created:
        auction["bid_count"] = int(auction.get("bid_count", 0) or 0) + 1
        _ra.save_auction_to_task(task, auction)
    try:
        _append_timeline_event(
            task,
            "auction_bid",
            f"Agent「{agent.name}」{'报价' if created else '更新报价'}：{body.price} 点"
            + (f"，ETA {eta}h" if eta else ""),
        )
    except Exception:
        pass
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="提交竞标失败，请稍后重试")
    db.refresh(bid)
    # 发站内信通知发布方
    try:
        msg = InternalMessage(
            sender_user_id=uid,
            recipient_user_id=task.owner_id,
            title=f"您的任务 #{task.id} 收到新报价",
            content=f"Agent「{agent.name}」出价 {body.price} 点，ETA {eta or '未指定'}。前往任务详情查看并选标。",
            related_task_id=task.id,
        )
        db.add(msg)
        db.commit()
    except Exception:
        db.rollback()
    return {
        "ok": True,
        "created": created,
        "bid": _ra.serialize_bid(bid),
        "auction": serialize_auction_state(task),
    }


@router.get("/tasks/{task_id}/bids")
def list_bids(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布方：看全部报价（含 proposal）；竞标者：仅看自己的报价。"""
    uid = int(current_user["user_id"])
    task = require_auction_task(db, task_id)
    is_owner = task.owner_id == uid
    q = db.query(TaskBid).filter(TaskBid.task_id == task_id).order_by(TaskBid.price.asc(), TaskBid.created_at.asc())
    if not is_owner:
        q = q.filter(TaskBid.bidder_user_id == uid)
    bids = q.all()
    return {
        "task_id": task_id,
        "is_publisher": is_owner,
        "auction": serialize_auction_state(task),
        "bids": [_ra.serialize_bid(b, hide_proposal=not is_owner and b.bidder_user_id != uid) for b in bids],
    }


@router.post("/tasks/{task_id}/bids/{bid_id}/withdraw")
def withdraw_bid(
    task_id: int,
    bid_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """竞标者撤回自己的 active 报价。已判标则不可撤回。"""
    uid = int(current_user["user_id"])
    task = require_auction_task(db, task_id, lock=True)
    bid = db.query(TaskBid).filter(TaskBid.id == bid_id, TaskBid.task_id == task_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="报价不存在")
    if bid.bidder_user_id != uid:
        raise HTTPException(status_code=403, detail="仅本人可撤回该报价")
    if bid.status == "won":
        raise HTTPException(status_code=400, detail="该报价已中标，无法撤回")
    if bid.status in ("withdrawn", "lost"):
        return {"ok": True, "idempotent": True, "bid": _ra.serialize_bid(bid)}
    bid.status = "withdrawn"
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="撤回失败，请稍后重试")
    db.refresh(bid)
    return {"ok": True, "idempotent": False, "bid": _ra.serialize_bid(bid)}


@router.post("/tasks/{task_id}/bids/{bid_id}/accept")
def accept_bid(
    task_id: int,
    bid_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布方选标：对指定 active 报价判标，退差额，任务进入 in_progress。"""
    uid = int(current_user["user_id"])
    task = require_auction_task(db, task_id, lock=True)
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅发布方可选标")
    auction = _ra.get_auction(task) or {}
    if auction.get("status") != _ra.AUCTION_STATUS_OPEN:
        raise HTTPException(status_code=400, detail="竞标已结束")
    if task.agent_id is not None:
        raise HTTPException(status_code=400, detail="任务已分配接取者")
    bid = db.query(TaskBid).filter(TaskBid.id == bid_id, TaskBid.task_id == task_id).with_for_update().first()
    if not bid:
        raise HTTPException(status_code=404, detail="报价不存在")
    if bid.status != "active":
        raise HTTPException(status_code=400, detail="仅可对 active 报价选标")
    result = award_bid_impl(task, bid, db)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="选标失败，请稍后重试")
    db.refresh(task)
    return {"ok": True, **result, "auction": serialize_auction_state(task)}



@router.post("/tasks/{task_id}/bids/close")
def close_auction(
    task_id: int,
    body: CloseAuctionBody = Body(default=CloseAuctionBody()),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布方手动关闭竞标：可选自动按最低价判标；无有效报价则全额退款并取消任务。"""
    uid = int(current_user["user_id"])
    task = require_auction_task(db, task_id, lock=True)
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅发布方可关闭竞标")
    auction = _ra.get_auction(task) or {}
    if auction.get("status") != _ra.AUCTION_STATUS_OPEN:
        return {"ok": True, "idempotent": True, "auction": serialize_auction_state(task)}

    active = db.query(TaskBid).filter(TaskBid.task_id == task_id, TaskBid.status == "active").all()
    auto_pick_mode = (auction.get("auto_pick") or "manual") == "lowest_price"
    winner = None
    if active and body.auto_pick_if_bids and auto_pick_mode:
        winner = _ra.pick_lowest_price(active)

    if winner:
        result = award_bid_impl(task, winner, db, auto=True)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="自动选标失败，请稍后重试")
        db.refresh(task)
        return {"ok": True, "awarded": True, **result, "auction": serialize_auction_state(task)}

    # 无中标者：全额退款并取消任务（等同于撤单）
    refund = 0
    reward_points = int(getattr(task, "reward_points", 0) or 0)
    if reward_points > 0:
        already = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.ref_id == task.id,
                CreditTransaction.type == "task_publish_refund",
                CreditTransaction.user_id == uid,
            )
            .first()
        )
        if not already:
            try:
                user = db.query(User).filter(User.id == uid).with_for_update().first()
            except Exception:
                user = db.query(User).filter(User.id == uid).first()
            if user:
                user.credits = int(getattr(user, "credits", 0) or 0) + reward_points
                db.add(
                    CreditTransaction(
                        user_id=uid,
                        amount=reward_points,
                        type="task_publish_refund",
                        ref_id=task.id,
                        remark=f"竞标关闭无成交，退还 {reward_points} 任务点",
                    )
                )
                refund = reward_points
    task.status = "cancelled_refunded"
    db.query(TaskBid).filter(TaskBid.task_id == task_id, TaskBid.status == "active").update(
        {"status": "lost"}, synchronize_session=False
    )
    _ra.save_auction_to_task(task, _ra.mark_auction_cancelled(auction))
    try:
        _append_timeline_event(task, "auction_cancelled", f"竞标关闭，无成交，退款 {refund} 点")
    except Exception:
        pass
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="关闭竞标失败，请稍后重试")
    db.refresh(task)
    return {
        "ok": True,
        "awarded": False,
        "task_id": task.id,
        "refunded_points": refund,
        "status": task.status,
        "auction": serialize_auction_state(task),
    }


@router.post("/tasks/{task_id}/subscribe")
def subscribe_task(
    task_id: int,
    body: SubscribeTaskBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """订阅任务：用我的 Agent 接取该任务（需登录）。任务已被接取后不可再由其他 Agent 接取。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    auction = _ra.get_auction(task)
    if auction and auction.get("status") == _ra.AUCTION_STATUS_OPEN:
        raise HTTPException(
            status_code=400,
            detail="该任务处于反向竞标中，请通过 /tasks/{id}/bids 提交报价等待选标",
        )
    # NOTE: translated comment in English.
    if task.agent_id is not None and task.agent_id != body.agent_id:
        raise HTTPException(
            status_code=403,
            detail="该任务已被接取，无法由其他 Agent 再次接取",
        )
    invited = getattr(task, "invited_agent_ids", None)
    if invited and isinstance(invited, list) and len(invited) > 0:
        if body.agent_id not in [int(x) for x in invited]:
            raise HTTPException(
                status_code=403,
                detail="该任务仅对指定接取者开放，当前 Agent 不在接取列表中",
            )
    agent = db.query(Agent).filter(Agent.id == body.agent_id, Agent.owner_id == uid).first()
    if not agent:
        raise HTTPException(status_code=400, detail="Agent 不存在或不属于当前用户")
    existing = db.query(TaskSubscription).filter(
        TaskSubscription.task_id == task_id,
        TaskSubscription.agent_id == body.agent_id,
    ).first()
    if existing:
        return {"message": "已订阅过该任务", "subscription_id": existing.id}
    sub = TaskSubscription(task_id=task_id, agent_id=body.agent_id)
    db.add(sub)
    # NOTE: translated comment in English.
    if task.agent_id is None:
        task.agent_id = body.agent_id
    if get_escrow(task) and task.status == "open":
        task.status = "in_progress"
    _append_timeline_event(task, "subscribed", f"Agent「{agent.name}」已接取任务")
    db.commit()
    db.refresh(sub)
    return {"message": "订阅成功", "subscription_id": sub.id}


@router.post("/tasks/{task_id}/submit-completion")
def submit_completion(
    task_id: int,
    body: SubmitCompletionBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """接取者提交完成：仅接取该任务的 Agent 所属用户可调用。会 POST 到发布者填写的 completion_webhook_url，任务进入待验收，6 小时内发布者不确认则自动完成并发奖。"""
    preflight = enforce_preflight("task_submit_completion")
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task.agent_id:
        raise HTTPException(status_code=400, detail="任务尚未被接取")
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
    if not agent or agent.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅接取该任务的用户可提交完成")
    if task.status == "completed":
        return {"message": "任务已完成", "task_id": task_id}
    escrow = get_escrow(task)
    if escrow and escrow.get("disputed"):
        raise HTTPException(status_code=400, detail="任务处于争议中，请等待处理后再提交")
    if task.status == "pending_verification":
        return {"message": "已提交验收，请等待发布者确认或 6 小时后自动完成", "task_id": task_id}
    if escrow and task.status not in ("open", "in_progress"):
        raise HTTPException(status_code=400, detail="当前任务状态不可提交里程碑交付")
    validate_verification_submission(task, body)
    try:
        safe_summary = _safety.sanitize_text(
            None,
            getattr(body, "result_summary", None),
            source="submit_completion",
            user_id=uid,
            related_task_id=int(task_id),
        )
        if safe_summary is not None:
            body.result_summary = safe_summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"内容安全策略：{str(e)}")
    webhook_url = getattr(task, "completion_webhook_url", None) or ""
    reward_points = getattr(task, "reward_points", 0) or 0
    payload = None
    webhook_delivery_meta: Optional[dict] = None
    if webhook_url:
        allow, cb_state = runtime_guard.can_request(webhook_url)
        if not allow:
            raise HTTPException(status_code=503, detail=f"完成回调熔断中，请稍后重试（{cb_state}）")
        payload = {
            "task_id": task_id,
            "title": task.title,
            "agent_id": task.agent_id,
            "agent_name": agent.name,
            "result_summary": body.result_summary or "",
            "evidence": body.evidence or {},
            "submitted_at": datetime.utcnow().isoformat() + "Z",
        }
        if escrow:
            idx = int(escrow.get("current_index", 0) or 0)
            ms = escrow.get("milestones") or []
            payload["escrow_milestone_index"] = idx
            payload["escrow_milestone_title"] = ms[idx].get("title") if idx < len(ms) else None
            payload["escrow_current_acceptance_criteria"] = ms[idx].get("acceptance_criteria") if idx < len(ms) else None
            payload["escrow_total_milestones"] = len(ms)
        max_attempts = 3
        last_err: Optional[str] = None
        import app.main as _app_main  # tests patch app.main.httpx
        for attempt in range(1, max_attempts + 1):
            try:
                with _app_main.httpx.Client(timeout=10.0) as client:
                    r = client.post(webhook_url, json=payload)
                if r.status_code < 400:
                    runtime_guard.record_success(webhook_url)
                    last_err = None
                    webhook_delivery_meta = {
                        "attempts": attempt,
                        "http_status": int(r.status_code),
                        "ok": True,
                    }
                    break
                if 400 <= r.status_code < 500:
                    runtime_guard.record_failure(webhook_url)
                    raise HTTPException(
                        status_code=502,
                        detail=f"完成回调返回异常：{r.status_code}，发布方需验收通过后再在平台确认",
                    )
                runtime_guard.record_failure(webhook_url)
                last_err = f"完成回调返回异常：{r.status_code}"
            except _app_main.httpx.RequestError as e:
                runtime_guard.record_failure(webhook_url)
                last_err = f"调用完成回调失败：{str(e)}"
            if attempt < max_attempts:
                time.sleep(0.2 * attempt)
        if last_err:
            raise HTTPException(status_code=502, detail=f"{last_err}（已重试 {max_attempts} 次）")
    task.status = "pending_verification"
    task.submitted_at = datetime.utcnow()
    vh = task_verification_hours(task)
    base_in = task.input_data if isinstance(task.input_data, dict) else {}
    base_in = copy.deepcopy(base_in) if base_in else {}
    base_in["verification_extend_used"] = 0
    task.input_data = base_in
    try:
        flag_modified(task, "input_data")
    except Exception:
        pass
    task.verification_deadline_at = datetime.utcnow() + timedelta(hours=vh)
    if body.result_summary or body.evidence:
        base = task.output_data if isinstance(task.output_data, dict) else {}
        task.output_data = {
            **(base or {}),
            "result_summary": body.result_summary or "",
            "evidence": body.evidence or {},
            "verification_chain": {
                "declaration": {
                    "verification_method": ((task.input_data or {}).get("verification_method") if isinstance(task.input_data, dict) else "manual_review"),
                    "verification_requirements": ((task.input_data or {}).get("verification_requirements") if isinstance(task.input_data, dict) else []),
                },
                "sandbox": preflight,
                "cross": {"status": "pending_verification", "submitted_at": datetime.utcnow().isoformat() + "Z"},
            },
        }
    if escrow:
        base = task.output_data if isinstance(task.output_data, dict) else {}
        idx = int(escrow.get("current_index", 0) or 0)
        task.output_data = {**(base or {}), "escrow_submit_milestone_index": idx}
    if webhook_delivery_meta is not None:
        base_od = task.output_data if isinstance(task.output_data, dict) else {}
        task.output_data = {**base_od, "webhook_delivery": webhook_delivery_meta}
        try:
            flag_modified(task, "output_data")
        except Exception:
            pass
    _append_timeline_event(task, "submitted_for_review", f"已提交验收，截止 {iso_utc(task.verification_deadline_at)}（{vh} 小时内未确认将自动发奖）")
    db.commit()
    append_task_status_update_comment(
        db,
        task,
        user_id=uid,
        agent_id=task.agent_id,
        content=f"任务已提交验收，截止时间：{iso_utc(task.verification_deadline_at)}",
    )
    return {
        "message": f"已提交验收，发布者需在 {vh} 小时内确认，否则将自动完成并发奖",
        "task_id": task_id,
        "verification_deadline_at": iso_utc(task.verification_deadline_at),
        "verification_hours": vh,
        "preflight": preflight,
    }
@router.get("/tasks/{task_id}/verification-chain")
def get_task_verification_chain(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    output = task.output_data if isinstance(task.output_data, dict) else {}
    declaration = {
        "verification_method": extra.get("verification_method") or "manual_review",
        "verification_requirements": extra.get("verification_requirements") or [],
    }
    sandbox = run_preflight("verification_chain_view")
    cross = {
        "status": task.status,
        "submitted_at": iso_utc(task.submitted_at) if getattr(task, "submitted_at", None) else None,
        "verification_deadline_at": iso_utc(task.verification_deadline_at) if getattr(task, "verification_deadline_at", None) else None,
        "rejection_reason": output.get("rejection_reason"),
        "verification_record": output.get("verification_record"),
        "has_escrow": bool(get_escrow(task)),
    }
    return {"task_id": task_id, "declaration": declaration, "sandbox": sandbox, "cross": cross}


@router.post("/tasks/{task_id}/confirm")
def confirm_task(
    task_id: int,
    body: Optional[ConfirmTaskBody] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布者验收通过：仅任务发布者可调用，发放奖励给接取者。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可验收")
    maybe_auto_confirm(task, db)
    db.refresh(task)
    if task.status == "completed":
        return {"message": "任务已是完成状态（或已自动完成）", "task_id": task_id}
    reward_points = getattr(task, "reward_points", 0) or 0
    escrow = get_escrow(task)
    if task.status == "pending_verification" and escrow:
        info = apply_escrow_milestone_confirm(task, db, auto=False)
        fin = bool(info.get("escrow_finished"))
        _append_timeline_event(
            task,
            "milestone_confirmed",
            "托管里程碑已确认并放款" + ("（全部里程碑已完成）" if fin else ""),
        )
        db.commit()
        if fin:
            try:
                maybe_settle_skill_revenue(task, db)
            except Exception:
                db.rollback()
        append_task_status_update_comment(
            db,
            task,
            user_id=uid,
            agent_id=task.agent_id,
            content="发布方已确认当前里程碑，奖励已发放",
        )
        msg = (
            "托管里程碑验收通过，奖励已发放"
            if not info.get("escrow_finished")
            else "托管任务已全部完成，奖励已发放"
        )
        return {
            "message": msg,
            "task_id": task_id,
            "reward_paid": info.get("reward_paid", 0),
            "reward_total": reward_points,
            "commission": info.get("commission", 0),
            "escrow": {
                "milestone_index": info.get("milestone_index"),
                "finished": bool(info.get("escrow_finished")),
            },
        }
    if task.status == "pending_verification":
        pay_task_reward(task, db)
        _append_timeline_event(task, "confirmed", "发布方确认验收，任务完成并已发奖")
    elif task.status == "open" and reward_points == 0:
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        try:
            from app.services import community_task_hooks as _ct_hooks

            _ct_hooks.on_task_completed_community_hooks(db, task)
        except Exception:
            pass
    else:
        raise HTTPException(status_code=400, detail="任务尚未进入待验收状态，请等待接取者提交完成")
    db.commit()
    append_task_status_update_comment(
        db,
        task,
        user_id=uid,
        agent_id=task.agent_id,
        content="发布方已确认验收通过，任务完成",
    )
    commission = int(reward_points * PLATFORM_COMMISSION_RATE) if reward_points else 0
    amount_to_executor = reward_points - commission if reward_points else 0
    try:
        base = task.output_data if isinstance(task.output_data, dict) else {}
        task.output_data = {
            **(base or {}),
            "verification_record": {
                "mode": ((body.verification_mode if body else "manual_review") or "manual_review")[:32],
                "note": ((body.verification_note if body else "") or "")[:1000],
                "verified_by_user_id": uid,
                "verified_at": datetime.utcnow().isoformat() + "Z",
            },
        }
        db.commit()
    except Exception:
        db.rollback()
    return {
        "message": "验收通过，奖励已发放" if reward_points else "任务已关闭",
        "task_id": task_id,
        "reward_paid": amount_to_executor,
        "reward_total": reward_points,
        "commission": commission,
    }


@router.post("/tasks/{task_id}/reject")
def reject_completion(
    task_id: int,
    body: RejectCompletionBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布者拒绝验收：必须填写拒绝理由（作为 RL 惩罚信号）；任务回到可继续状态，接取者可重新提交完成。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可拒绝")
    if task.status != "pending_verification":
        raise HTTPException(status_code=400, detail="仅待验收任务可拒绝")
    reason = (body.rejection_reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="请填写拒绝理由，以便接取者改进（作为 RL 反馈）")
    task.status = "in_progress" if get_escrow(task) else "open"
    task.submitted_at = None
    task.verification_deadline_at = None
    base = task.output_data if isinstance(task.output_data, dict) else {}
    rh = base.get("rejection_history")
    if not isinstance(rh, list):
        rh = []
    rh.append({"at": datetime.utcnow().isoformat() + "Z", "reason": reason[:2000]})
    base["rejection_history"] = rh[-20:]
    base["rejection_reason"] = reason
    task.output_data = base
    try:
        flag_modified(task, "output_data")
    except Exception:
        pass
    esc = get_escrow(task)
    _append_timeline_event(
        task,
        "rejected",
        ("退回修改（托管）" if esc else "退回修改（非托管：仍由原接取 Agent 负责，其他人不可抢单）")
        + f"：{reason[:120]}",
    )
    db.commit()
    append_task_status_update_comment(
        db,
        task,
        user_id=uid,
        agent_id=task.agent_id,
        content=f"发布方拒绝验收：{reason[:160]}",
    )
    return {"message": "已拒绝，接取者可重新提交完成", "task_id": task_id}


@router.post("/tasks/{task_id}/extend-verification")
def extend_task_verification(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布者延长本轮待验收截止时间一次（+24 小时）；仅 pending_verification 且尚未延长过。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.owner_id != uid:
        raise HTTPException(status_code=403, detail="仅任务发布者可延长验收")
    if task.status != "pending_verification":
        raise HTTPException(status_code=400, detail="仅待验收任务可延长")
    if not getattr(task, "verification_deadline_at", None):
        raise HTTPException(status_code=400, detail="无验收截止时间")
    base = task.input_data if isinstance(task.input_data, dict) else {}
    used = int(base.get("verification_extend_used", 0) or 0)
    if used >= 1:
        raise HTTPException(status_code=400, detail="本轮待验收仅可延长一次（+24 小时）")
    task.verification_deadline_at = task.verification_deadline_at + timedelta(hours=VERIFICATION_EXTEND_HOURS)
    base = copy.deepcopy(base)
    base["verification_extend_used"] = 1
    task.input_data = base
    try:
        flag_modified(task, "input_data")
    except Exception:
        pass
    _append_timeline_event(
        task,
        "verification_extended",
        f"发布方延长验收 {VERIFICATION_EXTEND_HOURS} 小时，新截止：{iso_utc(task.verification_deadline_at)}",
    )
    db.commit()
    return {
        "message": f"已延长 {VERIFICATION_EXTEND_HOURS} 小时",
        "task_id": task_id,
        "verification_deadline_at": iso_utc(task.verification_deadline_at),
    }


@router.post("/tasks/{task_id}/escrow/dispute")
def escrow_dispute(
    task_id: int,
    body: EscrowDisputeBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """托管争议：发布方或接取方发起，任务进入 disputed，暂停提交与放款直至管理员处理。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    escrow = get_escrow(task)
    if not escrow:
        raise HTTPException(status_code=400, detail="该任务未启用托管里程碑")
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="任务已完成，无法发起争议")
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="请填写争议说明")
    evidence = body.evidence if isinstance(body.evidence, dict) else {}
    is_pub = task.owner_id == uid
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first() if task.agent_id else None
    is_exe = agent and agent.owner_id == uid
    if not is_pub and not is_exe:
        raise HTTPException(status_code=403, detail="仅发布方或接取方可发起托管争议")
    escrow["disputed"] = True
    escrow["dispute_reason"] = reason[:4000]
    # NOTE: translated comment in English.
    try:
        # NOTE: translated comment in English.
        def _trim_obj(x, max_len: int = 4000):
            if isinstance(x, str):
                return x[:max_len]
            if isinstance(x, list):
                return [_trim_obj(i, max_len) for i in x[:20]]
            if isinstance(x, dict):
                out = {}
                for k, v in list(x.items())[:20]:
                    out[str(k)[:50]] = _trim_obj(v, max_len)
                return out
            return x

        escrow["dispute_evidence"] = _trim_obj(evidence, 4000)
    except Exception:
        escrow["dispute_evidence"] = {}
    save_escrow_to_task(task, escrow)
    task.status = "disputed"
    _append_timeline_event(
        task,
        "escrow_dispute",
        "托管争议已发起，双方暂停提交与放款，请等待管理员处理（详见 /admin 争议列表）",
    )
    db.commit()
    try:
        db.add(
            SystemLog(
                level="warning",
                category="task",
                message="escrow_dispute",
                user_id=uid,
                extra={"task_id": task_id, "reason_preview": reason[:200]},
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "已记录托管争议，任务已冻结", "task_id": task_id}


@router.post("/tasks/batch-confirm")
def batch_confirm_tasks(
    body: BatchConfirmBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """批量验收通过：仅任务发布者可调用，对多个待验收任务执行验收。响应含 summary 便于前端提示高额奖励风险。"""
    uid = int(current_user["user_id"])
    task_ids = list(set(body.task_ids or []))[:50]
    results = []
    total_reward_points = 0
    high_value_task_ids: List[int] = []
    for task_id in task_ids:
        task = db.query(Task).filter(Task.id == task_id, Task.owner_id == uid).first()
        if not task:
            results.append({"task_id": task_id, "ok": False, "reason": "not_found_or_forbidden"})
            continue
        rp = int(getattr(task, "reward_points", 0) or 0)
        if task.status == "pending_verification":
            total_reward_points += rp
            if rp >= 5000:
                high_value_task_ids.append(task_id)
        maybe_auto_confirm(task, db)
        db.refresh(task)
        if task.status == "completed":
            results.append({"task_id": task_id, "ok": True, "message": "already_completed"})
            continue
        if task.status != "pending_verification" and not (task.status == "open" and (getattr(task, "reward_points", 0) or 0) == 0):
            results.append({"task_id": task_id, "ok": False, "reason": "not_pending_verification"})
            continue
        try:
            if task.status == "pending_verification" and get_escrow(task):
                apply_escrow_milestone_confirm(task, db, auto=False)
            elif task.status == "pending_verification":
                pay_task_reward(task, db)
            if task.status == "open" and (getattr(task, "reward_points", 0) or 0) == 0:
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                try:
                    from app.services import community_task_hooks as _ct_hooks

                    _ct_hooks.on_task_completed_community_hooks(db, task)
                except Exception:
                    pass
            db.commit()
            results.append({"task_id": task_id, "ok": True})
        except Exception as e:
            db.rollback()
            results.append({"task_id": task_id, "ok": False, "reason": str(e)})
    warn = None
    if total_reward_points >= 10000 or len(high_value_task_ids) >= 3:
        warn = "批量中含高额奖励任务，请逐条核对后再验收"
    elif high_value_task_ids:
        warn = "部分任务奖励点较高（≥5000），请确认无误"
    return {
        "results": results,
        "summary": {
            "total_reward_points": total_reward_points,
            "high_value_task_ids": high_value_task_ids[:50],
            "warning": warn,
        },
    }
@router.get("/tasks/{task_id}")
async def get_task_by_id(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """获取单条任务详情（公开）；若处于待验收且已超过截止时间则自动完成。

    对「定向任务」做可见性控制：仅发布者与被邀请 Agent 的拥有者可读，其他人返回 404。
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    viewer_uid: Optional[int] = None
    viewer_agent_ids: List[int] = []
    if current_user:
        try:
            viewer_uid = int(current_user.get("user_id")) if current_user.get("user_id") is not None else None
        except (TypeError, ValueError):
            viewer_uid = None
        if viewer_uid is not None:
            viewer_agent_ids = [int(a.id) for a in db.query(Agent.id).filter(Agent.owner_id == viewer_uid).all()]
    if not task_is_visible_to(task, viewer_uid, viewer_agent_ids):
        raise HTTPException(status_code=404, detail="任务不存在")
    maybe_auto_confirm(task, db)
    db.refresh(task)
    owner = db.query(User).filter(User.id == task.owner_id).first()
    subs = db.query(TaskSubscription).filter(TaskSubscription.task_id == task_id).all()
    creator_agent = db.query(Agent).filter(Agent.id == task.creator_agent_id).first() if getattr(task, "creator_agent_id", None) else None
    tin = task.input_data if isinstance(task.input_data, dict) else {}
    tout = task.output_data if isinstance(task.output_data, dict) else {}
    tl = tin.get("timeline")
    if not isinstance(tl, list):
        tl = []
    rh = tout.get("rejection_history")
    if not isinstance(rh, list):
        rh = []
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "status": task.status,
        "priority": task.priority,
        "task_type": task.task_type,
        "owner_id": task.owner_id,
        "publisher_name": owner.username if owner else "",
        "agent_id": task.agent_id,
        "creator_agent_id": getattr(task, "creator_agent_id", None),
        "creator_agent_name": creator_agent.name if creator_agent else None,
        "reward_points": getattr(task, "reward_points", 0) or 0,
        "subscription_count": len(subs),
        "submitted_at": iso_utc(getattr(task, "submitted_at", None)),
        "verification_deadline_at": iso_utc(getattr(task, "verification_deadline_at", None)),
        "created_at": iso_utc(task.created_at),
        "output_data": task.output_data if isinstance(getattr(task, "output_data", None), dict) else None,
        "timeline": tl,
        "verification_hours": task_verification_hours(task),
        "verification_extend_used": int(tin.get("verification_extend_used", 0) or 0),
        "rejection_history": rh,
        "payment_breakdown": task_payment_breakdown(task, db),
        **task_extra(task, db),
    }


@router.get("/tasks/{task_id}/comments")
def list_task_comments(task_id: int, db: Session = Depends(get_db)):
    """任务评论列表（公开）。"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.asc()).all()
    out = []
    for c in comments:
        user = db.query(User).filter(User.id == c.user_id).first()
        agent = db.query(Agent).filter(Agent.id == c.agent_id).first() if getattr(c, "agent_id", None) else None
        out.append({
            "id": c.id,
            "task_id": c.task_id,
            "user_id": c.user_id,
            "author_name": user.username if user else "",
            "agent_id": getattr(c, "agent_id", None),
            "agent_name": agent.name if agent else None,
            "kind": getattr(c, "kind", None) or "message",
            "content": c.content,
            "created_at": iso_utc(c.created_at),
        })
    return {"comments": out}
@router.get("/forum/recent-posts")
def forum_recent_posts(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Recent task comments for Agent Forum feed (public read). Reuses task comments as discussion threads."""
    total = db.query(TaskComment).count()
    rows = (
        db.query(TaskComment)
        .order_by(desc(TaskComment.created_at))
        .offset(skip)
        .limit(min(limit, 100))
        .all()
    )
    items = []
    for c in rows:
        task = db.query(Task).filter(Task.id == c.task_id).first()
        user = db.query(User).filter(User.id == c.user_id).first()
        agent = db.query(Agent).filter(Agent.id == c.agent_id).first() if getattr(c, "agent_id", None) else None
        items.append({
            "comment": {
                "id": c.id,
                "task_id": c.task_id,
                "user_id": c.user_id,
                "author_name": user.username if user else "",
                "agent_id": getattr(c, "agent_id", None),
                "agent_name": agent.name if agent else None,
                "kind": getattr(c, "kind", None) or "message",
                "content": c.content,
                "created_at": iso_utc(c.created_at),
            },
            "task": {
                "id": task.id if task else c.task_id,
                "title": (task.title or "") if task else "",
                "status": (task.status or "") if task else "",
            },
        })
    return {"items": items, "total": total, "skip": skip, "limit": len(items)}
@router.post("/tasks/{task_id}/comments")
def post_task_comment(
    task_id: int,
    body: PostCommentBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发布任务评论（需登录）。支持 A2A：传入 agent_id 可以 Agent 身份留言，kind 可为 status_update 表示状态同步。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    agent_id = body.agent_id
    kind = (body.kind or "message").strip().lower() or "message"
    if kind not in ("message", "status_update"):
        kind = "message"
    if agent_id is not None:
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == uid).first()
        if not agent:
            raise HTTPException(status_code=400, detail="Agent 不存在或不属于当前用户")
    comment = TaskComment(
        task_id=task_id,
        user_id=uid,
        content=content,
        agent_id=agent_id,
        kind=kind,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    user = db.query(User).filter(User.id == uid).first()
    agent = db.query(Agent).filter(Agent.id == comment.agent_id).first() if getattr(comment, "agent_id", None) else None
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "user_id": comment.user_id,
        "author_name": user.username if user else "",
        "agent_id": getattr(comment, "agent_id", None),
        "agent_name": agent.name if agent else None,
        "kind": getattr(comment, "kind", None) or "message",
        "content": comment.content,
        "created_at": iso_utc(comment.created_at),
    }
@router.get("/a2a/tasks/{task_id}")
def a2a_get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """A2A：获取任务状态，供 Agent 同步。需登录且为任务发布者或接取者。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not a2a_can_access_task(task, uid, db):
        raise HTTPException(status_code=403, detail="无权访问该任务")
    owner = db.query(User).filter(User.id == task.owner_id).first()
    executor = db.query(Agent).filter(Agent.id == task.agent_id).first() if task.agent_id else None
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "status": task.status,
        "owner_id": task.owner_id,
        "publisher_name": owner.username if owner else "",
        "agent_id": task.agent_id,
        "executor_agent_name": executor.name if executor else None,
        "reward_points": getattr(task, "reward_points", 0) or 0,
        "submitted_at": iso_utc(getattr(task, "submitted_at", None)),
        "verification_deadline_at": iso_utc(getattr(task, "verification_deadline_at", None)),
        "created_at": iso_utc(task.created_at),
        "completed_at": iso_utc(getattr(task, "completed_at", None)),
    }


@router.post("/a2a/tasks/{task_id}/messages")
def a2a_post_message(
    task_id: int,
    body: A2AMessageBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """A2A：在任务下留言或发送状态更新。需登录且为任务发布者或接取者；可选 agent_id 表示以该 Agent 身份发言。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not a2a_can_access_task(task, uid, db):
        raise HTTPException(status_code=403, detail="无权在该任务下留言")
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    agent_id = body.agent_id
    kind = (body.kind or "message").strip().lower() or "message"
    if kind not in ("message", "status_update"):
        kind = "message"
    if agent_id is not None:
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_id == uid).first()
        if not agent:
            raise HTTPException(status_code=400, detail="Agent 不存在或不属于当前用户")
    comment = TaskComment(task_id=task_id, user_id=uid, content=content, agent_id=agent_id, kind=kind)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    agent = db.query(Agent).filter(Agent.id == comment.agent_id).first() if getattr(comment, "agent_id", None) else None
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "agent_id": getattr(comment, "agent_id", None),
        "agent_name": agent.name if agent else None,
        "kind": getattr(comment, "kind", None) or "message",
        "content": comment.content,
        "created_at": iso_utc(comment.created_at),
    }


@router.get("/a2a/tasks/{task_id}/messages")
def a2a_list_messages(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """A2A：拉取任务下的留言/状态更新。需登录且为任务发布者或接取者。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not a2a_can_access_task(task, uid, db):
        raise HTTPException(status_code=403, detail="无权查看该任务留言")
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.asc()).all()
    out = []
    for c in comments:
        agent = db.query(Agent).filter(Agent.id == c.agent_id).first() if getattr(c, "agent_id", None) else None
        user = db.query(User).filter(User.id == c.user_id).first()
        out.append({
            "id": c.id,
            "task_id": c.task_id,
            "user_id": c.user_id,
            "author_name": user.username if user else "",
            "agent_id": getattr(c, "agent_id", None),
            "agent_name": agent.name if agent else None,
            "kind": getattr(c, "kind", None) or "message",
            "content": c.content,
            "created_at": iso_utc(c.created_at),
        })
    return {"messages": out}
@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    retry_count: int = 0,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Execute a task using available agents（含执行沙箱 quota + 步骤级回放）。"""
    retries = max(0, min(3, int(retry_count or 0)))
    last_err: Optional[str] = None
    task = db.query(Task).filter(Task.id == int(task_id)).first() if str(task_id).isdigit() else None
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    uid = None
    try:
        uid = int((current_user or {}).get("user_id"))
    except Exception:
        uid = None

    base_quota = _sandbox.ExecutionQuota.from_env()
    task_quota_cfg = None
    if isinstance(task.input_data, dict):
        task_quota_cfg = task.input_data.get("execution_quota")
    quota = base_quota.merge(_sandbox.ExecutionQuota.from_dict(task_quota_cfg))

    for attempt in range(retries + 1):
        recorder = _replay.RunRecorder(db, task_id=int(task.id), user_id=uid)
        recorder.start(
            meta={
                "attempt": int(attempt),
                "max_retries": int(retries),
                "quota": quota.as_dict(),
            }
        )

        async def _runner(meter: _sandbox.QuotaMeter):
            recorder.step("tool", name="task_system.execute_task", input={"task_id": str(task_id)})
            result = await task_system.execute_task(task_id)
            try:
                meter.check()
            except _sandbox.QuotaExceeded:
                raise
            recorder.step("output", name="task_result", output={"preview": str(result)[:800]})
            return result

        outcome = await _sandbox.run_with_quota(_runner, quota)

        base = task.output_data if isinstance(task.output_data, dict) else {}
        if outcome.ok:
            task.output_data = {
                **base,
                "last_execute": {
                    "retried": int(attempt),
                    "at": datetime.utcnow().isoformat() + "Z",
                    "ok": True,
                    "run_id": recorder.run_id,
                    "duration_ms": outcome.duration_ms,
                    "tokens_used": outcome.tokens_used,
                    "cost_credits": outcome.cost_credits,
                },
            }
            try:
                flag_modified(task, "output_data")
            except Exception:
                pass
            db.commit()
            recorder.finish(
                ok=True,
                tokens_used=outcome.tokens_used,
                cost_credits=outcome.cost_credits,
                summary={"duration_ms": outcome.duration_ms},
            )
            result = outcome.result
            if attempt > 0 and isinstance(result, dict):
                result["retried"] = attempt
            if isinstance(result, dict):
                result["run_id"] = recorder.run_id
            return result

        last_err = outcome.error or outcome.reason
        if outcome.quota_exceeded:
            recorder.step("quota", name=outcome.reason or "quota_exceeded", ok=False, error=last_err)
            recorder.finish(
                ok=False,
                quota_exceeded=True,
                error=last_err,
                tokens_used=outcome.tokens_used,
                cost_credits=outcome.cost_credits,
                summary={"reason": outcome.reason},
            )
            task.output_data = {
                **base,
                "last_execute": {
                    "retried": int(attempt),
                    "at": datetime.utcnow().isoformat() + "Z",
                    "ok": False,
                    "quota_exceeded": True,
                    "reason": outcome.reason,
                    "run_id": recorder.run_id,
                    "duration_ms": outcome.duration_ms,
                },
            }
            try:
                flag_modified(task, "output_data")
            except Exception:
                pass
            db.commit()
            raise HTTPException(
                status_code=429,
                detail=f"执行超出沙箱配额：{outcome.reason}（quota_exceeded）",
            )

        recorder.step("error", name="runner_error", ok=False, error=last_err)
        recorder.finish(ok=False, error=last_err, summary={"attempt": attempt})
        if attempt < retries:
            await asyncio.sleep(0.2 * (attempt + 1))
            continue
        task.output_data = {
            **base,
            "last_execute": {
                "retried": int(retries),
                "at": datetime.utcnow().isoformat() + "Z",
                "ok": False,
                "error": (last_err or "")[:300],
                "run_id": recorder.run_id,
            },
        }
        try:
            flag_modified(task, "output_data")
        except Exception:
            pass
        db.commit()
        raise HTTPException(status_code=500, detail=f"执行失败：{last_err}（已重试 {retries} 次）")


# ---------------------------------------------------------------------------
# C-11 步骤回放（Step Replay）：发布方 / 接取方可读，超管可读
# ---------------------------------------------------------------------------


def can_view_task_runs(task: Task, uid: int, db: Session) -> bool:
    if task.owner_id == uid:
        return True
    if task.agent_id:
        a = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if a and a.owner_id == uid:
            return True
    u = db.query(User).filter(User.id == uid).first()
    return bool(u and getattr(u, "is_superuser", False))


@router.get("/tasks/{task_id}/runs")
def list_task_runs(
    task_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == int(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not can_view_task_runs(task, uid, db):
        raise HTTPException(status_code=403, detail="无权查看该任务运行记录")
    rows = (
        db.query(ExecutionRun)
        .filter(ExecutionRun.task_id == int(task_id))
        .order_by(ExecutionRun.started_at.desc())
        .limit(max(1, min(200, int(limit or 20))))
        .all()
    )
    return {"items": [_replay.serialize_run(r) for r in rows]}


@router.get("/tasks/{task_id}/runs/{run_id}/steps")
def list_task_run_steps(
    task_id: int,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == int(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not can_view_task_runs(task, uid, db):
        raise HTTPException(status_code=403, detail="无权查看该任务运行记录")
    run = (
        db.query(ExecutionRun)
        .filter(ExecutionRun.task_id == int(task_id), ExecutionRun.run_id == str(run_id))
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    steps = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.run_id == str(run_id))
        .order_by(ExecutionStep.idx.asc())
        .all()
    )
    return {
        "run": _replay.serialize_run(run),
        "steps": [_replay.serialize_step(s) for s in steps],
    }


@router.get("/tasks/{task_id}/runs/{run_id}/export")
def export_task_run(
    task_id: int,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """将某次运行导出为 JSON 审计包。"""
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == int(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not can_view_task_runs(task, uid, db):
        raise HTTPException(status_code=403, detail="无权导出该任务运行记录")
    run = (
        db.query(ExecutionRun)
        .filter(ExecutionRun.task_id == int(task_id), ExecutionRun.run_id == str(run_id))
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    steps = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.run_id == str(run_id))
        .order_by(ExecutionStep.idx.asc())
        .all()
    )
    return {
        "task_id": int(task_id),
        "run": _replay.serialize_run(run),
        "steps": [_replay.serialize_step(s) for s in steps],
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }
@router.get("/tasks/estimate")
def estimate_task_price_sla(
    skill: Optional[str] = None,
    kind: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """价格与 SLA 预估（公开）。

    - 依据历史任务（最近 500 单相似样本）聚合出奖励点的中位数与 p25/p75/p90 分位、
      预估完成时长（p50/p75）、预估接取等待时长（p50/p75）。
    - `difficulty` 可选 `easy|normal|hard|expert`，对输出做乘数修正。
    - 样本不足 5 条时自动走启发式回退（按 skill → category → 全局默认表）。
    - 响应头加 5 分钟缓存；服务内部还有 5 分钟 LRU。
    """
    from app.services.price_sla_estimator import estimate_price_sla

    result = estimate_price_sla(
        db,
        skill=skill,
        kind=kind,
        category=category,
        difficulty=difficulty,
    )
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/tasks")
def list_tasks_public(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    category_filter: str = None,
    creator_agent_id: Optional[int] = None,
    q: str = None,
    sort: str = "created_at_desc",
    reward_min: Optional[int] = None,
    reward_max: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """任务大厅：公开列出所有任务（无需登录）；支持分类、关键词、奖励区间、排序；creator_agent_id 可筛选某 Agent 发布的任务。

    若任务是「定向任务」（`input_data.visibility == invitees_only`），仅发布者与被邀请 Agent 的拥有者可见。
    """
    # 内部/握手/平台系统账号任务不进入公开大厅与计数。
    system_owner_ids = [
        int(u.id)
        for u in db.query(User.id).filter(User.username == CLAWJOB_SYSTEM_USERNAME).all()
    ]

    # 尝试在 SQL 层过滤 input_data.hidden_from_public（仅在 PostgreSQL 下生效，
    # SQLite 测试环境继续依赖 Python 层的 task_is_public_listing 过滤）。
    def _apply_hidden_filter(qy):
        try:
            dialect = db.bind.dialect.name if db.bind is not None else ""
        except Exception:
            dialect = ""
        if dialect != "postgresql":
            return qy
        try:
            from sqlalchemy import or_ as _or
            hidden_expr = Task.input_data.op("->>")("hidden_from_public")
            # NULL (字段不存在) 视为未隐藏；仅当显式为 'true'/'1' 时才过滤。
            return qy.filter(
                _or(
                    Task.input_data.is_(None),
                    hidden_expr.is_(None),
                    hidden_expr.notin_(("true", "True", "1")),
                )
            )
        except Exception:
            return qy

    def _apply_public_filters(qy):
        if status_filter:
            qy = qy.filter(Task.status == status_filter)
        else:
            qy = qy.filter(Task.status != "cancelled_refunded")
        if category_filter and category_filter.strip():
            qy = qy.filter(Task.category == category_filter.strip())
        if creator_agent_id is not None:
            qy = qy.filter(Task.creator_agent_id == creator_agent_id)
        if q and q.strip():
            from sqlalchemy import or_
            term = f"%{q.strip()}%"
            qy = qy.filter(or_(Task.title.ilike(term), Task.description.ilike(term)))
        if reward_min is not None:
            qy = qy.filter(Task.reward_points >= reward_min)
        if reward_max is not None:
            qy = qy.filter(Task.reward_points <= reward_max)
        if system_owner_ids:
            try:
                dialect = db.bind.dialect.name if db.bind is not None else ""
            except Exception:
                dialect = ""
            if dialect == "postgresql":
                from sqlalchemy import or_ as _or
                src_expr = Task.input_data.op("->>")("source")
                showcase_expr = Task.input_data.op("->>")("showcase")
                qy = qy.filter(
                    _or(
                        ~Task.owner_id.in_(system_owner_ids),
                        src_expr == "seed_open_tasks",
                        showcase_expr.in_(("true", "True", "1")),
                    )
                )
        qy = _apply_hidden_filter(qy)
        return qy

    query = _apply_public_filters(db.query(Task))
    if sort == "comments_desc":
        query = _apply_public_filters(
            db.query(Task, func.count(TaskComment.id).label("comment_count")).outerjoin(
                TaskComment, Task.id == TaskComment.task_id
            )
        )
        query = query.group_by(Task.id).order_by(func.count(TaskComment.id).desc().nullslast(), Task.created_at.desc())
        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        tasks_with_count = [(row[0], row[1]) for row in rows]
    else:
        if sort == "reward_desc":
            query = query.order_by(Task.reward_points.desc().nullslast(), Task.created_at.desc())
        elif sort == "created_at_asc":
            query = query.order_by(Task.created_at.asc())
        elif sort == "deadline_asc":
            query = query.order_by(Task.verification_deadline_at.asc().nullslast(), Task.created_at.desc())
        else:
            query = query.order_by(Task.created_at.desc())
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        tasks_with_count = [(t, db.query(TaskComment).filter(TaskComment.task_id == t.id).count()) for t in tasks]
    viewer_uid: Optional[int] = None
    viewer_agent_ids: List[int] = []
    if current_user:
        try:
            viewer_uid = int(current_user.get("user_id")) if current_user.get("user_id") is not None else None
        except (TypeError, ValueError):
            viewer_uid = None
        if viewer_uid is not None:
            viewer_agent_ids = [int(a.id) for a in db.query(Agent.id).filter(Agent.owner_id == viewer_uid).all()]

    out = []
    for t, comment_count in tasks_with_count:
        maybe_auto_confirm(t, db)
        db.refresh(t)
        if not task_is_visible_to(t, viewer_uid, viewer_agent_ids):
            continue
        owner = db.query(User).filter(User.id == t.owner_id).first()
        if not task_is_public_listing(t, owner) and viewer_uid != t.owner_id:
            continue
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        invited = getattr(t, "invited_agent_ids", None)
        creator_agent = db.query(Agent).filter(Agent.id == t.creator_agent_id).first() if getattr(t, "creator_agent_id", None) else None
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "task_type": t.task_type or "general",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "agent_id": t.agent_id,
            "creator_agent_id": getattr(t, "creator_agent_id", None),
            "creator_agent_name": creator_agent.name if creator_agent else None,
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "subscription_count": sub_count,
            "comment_count": comment_count,
            "invited_agent_ids": invited if invited else [],
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **task_extra(t, db),
        })
    return JSONResponse(
        content={"tasks": out, "total": total},
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/tasks/created-by-me")
def list_my_created_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """当前用户发布的任务（我创建的任务）。"""
    uid = int(current_user["user_id"])
    query = db.query(Task).filter(Task.owner_id == uid).order_by(Task.created_at.desc())
    tasks = query.offset(skip).limit(limit).all()
    out = []
    for t in tasks:
        maybe_auto_confirm(t, db)
        db.refresh(t)
        owner = db.query(User).filter(User.id == t.owner_id).first()
        sub_count = db.query(TaskSubscription).filter(TaskSubscription.task_id == t.id).count()
        comment_count = db.query(TaskComment).filter(TaskComment.task_id == t.id).count()
        invited = getattr(t, "invited_agent_ids", None)
        creator_agent = db.query(Agent).filter(Agent.id == t.creator_agent_id).first() if getattr(t, "creator_agent_id", None) else None
        out.append({
            "id": t.id,
            "title": t.title,
            "description": (t.description or "")[:200],
            "status": t.status,
            "priority": t.priority or "medium",
            "task_type": t.task_type or "general",
            "owner_id": t.owner_id,
            "publisher_name": owner.username if owner else "",
            "agent_id": t.agent_id,
            "creator_agent_id": getattr(t, "creator_agent_id", None),
            "creator_agent_name": creator_agent.name if creator_agent else None,
            "reward_points": getattr(t, "reward_points", 0) or 0,
            "subscription_count": sub_count,
            "comment_count": comment_count,
            "invited_agent_ids": invited if invited else [],
            "submitted_at": iso_utc(getattr(t, "submitted_at", None)),
            "verification_deadline_at": iso_utc(getattr(t, "verification_deadline_at", None)),
            "created_at": iso_utc(t.created_at),
            **task_extra(t, db),
        })
    total = db.query(Task).filter(Task.owner_id == uid).count()
    return {"tasks": out, "total": total}


