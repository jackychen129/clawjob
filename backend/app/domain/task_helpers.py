"""Task domain helpers and constants."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.relational_db import (
    Agent,
    CreditTransaction,
    PlatformClearingAccount,
    PlatformCommissionRecord,
    PublishedSkill,
    SystemLog,
    Task,
    TaskBid,
    TaskComment,
    User,
    UserCommissionRecord,
)
from app.domain.agent_helpers import ensure_agents_category_column
from app.domain.skill_xp import task_related_skill
from app.services import reverse_auction as _ra
from app.services.escrow_tasks import apply_escrow_milestone_confirm, get_escrow
from app.services.task_timeline import append_timeline_event as _append_timeline_event
from app.utils.datetime_iso import iso_utc

CLAWJOB_SYSTEM_USERNAME = "clawjob_system"
CLAWJOB_SYSTEM_AGENT_NAME = "clawjob-agent"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# NOTE: translated comment in English.
VERIFICATION_HOURS_DEFAULT = 6  # 默认验收窗口（小时）；可被任务级 verification_hours 覆盖
VERIFICATION_HOURS_MIN = 1
VERIFICATION_HOURS_MAX = 168  # 最长 7 天
VERIFICATION_HOURS = 6  # 兼容旧代码与测试引用
VERIFICATION_EXTEND_HOURS = 24  # 发布方一键延长的小时数（每轮待验收限 1 次）
PLATFORM_COMMISSION_RATE = 0.01  # 默认佣金比例，可被环境变量覆盖（见下方 _env_float 调用）
MAX_TASK_REWARD_POINTS = 10_000_000  # 单任务奖励点数上限（防止拼写/恶意巨额发布）


def env_int(name: str, default: int, *, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
    raw = os.getenv(name)
    try:
        v = int(raw) if raw not in (None, "") else int(default)
    except (TypeError, ValueError):
        v = int(default)
    if min_value is not None:
        v = max(min_value, v)
    if max_value is not None:
        v = min(max_value, v)
    return v


def env_float(name: str, default: float, *, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
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


SKILL_DECAY_IDLE_DAYS = env_int("SKILL_DECAY_IDLE_DAYS", 14, min_value=1)
SKILL_DECAY_WEEKLY_RATIO = env_float("SKILL_DECAY_WEEKLY_RATIO", 0.02, min_value=0.0, max_value=1.0)
SKILL_DECAY_MAX_RATIO = env_float("SKILL_DECAY_MAX_RATIO", 0.2, min_value=0.0, max_value=1.0)

PLATFORM_COMMISSION_RATE = env_float(
    "PLATFORM_COMMISSION_RATE",
    PLATFORM_COMMISSION_RATE,
    min_value=0.0,
    max_value=0.5,
)


def compute_publish_fee(reward_points: int) -> dict:
    """根据奖励点计算发布费用拆分（统一口径，供发布/估算/校验复用）。"""
    rp = max(0, int(reward_points or 0))
    commission = int(rp * PLATFORM_COMMISSION_RATE) if rp else 0
    executor_net = max(0, rp - commission)
    return {
        "reward_points": rp,
        "commission_rate": PLATFORM_COMMISSION_RATE,
        "commission_points": commission,
        "executor_net_points": executor_net,
        "max_reward_points": MAX_TASK_REWARD_POINTS,
    }


def task_verification_hours(task: Task) -> int:
    d = task.input_data if isinstance(task.input_data, dict) else {}
    try:
        n = int(d.get("verification_hours", VERIFICATION_HOURS_DEFAULT))
        if VERIFICATION_HOURS_MIN <= n <= VERIFICATION_HOURS_MAX:
            return n
    except (TypeError, ValueError):
        pass
    return VERIFICATION_HOURS_DEFAULT


def task_payment_breakdown(task: Task, db: Session) -> dict:
    rp = int(getattr(task, "reward_points", 0) or 0)
    comm = int(rp * PLATFORM_COMMISSION_RATE) if rp else 0
    net = max(0, rp - comm)
    txs = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.ref_id == task.id, CreditTransaction.type == "task_reward")
        .order_by(CreditTransaction.created_at.asc())
        .all()
    )
    return {
        "reward_points": rp,
        "commission_rate": PLATFORM_COMMISSION_RATE,
        "commission_points": comm,
        "executor_net_points": net,
        "transactions": [
            {"amount": t.amount, "remark": (t.remark or "")[:300], "created_at": iso_utc(t.created_at)}
            for t in txs[:20]
        ],
    }
def push_task_to_discord(task: Task, webhook_url: str, frontend_url: str) -> None:
    """将任务信息推送到 Discord 频道（Webhook），便于 Agent 通过 Skill 发现并接取。"""
    if not webhook_url or not webhook_url.strip().startswith(("http://", "https://")):
        return
    task_link = f"{frontend_url}/tasks"
    if getattr(task, "id", None):
        task_link = f"{frontend_url}/tasks?taskId={task.id}"
    desc = (task.description or "").strip() or "无描述"
    if len(desc) > 150:
        desc = desc[:147] + "..."
    reward = getattr(task, "reward_points", 0) or 0
    category = (getattr(task, "category", None) or "").strip() or "—"
    extra = getattr(task, "input_data", None) or {}
    location = (extra.get("location") or "").strip() or "—"
    skills = extra.get("skills") or []
    skills_str = ", ".join(str(s) for s in skills[:5]) if skills else "—"
    fields = [
        {"name": "奖励点", "value": str(reward), "inline": True},
        {"name": "分类", "value": category, "inline": True},
        {"name": "地点", "value": location, "inline": True},
        {"name": "技能", "value": skills_str[:100], "inline": False},
        {"name": "接取方式", "value": "通过 ClawJob Skill 或打开任务大厅接取", "inline": False},
    ]
    payload = {
        "embeds": [
            {
                "title": (task.title or "新任务")[:256],
                "description": desc,
                "url": task_link,
                "color": 5814783,
                "fields": fields,
                "footer": {"text": "ClawJob"},
            }
        ]
    }
    try:
        import app.main as _app_main  # tests patch app.main.httpx
        with _app_main.httpx.Client(timeout=8.0) as client:
            client.post(webhook_url.strip(), json=payload)
    except Exception:
        pass  # 不因 Discord 失败而影响发布结果

def normalize_verification_method(raw: str) -> str:
    method = (raw or "manual_review").strip().lower()
    allowed = {"manual_review", "proof_link", "checklist", "hybrid"}
    return method if method in allowed else "manual_review"


def validate_verification_submission(task: Task, body: SubmitCompletionBody) -> None:
    extra = getattr(task, "input_data", None) or {}
    if not isinstance(extra, dict):
        return
    method = normalize_verification_method(extra.get("verification_method") or "manual_review")
    reqs = extra.get("verification_requirements") or []
    reqs = [str(x).strip() for x in reqs if str(x).strip()][:20]
    ev = body.evidence if isinstance(body.evidence, dict) else {}
    links = ev.get("proof_links") if isinstance(ev.get("proof_links"), list) else []
    links = [str(x).strip() for x in links if isinstance(x, str) and x.strip().startswith(("http://", "https://"))]
    completed = ev.get("completed_requirements") if isinstance(ev.get("completed_requirements"), list) else []
    completed = [str(x).strip() for x in completed if str(x).strip()]

    if method in ("proof_link", "hybrid") and not links:
        raise HTTPException(status_code=400, detail="该任务要求证据链接验收，请在 evidence.proof_links 提供至少一个 http(s) 链接")
    if method in ("checklist", "hybrid"):
        if not reqs:
            raise HTTPException(status_code=400, detail="该任务配置了清单验收，但发布方未配置 verification_requirements")
        missing = [x for x in reqs if x not in completed]
        if missing:
            raise HTTPException(status_code=400, detail=f"清单验收未完成：{', '.join(missing[:5])}")


def append_task_status_update_comment(db: Session, task: Task, user_id: int, content: str, agent_id: Optional[int] = None) -> None:
    try:
        row = TaskComment(
            task_id=int(task.id),
            user_id=int(user_id),
            agent_id=int(agent_id) if agent_id else None,
            kind="status_update",
            content=(content or "").strip()[:2000] or "status updated",
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()


def get_or_create_clearing_account(db: Session) -> PlatformClearingAccount:
    """获取或创建平台中转账户（单例，id=1）"""
    acc = db.query(PlatformClearingAccount).filter(PlatformClearingAccount.id == 1).first()
    if not acc:
        acc = PlatformClearingAccount(id=1, balance=0)
        db.add(acc)
        db.flush()
    return acc


CLAWJOB_SYSTEM_USERNAME = "clawjob_system"
CLAWJOB_SYSTEM_AGENT_NAME = "clawjob-agent"


def owner_display_name(username: Optional[str]) -> str:
    """拥有者展示名：游客账号显示「待注册」，否则显示用户名。"""
    if not username or (isinstance(username, str) and username.startswith("guest_")):
        return "待注册"
    return username


def get_or_create_clawjob_system_agent(db: Session):
    """获取或创建平台引导用系统 Agent（clawjob-agent），用于用户通过 Skill 发布的第一个任务自动接取并完成。返回 (User, Agent)。"""
    user = db.query(User).filter(User.username == CLAWJOB_SYSTEM_USERNAME).first()
    if not user:
        user = User(
            username=CLAWJOB_SYSTEM_USERNAME,
            email="system@clawjob.local",
            hashed_password="",
        )
        db.add(user)
        db.flush()
    ensure_agents_category_column()
    agent = db.query(Agent).filter(
        Agent.owner_id == user.id,
        Agent.name == CLAWJOB_SYSTEM_AGENT_NAME,
    ).first()
    if not agent:
        agent = Agent(
            name=CLAWJOB_SYSTEM_AGENT_NAME,
            description="平台引导 Agent：用户通过 Skill 发布的第一个任务将由此 Agent 自动接取并完成。",
            agent_type="general",
            category="api",
            owner_id=user.id,
            capabilities=[{"name": "clawjob", "category": "skill"}],
            config={},
            is_active=True,
        )
        db.add(agent)
        db.flush()
    return user, agent


def pay_task_reward(task: Task, db: Session) -> bool:
    """发放任务奖励：接取者得奖励；若已配置佣金则按比例计入发布者佣金余额。已完成则返回 False。"""
    if task.status == "completed":
        return False
    reward_points = getattr(task, "reward_points", 0) or 0
    invitee_user_id_for_referral: Optional[int] = None
    if reward_points > 0 and task.agent_id:
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if agent:
            receiver = db.query(User).filter(User.id == agent.owner_id).first()
            if receiver:
                commission = int(reward_points * PLATFORM_COMMISSION_RATE)
                amount_to_receiver = reward_points - commission
                receiver.credits = (getattr(receiver, "credits", 0) or 0) + amount_to_receiver
                remark = f"完成任务 #{task.id} 获得 {amount_to_receiver} 任务点"
                if commission > 0:
                    remark += f"（已配置佣金 {commission} 点）"
                tx = CreditTransaction(
                    user_id=agent.owner_id,
                    amount=amount_to_receiver,
                    type="task_reward",
                    ref_id=task.id,
                    remark=remark,
                )
                db.add(tx)
                invitee_user_id_for_referral = int(agent.owner_id)
                # NOTE: translated comment in English.
                if commission > 0 and task.owner_id:
                    publisher = db.query(User).filter(User.id == task.owner_id).first()
                    if publisher:
                        publisher.commission_balance = (getattr(publisher, "commission_balance", 0) or 0) + commission
                        ucr = UserCommissionRecord(
                            user_id=task.owner_id,
                            amount=commission,
                            task_id=task.id,
                            remark=f"任务 #{task.id} 佣金",
                        )
                        db.add(ucr)
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    if invitee_user_id_for_referral is not None:
        try:
            from app.services import referrals as _rf
            _rf.grant_first_task_reward(
                db,
                invitee_user_id=invitee_user_id_for_referral,
                trigger_task_id=task.id,
            )
        except Exception:
            pass
    try:
        maybe_settle_skill_revenue(task, db)
    except Exception:
        db.rollback()
    try:
        from app.services import community_task_hooks as _ct_hooks

        _ct_hooks.on_task_completed_community_hooks(db, task)
    except Exception:
        pass
    return True


def maybe_settle_skill_revenue(task: Task, db: Session) -> None:
    """任务关联的 Skill 若为付费类型，结算 invoke 分成（D-19）。
    幂等：同一 task 只结算一次；余额不足或作者缺失等异常静默处理。
    """
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    tok = (extra.get("related_skill_token") or "").strip()
    if not tok:
        return
    from app.services import skill_revenue as _skill_rev
    skill = (
        db.query(PublishedSkill)
        .filter(PublishedSkill.skill_token == tok)
        .first()
    )
    if skill is None or (skill.pricing_model or "free") == "free":
        return
    if int(skill.price_per_unit or 0) <= 0 or skill.author_user_id is None:
        return
    publisher = db.query(User).filter(User.id == task.owner_id).first()
    if publisher is None:
        return
    # 不向自己收费
    if skill.author_user_id == publisher.id:
        return
    try:
        _skill_rev.charge(
            db,
            skill=skill,
            consumer=publisher,
            event_kind="invoke",
            related_task_id=task.id,
        )
    except ValueError:
        # 余额不足或重复结算时，记录日志即可
        try:
            db.add(
                SystemLog(
                    level="warning",
                    category="task",
                    message="skill_revenue_charge_failed",
                    user_id=task.owner_id,
                    extra={
                        "task_id": task.id,
                        "skill_token": tok,
                    },
                )
            )
            db.commit()
        except Exception:
            db.rollback()


def maybe_auto_confirm(task: Task, db: Session) -> None:
    """若任务处于待验收且已过截止时间，自动验收并发奖。"""
    if task.status != "pending_verification" or not getattr(task, "verification_deadline_at", None):
        return
    deadline = task.verification_deadline_at
    if not (deadline and datetime.utcnow() >= deadline):
        return
    esc = get_escrow(task)
    if esc and esc.get("disputed"):
        return
    if esc:
        info = apply_escrow_milestone_confirm(task, db, auto=True)
        fin = bool(info.get("escrow_finished"))
        _append_timeline_event(
            task,
            "auto_milestone_confirmed",
            "验收截止未操作，系统自动确认当前里程碑并放款"
            + ("（全部里程碑已完成）" if fin else ""),
        )
        db.commit()
        return
    pay_task_reward(task, db)
    _append_timeline_event(task, "auto_confirmed", "验收截止未操作，系统自动确认并发奖")
    db.commit()
def task_extra(t: Task, db: Session) -> dict:
    """任务扩展字段：分类、要求、地点、时长、技能等"""
    d = getattr(t, "input_data", None) or {}
    if not isinstance(d, dict):
        d = {}
    esc = get_escrow(t)
    out = {
        "category": getattr(t, "category", None) or None,
        "requirements": getattr(t, "requirements", None) or None,
        "location": d.get("location") or None,
        "duration_estimate": d.get("duration_estimate") or None,
        "skills": d.get("skills") if isinstance(d.get("skills"), list) else None,
        "verification_method": normalize_verification_method(d.get("verification_method") or "manual_review"),
        "verification_requirements": d.get("verification_requirements") if isinstance(d.get("verification_requirements"), list) else [],
        "related_skill": task_related_skill(db, t, d),
        "collaborative": bool(d.get("collaborative")),
    }
    out["verification_hours"] = task_verification_hours(t)
    out["verification_extend_used"] = int(d.get("verification_extend_used", 0) or 0)
    if esc:
        ms = esc.get("milestones") or []
        idx = int(esc.get("current_index", 0) or 0)
        out["escrow"] = {
            "enabled": True,
            "milestone_count": len(ms),
            "current_index": idx,
            "released_points": int(esc.get("released_points", 0) or 0),
            "disputed": bool(esc.get("disputed")),
            "milestones_preview": [
                {
                    "title": m.get("title"),
                    "points": m.get("points"),
                    "acceptance_criteria": m.get("acceptance_criteria"),
                }
                for m in ms[:20]
            ],
            "dispute_reason": (esc.get("dispute_reason") or None),
            "dispute_evidence": esc.get("dispute_evidence") or None,
            "admin_resolve_note": (esc.get("admin_resolve_note") or None),
        }
    else:
        out["escrow"] = {"enabled": False}
    auction = _ra.get_auction(t)
    if auction:
        out["auction"] = {
            "enabled": True,
            "status": auction.get("status"),
            "min_reward": int(auction.get("min_reward", 0) or 0),
            "max_reward": int(auction.get("max_reward", 0) or 0),
            "deadline": auction.get("deadline"),
            "auto_pick": auction.get("auto_pick", "manual"),
            "selected_bid_id": auction.get("selected_bid_id"),
            "bid_count": int(auction.get("bid_count", 0) or 0),
            "is_open": _ra.is_auction_open(auction),
        }
    else:
        out["auction"] = {"enabled": False}
    badges: List[str] = []
    if esc and esc.get("enabled"):
        badges.append("escrow")
    reward_pts = int(getattr(t, "reward_points", 0) or 0)
    if reward_pts > 0:
        badges.append("verified_payout")
    out["badges"] = badges
    return out
def task_is_visible_to(task: Task, viewer_user_id: Optional[int], viewer_agent_ids: List[int]) -> bool:
    """定向任务可见性：仅发布者 + 被邀请 Agent 的拥有者可见。

    同时屏蔽标记为 hidden_from_public / 注册握手 / 平台系统账号发起的内部任务。
    发布者本人仍可见自己的隐藏任务。
    """
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    if isinstance(extra, dict):
        hidden = bool(extra.get("hidden_from_public"))
        source = (extra.get("source") or "").strip()
        if (hidden or source == "register_via_skill") and viewer_user_id != task.owner_id:
            return False
    visibility = extra.get("visibility") if isinstance(extra, dict) else None
    if visibility != "invitees_only":
        return True
    if viewer_user_id is not None and task.owner_id == viewer_user_id:
        return True
    invited = getattr(task, "invited_agent_ids", None) or []
    invited_ints = {int(x) for x in invited if x is not None}
    if viewer_agent_ids and invited_ints.intersection(set(viewer_agent_ids)):
        return True
    return False


CLAWJOB_SYSTEM_USERNAME = "clawjob_system"


def task_is_public_listing(task: Task, owner: Optional[User]) -> bool:
    """公开大厅/计数是否应当收录该任务（对所有访客一致的真实任务）。"""
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    if isinstance(extra, dict):
        if extra.get("hidden_from_public"):
            return False
        if (extra.get("source") or "").strip() == "register_via_skill":
            return False
    if owner is not None and owner.username == CLAWJOB_SYSTEM_USERNAME:
        return False
    return True


# NOTE: Intent-to-Task 内存限频：每用户 X 次/小时；重启/重部署会重置（正式上线可换 Redis）
INTENT_RATE_LIMIT_WINDOW = 3600
INTENT_RATE_LIMIT_MAX = int(os.getenv("CLAWJOB_INTENT_RATE_PER_HOUR", "30"))
intent_rate_bucket: Dict[int, List[float]] = {}


def intent_rate_check(user_id: int) -> Tuple[bool, int]:
    import time as _t
    max_limit = INTENT_RATE_LIMIT_MAX
    now = _t.time()
    window_start = now - INTENT_RATE_LIMIT_WINDOW
    bucket = intent_rate_bucket.setdefault(user_id, [])
    bucket[:] = [ts for ts in bucket if ts >= window_start]
    if len(bucket) >= max_limit:
        reset_in = int(max(0, (bucket[0] + INTENT_RATE_LIMIT_WINDOW) - now))
        return False, reset_in
    bucket.append(now)
    return True, 0
def require_auction_task(db: Session, task_id: int, *, lock: bool = False) -> Task:
    q = db.query(Task).filter(Task.id == task_id)
    try:
        if lock:
            q = q.with_for_update()
    except Exception:
        pass
    task = q.first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not _ra.get_auction(task):
        raise HTTPException(status_code=400, detail="该任务未开启反向竞标")
    return task


def serialize_auction_state(task: Task) -> Dict[str, Any]:
    a = _ra.get_auction(task) or {}
    return {
        "enabled": True,
        "status": a.get("status"),
        "min_reward": int(a.get("min_reward", 0) or 0),
        "max_reward": int(a.get("max_reward", 0) or 0),
        "deadline": a.get("deadline"),
        "auto_pick": a.get("auto_pick", "manual"),
        "selected_bid_id": a.get("selected_bid_id"),
        "awarded_at": a.get("awarded_at"),
        "bid_count": int(a.get("bid_count", 0) or 0),
        "is_open": _ra.is_auction_open(a),
    }

def award_bid_impl(task: Task, winning_bid: TaskBid, db: Session, *, auto: bool = False) -> Dict[str, Any]:
    """在已持有 task 行锁的上下文中执行判标。退差额、设接取者、关竞拍、置对手 lost。
    调用方负责 db.commit()。"""
    auction = _ra.get_auction(task) or {}
    original_reward = int(getattr(task, "reward_points", 0) or 0)
    price = int(winning_bid.price or 0)
    if price > original_reward:
        raise HTTPException(status_code=500, detail="报价高于任务预算，状态异常")
    refund = max(0, original_reward - price)
    if refund > 0:
        try:
            publisher = db.query(User).filter(User.id == task.owner_id).with_for_update().first()
        except Exception:
            publisher = db.query(User).filter(User.id == task.owner_id).first()
        if publisher:
            publisher.credits = int(getattr(publisher, "credits", 0) or 0) + refund
            db.add(
                CreditTransaction(
                    user_id=task.owner_id,
                    amount=refund,
                    type="task_publish_refund",
                    ref_id=task.id,
                    remark=f"任务 #{task.id} 竞标选标后退还差额 {refund} 点",
                )
            )
    task.reward_points = price
    task.agent_id = int(winning_bid.agent_id)
    if task.status == "open":
        task.status = "in_progress"
    winning_bid.status = "won"
    db.query(TaskBid).filter(
        TaskBid.task_id == task.id,
        TaskBid.id != winning_bid.id,
        TaskBid.status == "active",
    ).update({"status": "lost"}, synchronize_session=False)
    _ra.save_auction_to_task(task, _ra.mark_auction_awarded(auction, selected_bid_id=winning_bid.id))
    try:
        _append_timeline_event(
            task,
            "auction_awarded",
            f"中标价 {price} 点，接取 Agent ID={winning_bid.agent_id}"
            + ("（系统自动选标）" if auto else ""),
        )
    except Exception:
        pass
    return {
        "task_id": task.id,
        "winning_bid_id": winning_bid.id,
        "final_reward_points": price,
        "refunded_points": refund,
        "agent_id": winning_bid.agent_id,
    }
def a2a_can_access_task(task: Task, uid: int, db: Session) -> bool:
    """A2A：当前用户是否为任务发布者或接取者（Agent 所属用户）。"""
    if task.owner_id == uid:
        return True
    if task.agent_id:
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if agent and agent.owner_id == uid:
            return True
    return False
def can_view_task_runs(task: Task, uid: int, db: Session) -> bool:
    if task.owner_id == uid:
        return True
    if task.agent_id:
        a = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if a and a.owner_id == uid:
            return True
    u = db.query(User).filter(User.id == uid).first()
    return bool(u and getattr(u, "is_superuser", False))
