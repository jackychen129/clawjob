"""
管理后台：核心指标、运行日志（仅 is_superuser 可访问）
"""
import csv
import io
import json
import os
import zipfile
from datetime import datetime, timedelta
from typing import Optional, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database.relational_db import (
    get_db, User, Task, Agent, SystemLog, CreditTransaction,
    SafetyEvent, ExecutionRun, ExecutionStep,
    KycRecord, WithdrawalRequest, Workspace, WorkspaceMember,
    UserCommissionRecord,
)
from app.services.escrow_tasks import get_escrow, save_escrow_to_task, apply_escrow_milestone_confirm
from app.services.task_timeline import append_timeline_event
from app.services import insights as _insights
from app.services import kyc as _kyc
from app.services import payout as _payout
from app.services import settlement as _settlement
from app.security import get_current_user

router = APIRouter(prefix="", tags=["Admin · 运营"])


def get_superuser_dep(get_current_user: Callable, get_db_fn: Callable):
    """返回「要求超级用户」的依赖，供 main 在 include_router 时注入。"""
    async def _require_superuser(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db_fn),
    ):
        uid = current_user.get("user_id")
        if uid is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要登录")
        try:
            uid_int = int(uid)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无效用户")
        user = db.query(User).filter(User.id == uid_int).first()
        if not user or not getattr(user, "is_superuser", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
        return {"user_id": uid, "username": getattr(user, "username", None)}
    return _require_superuser


@router.post("/community/dispatch-hot")
def admin_dispatch_community_hot(
    top_limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """手动触发社区热议站内信分发（与后台定时任务逻辑一致）。需管理员权限。"""
    if os.getenv("CLAWJOB_COMMUNITY_ENABLED", "1").strip() == "0":
        raise HTTPException(status_code=503, detail="community disabled")
    if os.getenv("CLAWJOB_COMMUNITY_HOT_DISPATCH_ENABLED", "1").strip() == "0":
        raise HTTPException(status_code=503, detail="hot dispatch disabled")
    from app.services import community as _community

    res = _community.dispatch_hot_topics(db, top_limit=top_limit)
    db.commit()
    return {"ok": True, **res}


@router.get("/overview")
def get_admin_overview(db: Session = Depends(get_db)):
    """运营仪表盘聚合：核心指标 + 待处理结算/争议/KYC/提现（减少 Admin UI 往返）。"""
    from app.services import settlement as _settlement

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)

    tasks_total = db.query(Task).count()
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    tasks_pending_verification = db.query(Task).filter(Task.status == "pending_verification").count()
    tasks_disputed = db.query(Task).filter(Task.status == "disputed").count()

    users_total = db.query(User).count()
    users_new_today = db.query(User).filter(User.created_at >= today_start).count()
    agents_total = db.query(Agent).count()
    agents_new_today = db.query(Agent).filter(Agent.created_at >= today_start).count()

    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0

    kyc_pending = db.query(KycRecord).filter(KycRecord.status == "pending").count()
    withdrawals_pending = db.query(WithdrawalRequest).filter(WithdrawalRequest.status == "pending").count()
    settlement_counts = _settlement.count_unpaid_settlements(db)

    requests_last_hour = db.query(SystemLog).filter(
        SystemLog.category == "request", SystemLog.created_at >= hour_ago,
    ).count()
    errors_last_hour = db.query(SystemLog).filter(
        SystemLog.level == "error", SystemLog.created_at >= hour_ago,
    ).count()

    return {
        "generated_at": now.isoformat() + "Z",
        "tasks": {
            "total": tasks_total,
            "open": tasks_open,
            "completed": tasks_completed,
            "pending_verification": tasks_pending_verification,
            "disputed": tasks_disputed,
        },
        "users": {"total": users_total, "new_today": users_new_today},
        "agents": {"total": agents_total, "new_today": agents_new_today},
        "rewards_paid": int(rewards_paid),
        "pending": {
            "kyc_reviews": kyc_pending,
            "withdrawals": withdrawals_pending,
            "disputed_tasks": tasks_disputed,
            "pending_verification_tasks": tasks_pending_verification,
            "settlements": settlement_counts,
        },
        "observability": {
            "requests_last_hour": int(requests_last_hour),
            "errors_last_hour": int(errors_last_hour),
        },
    }


@router.get("/metrics")
def get_metrics(
    db: Session = Depends(get_db),
):
    """核心指标：任务数、新注册人数、Agent 数等（含今日新增）。需管理员权限。"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)

    tasks_total = db.query(Task).count()
    tasks_open = db.query(Task).filter(Task.status == "open").count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    tasks_today = db.query(Task).filter(Task.created_at >= today_start).count()
    tasks_pending_verification = db.query(Task).filter(Task.status == "pending_verification").count()
    tasks_disputed = db.query(Task).filter(Task.status == "disputed").count()

    users_total = db.query(User).count()
    users_new_today = db.query(User).filter(User.created_at >= today_start).count()
    users_active_count = db.query(User).filter(User.is_active == True).count()

    agents_total = db.query(Agent).count()
    agents_today = db.query(Agent).filter(Agent.created_at >= today_start).count()
    agents_active = db.query(Agent).filter(Agent.is_active == True).count()

    rewards_paid = db.query(func.coalesce(func.sum(Task.reward_points), 0)).filter(
        Task.status == "completed", Task.reward_points.isnot(None)
    ).scalar() or 0

    requests_last_hour = db.query(SystemLog).filter(
        SystemLog.category == "request",
        SystemLog.created_at >= hour_ago,
    ).count()
    errors_last_hour = db.query(SystemLog).filter(
        SystemLog.level == "error",
        SystemLog.created_at >= hour_ago,
    ).count()

    from app.domain.agent_public import count_public_agents

    settlement_counts = _settlement.count_unpaid_settlements(db)

    return {
        "tasks": {
            "total": tasks_total,
            "open": tasks_open,
            "completed": tasks_completed,
            "today": tasks_today,
            "pending_verification": tasks_pending_verification,
            "disputed": tasks_disputed,
        },
        "users": {
            "total": users_total,
            "new_today": users_new_today,
            "active": users_active_count,
        },
        "agents": {
            "total": agents_total,
            "new_today": agents_today,
            "active": agents_active,
            "public": int(count_public_agents(db)),
        },
        "rewards_paid": int(rewards_paid),
        "pending_settlements": settlement_counts,
        "observability": {
            "requests_last_hour": int(requests_last_hour),
            "errors_last_hour": int(errors_last_hour),
        },
        "generated_at": now.isoformat(),
    }


@router.get("/settlements/pending")
def list_pending_settlements(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """agent_direct 待结算队列：status 非 paid（含待打款、待执行方确认）。"""
    items, total = _settlement.list_unpaid_settlements(db, skip=skip, limit=limit)
    return {"items": items, "total": total, "skip": skip, "limit": len(items)}


@router.get("/logs")
def get_logs(
    skip: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """分页查询系统日志（请求、认证、任务等）。"""
    q = db.query(SystemLog).order_by(desc(SystemLog.created_at))
    if level:
        q = q.filter(SystemLog.level == level)
    if category:
        q = q.filter(SystemLog.category == category)
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 500)).all()
    return {
        "items": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "level": r.level,
                "category": r.category,
                "message": r.message,
                "path": r.path,
                "method": r.method,
                "status_code": r.status_code,
                "user_id": r.user_id,
                "extra": r.extra,
            }
            for r in rows
        ],
        "total": total,
        "skip": skip,
        "limit": len(rows),
    }


@router.get("/me")
def admin_me():
    """确认当前用户为管理员（由路由级 dependency 校验），供前端判断是否展示管理入口。"""
    return {"ok": True, "is_superuser": True}

@router.get("/tasks/disputed")
def get_disputed_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Task).filter(Task.status == "disputed").order_by(desc(Task.updated_at), desc(Task.id))
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 200)).all()
    items = []
    for t in rows:
        escrow = get_escrow(t) or {}
        items.append({
            "id": t.id,
            "title": t.title,
            "owner_id": t.owner_id,
            "agent_id": t.agent_id,
            "status": t.status,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "dispute_reason": escrow.get("dispute_reason"),
            "dispute_evidence": escrow.get("dispute_evidence"),
            "current_index": int(escrow.get("current_index", 0) or 0),
            "milestones_total": len(escrow.get("milestones") or []),
        })
    return {"items": items, "total": total, "skip": skip, "limit": len(items)}


class EscrowDisputeResolveBody(BaseModel):
    note: str = ""
    resolution_type: str = "resume"


@router.post("/tasks/{task_id}/escrow/dispute/resolve")
def admin_resolve_escrow_dispute(
    task_id: int,
    body: EscrowDisputeResolveBody,
    db: Session = Depends(get_db),
):
    """解除托管争议冻结，恢复为可继续执行（in_progress / open）。"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    escrow = get_escrow(task)
    if not escrow:
        raise HTTPException(status_code=400, detail="该任务未启用托管")
    resolution_type = (body.resolution_type or "").strip() or "resume"

    # NOTE: translated comment in English.
    escrow["disputed"] = False
    escrow["dispute_reason"] = None
    if (body.note or "").strip():
        escrow["admin_resolve_note"] = (body.note or "").strip()[:2000]

    ms = escrow.get("milestones") or []
    current_index = int(escrow.get("current_index", 0) or 0)

    if resolution_type == "force_confirm":
        # NOTE: translated comment in English.
        task.status = "pending_verification"
        save_escrow_to_task(task, escrow)
        info = apply_escrow_milestone_confirm(task, db, auto=False)
        note_snip = (body.note or "").strip()[:200]
        append_timeline_event(
            task,
            "admin_escrow_resolved",
            "管理员裁决：强制确认当前里程碑并放款"
            + (f"。备注：{note_snip}" if note_snip else ""),
        )
        db.commit()
        return {
            "ok": True,
            "task_id": task_id,
            "status": task.status,
            "resolution_type": resolution_type,
            "escrow": {
                "milestone_index": info.get("milestone_index", current_index),
                "finished": bool(info.get("escrow_finished")),
            },
            "reward_paid": int(info.get("reward_paid", 0) or 0),
            "commission": int(info.get("commission", 0) or 0),
        }

    # NOTE: translated comment in English.
    save_escrow_to_task(task, escrow)
    task.status = "in_progress" if task.agent_id else "open"
    note_snip = (body.note or "").strip()[:200]
    append_timeline_event(
        task,
        "admin_escrow_resumed",
        "管理员裁决：解除争议冻结，任务恢复可执行"
        + (f"。备注：{note_snip}" if note_snip else ""),
    )
    db.commit()
    finished = current_index >= (len(ms) - 1) if ms else False
    return {
        "ok": True,
        "task_id": task_id,
        "status": task.status,
        "resolution_type": resolution_type,
        "escrow": {
            "milestone_index": current_index,
            "finished": finished,
        },
    }


# ===================== C-6 审计日志 ZIP 导出 =====================

_AUDIT_MAX_ROWS = 50000


def _parse_export_date(raw: Optional[str], *, default: datetime) -> datetime:
    if not raw:
        return default
    try:
        s = raw.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError:
        raise HTTPException(status_code=400, detail=f"时间格式无效：{raw}")


def _write_csv_to_zip(zf: zipfile.ZipFile, filename: str, header: list, rows: list) -> int:
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    count = 0
    for row in rows:
        writer.writerow(row)
        count += 1
    zf.writestr(filename, buf.getvalue().encode("utf-8"))
    return count


@router.get("/audit/export")
def export_audit_logs(
    start: Optional[str] = Query(None, description="起始时间 ISO8601；默认 30 天前"),
    end: Optional[str] = Query(None, description="结束时间 ISO8601；默认现在"),
    include: str = Query("system_logs,credit_transactions,tasks", description="逗号分隔：system_logs/credit_transactions/tasks"),
    max_rows: int = Query(50000, ge=100, le=200000),
    db: Session = Depends(get_db),
):
    """按时间区间导出审计日志 ZIP（含 CSV + manifest.json），满足合规审计。

    - 安全：仅超级用户可访问（由路由级依赖保护）
    - 幂等：同参数多次调用结果稳定
    - 限流：每类数据单次最多导出 `max_rows` 行，超过会在 manifest 标记 truncated=True
    """
    now = datetime.utcnow()
    default_start = now - timedelta(days=30)
    dt_start = _parse_export_date(start, default=default_start)
    dt_end = _parse_export_date(end, default=now)
    if dt_end <= dt_start:
        raise HTTPException(status_code=400, detail="end 必须晚于 start")
    if (dt_end - dt_start).days > 366:
        raise HTTPException(status_code=400, detail="单次导出区间不能超过 366 天")
    cap = int(max(100, min(max_rows, _AUDIT_MAX_ROWS)))
    wanted = {x.strip() for x in (include or "").split(",") if x.strip()}
    if not wanted:
        wanted = {"system_logs", "credit_transactions", "tasks"}
    allowed = {"system_logs", "credit_transactions", "tasks"}
    unknown = wanted - allowed
    if unknown:
        raise HTTPException(status_code=400, detail=f"include 含未知数据集：{','.join(sorted(unknown))}")

    buf = io.BytesIO()
    manifest = {
        "generated_at": now.isoformat() + "Z",
        "range": {
            "start": dt_start.isoformat() + "Z",
            "end": dt_end.isoformat() + "Z",
        },
        "max_rows": cap,
        "datasets": {},
    }
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if "system_logs" in wanted:
            q = (
                db.query(SystemLog)
                .filter(SystemLog.created_at >= dt_start, SystemLog.created_at < dt_end)
                .order_by(SystemLog.id.asc())
            )
            total = q.count()
            rows_raw = q.limit(cap).all()
            rows = [
                [
                    r.id,
                    r.created_at.isoformat() + "Z" if r.created_at else "",
                    r.level or "",
                    r.category or "",
                    r.message or "",
                    r.path or "",
                    r.method or "",
                    r.status_code if r.status_code is not None else "",
                    r.user_id if r.user_id is not None else "",
                    json.dumps(r.extra, ensure_ascii=False) if r.extra is not None else "",
                ]
                for r in rows_raw
            ]
            written = _write_csv_to_zip(
                zf,
                "system_logs.csv",
                ["id", "created_at", "level", "category", "message", "path", "method", "status_code", "user_id", "extra"],
                rows,
            )
            manifest["datasets"]["system_logs"] = {
                "total": int(total),
                "written": written,
                "truncated": int(total) > written,
            }

        if "credit_transactions" in wanted:
            q = (
                db.query(CreditTransaction)
                .filter(CreditTransaction.created_at >= dt_start, CreditTransaction.created_at < dt_end)
                .order_by(CreditTransaction.id.asc())
            )
            total = q.count()
            rows_raw = q.limit(cap).all()
            rows = [
                [
                    r.id,
                    r.created_at.isoformat() + "Z" if r.created_at else "",
                    r.user_id,
                    r.amount,
                    r.type or "",
                    r.ref_id if r.ref_id is not None else "",
                    r.remark or "",
                ]
                for r in rows_raw
            ]
            written = _write_csv_to_zip(
                zf,
                "credit_transactions.csv",
                ["id", "created_at", "user_id", "amount", "type", "ref_id", "remark"],
                rows,
            )
            manifest["datasets"]["credit_transactions"] = {
                "total": int(total),
                "written": written,
                "truncated": int(total) > written,
            }

        if "tasks" in wanted:
            q = (
                db.query(Task)
                .filter(Task.updated_at >= dt_start, Task.updated_at < dt_end)
                .order_by(Task.id.asc())
            )
            total = q.count()
            rows_raw = q.limit(cap).all()
            rows = [
                [
                    t.id,
                    t.title or "",
                    t.status or "",
                    t.task_type or "",
                    t.priority or "",
                    t.owner_id,
                    t.agent_id if t.agent_id is not None else "",
                    t.reward_points if t.reward_points is not None else 0,
                    t.category or "",
                    t.created_at.isoformat() + "Z" if t.created_at else "",
                    t.updated_at.isoformat() + "Z" if t.updated_at else "",
                    t.completed_at.isoformat() + "Z" if t.completed_at else "",
                ]
                for t in rows_raw
            ]
            written = _write_csv_to_zip(
                zf,
                "tasks.csv",
                [
                    "id", "title", "status", "task_type", "priority", "owner_id",
                    "agent_id", "reward_points", "category",
                    "created_at", "updated_at", "completed_at",
                ],
                rows,
            )
            manifest["datasets"]["tasks"] = {
                "total": int(total),
                "written": written,
                "truncated": int(total) > written,
            }

        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))

    buf.seek(0)
    filename = f"clawjob-audit-{dt_start.strftime('%Y%m%d')}-{dt_end.strftime('%Y%m%d')}.zip"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "private, no-store",
        "X-Audit-Rows": json.dumps(manifest["datasets"], ensure_ascii=False),
    }
    return StreamingResponse(buf, media_type="application/zip", headers=headers)


# ---------------------------------------------------------------------------
# C-13 内容安全 / PII 网关：审计事件只读查询
# ---------------------------------------------------------------------------


@router.get("/safety/events")
def list_safety_events(
    source: Optional[str] = Query(None, description="按触发来源过滤，如 publish_task/submit_completion/message"),
    action: Optional[str] = Query(None, description="过滤动作：block / redact"),
    related_task_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """超管只读查看近期内容安全事件（已脱敏）。"""
    q = db.query(SafetyEvent).order_by(SafetyEvent.created_at.desc())
    if source:
        q = q.filter(SafetyEvent.source == source.strip())
    if action:
        q = q.filter(SafetyEvent.action == action.strip())
    if related_task_id is not None:
        q = q.filter(SafetyEvent.related_task_id == int(related_task_id))
    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    items = [
        {
            "id": r.id,
            "created_at": (r.created_at.isoformat() + "Z") if r.created_at else None,
            "user_id": r.user_id,
            "source": r.source,
            "action": r.action,
            "reasons": list(r.reasons or []),
            "pii_types": list(r.pii_types or []),
            "related_task_id": r.related_task_id,
            "snippet": (r.snippet or "")[:400],
        }
        for r in rows
    ]
    return {"items": items, "total": int(total), "offset": offset, "limit": limit}


@router.get("/safety/stats")
def safety_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(SafetyEvent.action, SafetyEvent.source, func.count(SafetyEvent.id))
        .filter(SafetyEvent.created_at >= since)
        .group_by(SafetyEvent.action, SafetyEvent.source)
        .all()
    )
    by_action: dict = {}
    by_source: dict = {}
    for action, source, cnt in rows:
        by_action[action or "unknown"] = by_action.get(action or "unknown", 0) + int(cnt or 0)
        by_source[source or "unknown"] = by_source.get(source or "unknown", 0) + int(cnt or 0)
    return {
        "window_days": int(days),
        "by_action": by_action,
        "by_source": by_source,
        "total": int(sum(by_action.values())),
    }


# ---------------------------------------------------------------------------
# D-22 Insights：平台报表（超管）
# ---------------------------------------------------------------------------


@router.get("/insights/platform")
def platform_insights(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """平台侧 Insights：GMV、撮合漏斗、每日趋势、留存矩阵。"""
    return _insights.platform_report(db, days=days)


# ---------------------------------------------------------------------------
# C-14 KYC / KYB：审核
# ---------------------------------------------------------------------------


@router.get("/kyc/records")
def list_kyc_records(
    status: Optional[str] = None,
    kind: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(KycRecord).order_by(desc(KycRecord.submitted_at))
    if status:
        q = q.filter(KycRecord.status == status)
    if kind:
        q = q.filter(KycRecord.kind == kind)
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 200)).all()
    return {
        "total": total,
        "skip": skip,
        "items": [_kyc.serialize(r) for r in rows],
    }


class KycReviewBody(BaseModel):
    reason: Optional[str] = None


@router.post("/kyc/records/{record_id}/approve")
def approve_kyc(
    record_id: int,
    body: Optional[KycReviewBody] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rec = db.query(KycRecord).filter(KycRecord.id == record_id).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="KYC 记录不存在")
    reviewer_id = int(current_user.get("user_id") or 0)
    rec = _kyc.approve(db, rec, reviewer_id=reviewer_id)
    return _kyc.serialize(rec)


@router.post("/kyc/records/{record_id}/reject")
def reject_kyc(
    record_id: int,
    body: KycReviewBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rec = db.query(KycRecord).filter(KycRecord.id == record_id).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="KYC 记录不存在")
    reviewer_id = int(current_user.get("user_id") or 0)
    reason = (body.reason if body else "") or "未通过审核"
    rec = _kyc.reject(db, rec, reviewer_id=reviewer_id, reason=reason)
    return _kyc.serialize(rec)


# ---------------------------------------------------------------------------
# C-14 提现申请审批
# ---------------------------------------------------------------------------


@router.get("/withdrawals")
def list_withdrawals(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(WithdrawalRequest).order_by(desc(WithdrawalRequest.submitted_at))
    if status:
        q = q.filter(WithdrawalRequest.status == status)
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 200)).all()
    return {
        "total": total,
        "skip": skip,
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "amount": r.amount,
                "status": r.status,
                "receiving_account_type": r.receiving_account_type,
                "receiving_account_number": r.receiving_account_number,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
                "remark": r.remark,
            }
            for r in rows
        ],
    }


class WithdrawalDecisionBody(BaseModel):
    action: str  # mark_paid | reject
    remark: Optional[str] = None


@router.post("/withdrawals/{request_id}/decide")
def decide_withdrawal(
    request_id: int,
    body: WithdrawalDecisionBody,
    db: Session = Depends(get_db),
):
    req = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.id == request_id)
        .first()
    )
    if req is None:
        raise HTTPException(status_code=404, detail="提现申请不存在")
    if req.status not in ("pending",):
        raise HTTPException(status_code=400, detail=f"提现单状态为 {req.status}，无法审批")
    action = (body.action or "").strip().lower()
    if action == "mark_paid":
        req.status = "paid"
        req.processed_at = datetime.utcnow()
        req.remark = (body.remark or "已打款")[:512]
    elif action == "reject":
        req.status = "rejected"
        req.processed_at = datetime.utcnow()
        admin_note = (body.remark or "已驳回")[:512]
        hold = _payout.parse_hold(req.remark)
        user = db.query(User).filter(User.id == req.user_id).first()
        if user is not None and hold:
            _payout.refund_withdrawal_hold(db, user, withdrawal_id=req.id, hold=hold)
        elif user is not None:
            user.commission_balance = int(user.commission_balance or 0) + int(req.amount or 0)
            db.add(
                UserCommissionRecord(
                    user_id=req.user_id,
                    amount=int(req.amount or 0),
                    remark=f"提现申请 #{req.id} 驳回，余额回退 +{req.amount}",
                )
            )
        req.remark = admin_note
    else:
        raise HTTPException(status_code=400, detail="action 须为 mark_paid | reject")
    db.commit()
    db.refresh(req)
    return {
        "id": req.id,
        "status": req.status,
        "processed_at": req.processed_at.isoformat() if req.processed_at else None,
        "remark": req.remark,
    }


# ---------------------------------------------------------------------------
# D-17 工作区概览（运营）
# ---------------------------------------------------------------------------


@router.get("/workspaces")
def list_all_workspaces(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Workspace).order_by(desc(Workspace.created_at))
    total = q.count()
    rows = q.offset(skip).limit(min(limit, 200)).all()
    out = []
    for ws in rows:
        seats_used = (
            db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
        )
        out.append(
            {
                "id": ws.id,
                "name": ws.name,
                "slug": ws.slug,
                "plan": ws.plan,
                "seats": ws.seats,
                "seats_used": seats_used,
                "credits": ws.credits,
                "owner_user_id": ws.owner_user_id,
                "created_at": ws.created_at.isoformat() if ws.created_at else None,
            }
        )
    return {"total": total, "skip": skip, "items": out}
