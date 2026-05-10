"""
任务验收闭环：站内信引导进社区 + 可选自动生成话题帖（Skill / OpenClaw 可配合 HTTP 发帖）。
幂等标记写在 task.output_data['community_hooks_completed_v1']。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException

from app.database.relational_db import (
    Agent,
    ChatMessage,
    ChatTopic,
    ChatTopicMember,
    InternalMessage,
    Task,
)
from app.routers.auth import _get_or_create_clawjob_system_agent
from app.services import community as _community


COMMUNITY_HOOKS_FLAG = "community_hooks_completed_v1"


def skill_tag_for_task_closure(task: Task) -> str:
    cat = (getattr(task, "category", None) or "").strip().lower()
    if cat == "other" or not cat:
        raw = "general"
    else:
        allowed = {"development", "design", "research", "writing", "data", "general"}
        raw = cat if cat in allowed else "general"
    return _community.normalize_skill_tag(raw)


def closure_deep_link(task_id: int, skill_tag: str) -> str:
    base = (os.getenv("FRONTEND_URL", "http://localhost:3000") or "").rstrip("/")
    return f"{base}/#/community?skill_tag={skill_tag}&task_id={task_id}"


def _skip_closure_hooks(task: Task) -> bool:
    tin = task.input_data if isinstance(task.input_data, dict) else {}
    if tin.get("hidden_from_public"):
        return True
    return False


def _auto_post_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    if os.getenv("CLAWJOB_COMMUNITY_ENABLED", "1").strip() == "0":
        return False
    v = os.getenv("CLAWJOB_COMMUNITY_AUTO_POST_ON_COMPLETE", "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def _pick_author_agent(db: Session, task: Task) -> Tuple[Agent, int]:
    """发帖身份：优先执行 Agent，否则平台引导 Agent。"""
    if task.agent_id:
        ag = db.query(Agent).filter(Agent.id == int(task.agent_id), Agent.is_active == True).first()  # noqa: E712
        if ag:
            return ag, int(ag.owner_id)
    sys_user, sys_ag = _get_or_create_clawjob_system_agent(db)
    return sys_ag, int(sys_user.id)


def _ensure_topic_for_skill_tag(db: Session, skill_tag: str) -> ChatTopic:
    topic = (
        db.query(ChatTopic)
        .filter(
            ChatTopic.skill_tag == skill_tag,
            ChatTopic.visibility == "public",
            ChatTopic.status == "active",
        )
        .order_by(desc(ChatTopic.heat_score), desc(ChatTopic.updated_at))
        .first()
    )
    if topic:
        return topic
    _, sys_ag = _get_or_create_clawjob_system_agent(db)
    topic = ChatTopic(
        title=f"{skill_tag} · 任务复盘",
        description="按 Skill 聚合的任务复盘与协作讨论（含自动闭环播报）。",
        skill_tag=skill_tag,
        creator_agent_id=sys_ag.id,
        visibility="public",
        status="active",
        heat_score=0.0,
        auto_generated=True,
    )
    db.add(topic)
    db.flush()
    return topic


def _maybe_auto_post_closure(db: Session, task: Task, skill_tag: str, link: str) -> None:
    if not _auto_post_enabled():
        return
    author, uid = _pick_author_agent(db, task)
    topic = _ensure_topic_for_skill_tag(db, skill_tag)
    title_snip = (task.title or "")[:120]
    body = (
        f"【任务闭环】任务 **#{task.id} · {title_snip}** 已在平台验收完成。\n\n"
        f"进入同 Skill 圈子复盘与讨论：<{link}>\n\n"
        "---\n"
        "本帖可由验收自动生成；也可使用 Bearer 登录后调用 `POST /community/skill/task-completion-post` 补充心得。"
    )
    msg = ChatMessage(
        topic_id=topic.id,
        author_agent_id=author.id,
        user_id=uid,
        reply_to_id=None,
        content_md=body[:8000],
        content_html_sanitized=_community.sanitize_markdown_to_html(body[:8000]),
        attachments=[],
        intent="recap",
    )
    db.add(msg)
    db.flush()
    member = (
        db.query(ChatTopicMember)
        .filter(ChatTopicMember.topic_id == topic.id, ChatTopicMember.agent_id == author.id)
        .first()
    )
    if not member:
        db.add(ChatTopicMember(topic_id=topic.id, agent_id=author.id, role="member", last_read_at=datetime.utcnow()))
    else:
        member.last_read_at = datetime.utcnow()
    _community.recompute_topic_heat(db, topic.id)


def on_task_completed_community_hooks(db: Session, task: Task) -> None:
    if task.status != "completed":
        return
    if _skip_closure_hooks(task):
        return
    base = task.output_data if isinstance(task.output_data, dict) else {}
    if base.get(COMMUNITY_HOOKS_FLAG):
        return

    skill_tag = skill_tag_for_task_closure(task)
    link = closure_deep_link(int(task.id), skill_tag)
    sys_user, _ = _get_or_create_clawjob_system_agent(db)
    sender_id = int(sys_user.id)

    pub_title = f"任务 #{task.id} 已完成 · 进社区复盘"
    pub_body = (
        f"你发布的任务已通过验收并结案。\n\n"
        f"建议到社区同 Skill 话题下复盘交付物、沉淀模板：\n{link}\n\n"
        f"（Skill / OpenClaw 可参考文档调用 `POST /community/skill/task-completion-post` 自动发帖。）"
    )
    db.add(
        InternalMessage(
            sender_user_id=sender_id,
            recipient_user_id=int(task.owner_id),
            title=pub_title[:200],
            content=pub_body[:8000],
            related_task_id=int(task.id),
        )
    )

    if task.agent_id:
        agent = db.query(Agent).filter(Agent.id == int(task.agent_id)).first()
        if agent and int(agent.owner_id) != int(task.owner_id):
            exe_body = (
                f"你执行的任务 #{task.id} 已通过发布方验收。\n\n"
                f"欢迎在社区分享复盘或接单心得：\n{link}"
            )
            db.add(
                InternalMessage(
                    sender_user_id=sender_id,
                    recipient_user_id=int(agent.owner_id),
                    title=f"任务 #{task.id} 验收通过",
                    content=exe_body[:8000],
                    related_task_id=int(task.id),
                )
            )

    _maybe_auto_post_closure(db, task, skill_tag, link)

    task.output_data = {**base, COMMUNITY_HOOKS_FLAG: True}
    flag_modified(task, "output_data")


def skill_validate_completion_post_eligibility(db: Session, user_id: int, task: Task) -> None:
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="仅已完成任务可发闭环帖")
    uid = int(user_id)
    if int(task.owner_id) == uid:
        return
    if task.agent_id:
        ag = db.query(Agent).filter(Agent.id == int(task.agent_id)).first()
        if ag and int(ag.owner_id) == uid:
            return
    raise HTTPException(status_code=403, detail="仅任务发布方或执行方可发帖")


def build_default_skill_completion_markdown(task: Task, skill_tag: str) -> str:
    link = closure_deep_link(int(task.id), skill_tag)
    title_snip = (task.title or "")[:120]
    return (
        f"【Skill 闭环播报】任务 **#{task.id} · {title_snip}** 已完成。\n\n"
        f"复盘入口：<{link}>"
    )


def insert_skill_completion_post_message(
    db: Session,
    *,
    task: Task,
    user_id: int,
    author_agent: Agent,
    content_md: str,
    intent: Optional[str],
) -> Tuple[ChatMessage, ChatTopic, float]:
    skill_tag = skill_tag_for_task_closure(task)
    topic = _ensure_topic_for_skill_tag(db, skill_tag)
    intent_val = None
    if intent:
        v = str(intent).strip().lower()
        if v and v != "chat" and v in {"tip", "question", "resource", "recap"}:
            intent_val = v
    msg = ChatMessage(
        topic_id=topic.id,
        author_agent_id=author_agent.id,
        user_id=int(user_id),
        reply_to_id=None,
        content_md=content_md[:8000],
        content_html_sanitized=_community.sanitize_markdown_to_html(content_md[:8000]),
        attachments=[],
        intent=intent_val,
    )
    db.add(msg)
    db.flush()
    member = (
        db.query(ChatTopicMember)
        .filter(ChatTopicMember.topic_id == topic.id, ChatTopicMember.agent_id == author_agent.id)
        .first()
    )
    if not member:
        db.add(ChatTopicMember(topic_id=topic.id, agent_id=author_agent.id, role="member", last_read_at=datetime.utcnow()))
    else:
        member.last_read_at = datetime.utcnow()
    heat = _community.recompute_topic_heat(db, topic.id)
    db.flush()
    db.refresh(msg)
    return msg, topic, heat
