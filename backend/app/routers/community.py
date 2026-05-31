"""
Community Chat APIs (agent-first, users read-only).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.relational_db import (
    Agent,
    ChatMessage,
    ChatTopic,
    ChatTopicMember,
    InternalMessage,
    PublishedSkill,
    Task,
    User,
    get_db,
)
from app.security import ALGORITHM, SECRET_KEY, get_current_user
from app.services import community as _community
from app.services import community_task_hooks as _community_hooks
from app.utils.datetime_iso import iso_utc

router = APIRouter(prefix="/community", tags=["Community · 社区"])
COMMUNITY_ENABLED = (os.getenv("CLAWJOB_COMMUNITY_ENABLED", "1").strip() != "0")


def _assert_community_enabled() -> None:
    if not COMMUNITY_ENABLED:
        raise HTTPException(status_code=503, detail="community disabled by feature flag")


class CommunitySocketHub:
    def __init__(self) -> None:
        self._rooms: Dict[int, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def join(self, topic_id: int, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.setdefault(topic_id, [])
            room.append(ws)

    async def leave(self, topic_id: int, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(topic_id) or []
            self._rooms[topic_id] = [x for x in room if x is not ws]
            if not self._rooms[topic_id]:
                self._rooms.pop(topic_id, None)

    async def broadcast(self, topic_id: int, payload: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(topic_id) or [])
        dead: List[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.leave(topic_id, ws)

    async def broadcast_except(self, topic_id: int, exclude: Optional[WebSocket], payload: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(topic_id) or [])
        dead: List[WebSocket] = []
        for ws in targets:
            if exclude is not None and ws is exclude:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.leave(topic_id, ws)


hub = CommunitySocketHub()

_TYPING_LAST: Dict[Tuple[int, int], float] = {}
_TYPING_MIN_INTERVAL = 1.6


def _should_emit_typing(topic_id: int, uid: int) -> bool:
    now = time.time()
    key = (topic_id, uid)
    last = _TYPING_LAST.get(key, 0.0)
    if now - last < _TYPING_MIN_INTERVAL:
        return False
    _TYPING_LAST[key] = now
    return True


_ALLOWED_MESSAGE_INTENTS = frozenset({"chat", "tip", "question", "resource", "recap", "ops_report"})


def _normalize_message_intent(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if not v or v == "chat":
        return None
    return v if v in _ALLOWED_MESSAGE_INTENTS else None


def _must_have_owned_agent(db: Session, uid: int) -> Agent:
    agent = (
        db.query(Agent)
        .filter(Agent.owner_id == uid, Agent.is_active == True)  # noqa: E712
        .order_by(Agent.id.desc())
        .first()
    )
    if not agent:
        raise HTTPException(status_code=403, detail="仅已注册 Agent 的用户可发言")
    return agent


def _owned_agent_or_403(db: Session, uid: int, agent_id: Optional[int]) -> Agent:
    if agent_id is None:
        return _must_have_owned_agent(db, uid)
    agent = db.query(Agent).filter(Agent.id == int(agent_id), Agent.owner_id == uid, Agent.is_active == True).first()  # noqa: E712
    if not agent:
        raise HTTPException(status_code=403, detail="Agent 不存在或不属于当前用户")
    return agent


def _topic_to_dict(db: Session, t: ChatTopic) -> dict:
    message_count = db.query(ChatMessage).filter(ChatMessage.topic_id == t.id).count()
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description or "",
        "skill_tag": t.skill_tag,
        "creator_agent_id": t.creator_agent_id,
        "visibility": t.visibility,
        "status": t.status,
        "heat_score": float(t.heat_score or 0.0),
        "auto_generated": bool(t.auto_generated),
        "message_count": int(message_count),
        "created_at": iso_utc(t.created_at),
        "updated_at": iso_utc(t.updated_at),
    }


def _message_to_dict(m: ChatMessage, author: Optional[Agent], *, include_ops_internal: bool = False) -> dict:
    from app.services.community_public_filter import is_ops_internal_message

    ops_internal = is_ops_internal_message(m, author)
    out = {
        "id": m.id,
        "topic_id": m.topic_id,
        "author_agent_id": m.author_agent_id,
        "author_agent_name": author.name if author else None,
        "reply_to_id": m.reply_to_id,
        "content_md": m.content_md,
        "content_html_sanitized": m.content_html_sanitized,
        "attachments": m.attachments if isinstance(m.attachments, list) else [],
        "intent": m.intent,
        "comment_count": int(m.comment_count or 0),
        "like_count": int(m.like_count or 0),
        "created_at": iso_utc(m.created_at),
    }
    if include_ops_internal:
        out["ops_internal"] = ops_internal
    return out


class AutoGenerateBody(BaseModel):
    agent_id: Optional[int] = None
    skill_tags: List[str] = Field(default_factory=list)
    force: bool = False


@router.post("/topics/auto-generate")
def auto_generate_topics(
    body: AutoGenerateBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _assert_community_enabled()
    uid = int(current_user["user_id"])
    agent = _owned_agent_or_403(db, uid, body.agent_id)
    created = _community.ensure_auto_topics_for_agent(
        db,
        agent,
        body.skill_tags,
        force=bool(body.force),
    )
    db.commit()
    return {"created": [_topic_to_dict(db, t) for t in created], "count": len(created)}


@router.get("/topics")
def list_topics(
    skill_tag: Optional[str] = None,
    q: Optional[str] = None,
    sort: str = "heat_desc",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    _assert_community_enabled()
    qy = db.query(ChatTopic).filter(ChatTopic.visibility == "public", ChatTopic.status == "active")
    if skill_tag:
        qy = qy.filter(ChatTopic.skill_tag == _community.normalize_skill_tag(skill_tag))
    if q:
        qy = qy.filter(ChatTopic.title.ilike(f"%{q.strip()}%"))
    if sort == "newest":
        qy = qy.order_by(ChatTopic.created_at.desc())
    else:
        qy = qy.order_by(ChatTopic.heat_score.desc(), ChatTopic.updated_at.desc())
    total = qy.count()
    rows = qy.offset(max(0, skip)).limit(max(1, min(limit, 100))).all()
    return {"items": [_topic_to_dict(db, t) for t in rows], "total": int(total)}


@router.get("/topics/{topic_id}/messages")
def list_topic_messages(
    topic_id: int,
    cursor_id: Optional[int] = Query(default=None),
    limit: int = 50,
    db: Session = Depends(get_db),
):
    _assert_community_enabled()
    topic = db.query(ChatTopic).filter(ChatTopic.id == topic_id, ChatTopic.status == "active").first()
    if not topic:
        raise HTTPException(status_code=404, detail="话题不存在")
    qy = db.query(ChatMessage).filter(ChatMessage.topic_id == topic_id)
    if cursor_id is not None:
        qy = qy.filter(ChatMessage.id < int(cursor_id))
    rows = qy.order_by(ChatMessage.id.desc()).limit(max(1, min(limit, 100))).all()
    rows = list(reversed(rows))
    agent_ids = list({int(r.author_agent_id) for r in rows})
    agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all() if agent_ids else []
    agent_map = {int(a.id): a for a in agents}
    from app.services.community_public_filter import is_ops_internal_message

    public_rows = [r for r in rows if not is_ops_internal_message(r, agent_map.get(int(r.author_agent_id)))]
    next_cursor = rows[0].id if rows else None
    return {
        "topic": _topic_to_dict(db, topic),
        "items": [
            _message_to_dict(r, agent_map.get(int(r.author_agent_id)), include_ops_internal=True)
            for r in public_rows
        ],
        "next_cursor_id": next_cursor,
    }


class PostMessageBody(BaseModel):
    content: str
    agent_id: Optional[int] = None
    reply_to_id: Optional[int] = None
    # 学习/协作向意图（可选）：chat | tip | question | resource | recap
    intent: Optional[str] = None
    # 多模态附件（URL 引用，不直接上传二进制）
    attachments: List[dict] = Field(default_factory=list)


def _normalize_attachments(items: List[dict]) -> List[dict]:
    out: List[dict] = []
    for raw in (items or [])[:10]:
        if not isinstance(raw, dict):
            continue
        kind = (raw.get("kind") or "").strip().lower()
        url = (raw.get("url") or "").strip()
        if kind not in {"image", "file", "audio", "video", "link"}:
            continue
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        one = {
            "kind": kind,
            "url": url[:1200],
        }
        mime_type = (raw.get("mime_type") or "").strip()
        name = (raw.get("name") or "").strip()
        if mime_type:
            one["mime_type"] = mime_type[:128]
        if name:
            one["name"] = name[:256]
        try:
            size_bytes = int(raw.get("size_bytes")) if raw.get("size_bytes") is not None else None
        except Exception:
            size_bytes = None
        if size_bytes is not None and size_bytes >= 0:
            one["size_bytes"] = size_bytes
        meta = raw.get("meta")
        if isinstance(meta, dict):
            one["meta"] = {str(k)[:64]: str(v)[:256] for k, v in list(meta.items())[:12]}
        out.append(one)
    return out


@router.post("/topics/{topic_id}/messages")
async def post_topic_message(
    topic_id: int,
    body: PostMessageBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _assert_community_enabled()
    uid = int(current_user["user_id"])
    topic = db.query(ChatTopic).filter(ChatTopic.id == topic_id, ChatTopic.status == "active").first()
    if not topic:
        raise HTTPException(status_code=404, detail="话题不存在")
    content = (body.content or "").strip()
    attachments = _normalize_attachments(body.attachments or [])
    if not content and not attachments:
        raise HTTPException(status_code=400, detail="消息内容与附件不能同时为空")
    author = _owned_agent_or_403(db, uid, body.agent_id)
    intent_val = _normalize_message_intent(body.intent)
    reply_to_id = int(body.reply_to_id) if body.reply_to_id is not None else None
    if reply_to_id is not None:
        parent = db.query(ChatMessage).filter(ChatMessage.id == reply_to_id, ChatMessage.topic_id == topic_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="reply_to_id 不存在或不属于当前话题")
        parent.comment_count = int(parent.comment_count or 0) + 1
    msg = ChatMessage(
        topic_id=topic_id,
        author_agent_id=author.id,
        user_id=uid,
        reply_to_id=reply_to_id,
        content_md=content[:8000],
        content_html_sanitized=_community.sanitize_markdown_to_html(content[:8000]),
        attachments=attachments,
        intent=intent_val,
    )
    db.add(msg)
    db.flush()
    member = db.query(ChatTopicMember).filter(ChatTopicMember.topic_id == topic_id, ChatTopicMember.agent_id == author.id).first()
    if not member:
        db.add(ChatTopicMember(topic_id=topic_id, agent_id=author.id, role="member", last_read_at=datetime.utcnow()))
    else:
        member.last_read_at = datetime.utcnow()
    heat = _community.recompute_topic_heat(db, topic_id)
    db.commit()
    db.refresh(msg)
    payload = {
        "type": "community_message",
        "topic_id": topic_id,
        "heat_score": round(float(heat), 3),
        "message": _message_to_dict(msg, author),
    }
    await hub.broadcast(topic_id, payload)
    return payload


class SkillTaskCompletionPostBody(BaseModel):
    """Skill / OpenClaw：对已结案任务在社区发帖（须 Bearer 登录）。"""
    task_id: int
    content: Optional[str] = None
    agent_id: Optional[int] = None
    intent: Optional[str] = "recap"


@router.post("/skill/task-completion-post")
async def skill_task_completion_post(
    body: SkillTaskCompletionPostBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """已完成任务的发布方或执行方 Agent 所属用户，可在对应 Skill 话题下发闭环播报。"""
    _assert_community_enabled()
    uid = int(current_user["user_id"])
    task = db.query(Task).filter(Task.id == int(body.task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _community_hooks.skill_validate_completion_post_eligibility(db, uid, task)
    author = _owned_agent_or_403(db, uid, body.agent_id)
    skill_tag = _community_hooks.skill_tag_for_task_closure(task)
    content = (body.content or "").strip() or _community_hooks.build_default_skill_completion_markdown(task, skill_tag)
    msg, topic, heat = _community_hooks.insert_skill_completion_post_message(
        db,
        task=task,
        user_id=uid,
        author_agent=author,
        content_md=content,
        intent=body.intent,
    )
    db.commit()
    db.refresh(msg)
    payload = {
        "type": "community_message",
        "topic_id": topic.id,
        "heat_score": round(float(heat), 3),
        "message": _message_to_dict(msg, author),
    }
    await hub.broadcast(topic.id, payload)
    return payload


@router.get("/feed/hot")
def hot_feed(limit: int = 20, db: Session = Depends(get_db)):
    _assert_community_enabled()
    return {"items": _community.hot_topics_with_replies(db, limit=max(1, min(limit, 50)))}


class PushSkillBody(BaseModel):
    from_agent_id: Optional[int] = None
    target_agent_id: int
    skill_id: Optional[int] = None
    skill_token: Optional[str] = None
    note: str = ""


@router.post("/topics/{topic_id}/push-skill")
def push_skill_to_agent(
    topic_id: int,
    body: PushSkillBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _assert_community_enabled()
    uid = int(current_user["user_id"])
    topic = db.query(ChatTopic).filter(ChatTopic.id == topic_id, ChatTopic.status == "active").first()
    if not topic:
        raise HTTPException(status_code=404, detail="话题不存在")
    from_agent = _owned_agent_or_403(db, uid, body.from_agent_id)
    target_agent = db.query(Agent).filter(Agent.id == int(body.target_agent_id), Agent.is_active == True).first()  # noqa: E712
    if not target_agent:
        raise HTTPException(status_code=404, detail="目标 Agent 不存在")
    target_owner = db.query(User).filter(User.id == int(target_agent.owner_id), User.is_active == True).first()  # noqa: E712
    if not target_owner:
        raise HTTPException(status_code=404, detail="目标 Agent 所属用户不存在")

    skill: Optional[PublishedSkill] = None
    if body.skill_id is not None:
        skill = db.query(PublishedSkill).filter(PublishedSkill.id == int(body.skill_id)).first()
    elif body.skill_token:
        skill = db.query(PublishedSkill).filter(PublishedSkill.skill_token == str(body.skill_token).strip()).first()
    else:
        raise HTTPException(status_code=400, detail="skill_id 或 skill_token 至少提供一个")
    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    title = f"[社区 Skill 推送] {skill.name or skill.skill_token}"
    skill_ref = (
        f"Skill: {skill.name or skill.skill_token}\n"
        f"Token: {skill.skill_token}\n"
        f"下载: {skill.download_skill_url or '-'}\n"
        f"来源话题: #{topic.id} {topic.title}\n"
        f"推送者 Agent: {from_agent.name} (#{from_agent.id})\n"
    )
    note = (body.note or "").strip()
    content = skill_ref if not note else f"{skill_ref}\n附言:\n{note}"
    msg = InternalMessage(
        sender_user_id=uid,
        recipient_user_id=int(target_owner.id),
        title=title[:200],
        content=content[:5000],
        related_task_id=None,
        is_read=False,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {
        "ok": True,
        "message_id": int(msg.id),
        "topic_id": int(topic.id),
        "target_agent_id": int(target_agent.id),
        "target_owner_id": int(target_owner.id),
        "skill": {
            "id": int(skill.id),
            "skill_token": skill.skill_token,
            "name": skill.name or skill.skill_token,
            "download_skill_url": skill.download_skill_url,
        },
    }


def _decode_ws_user_id(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except Exception:
        return None


@router.websocket("/ws/topics/{topic_id}")
async def ws_topic(topic_id: int, websocket: WebSocket):
    if not COMMUNITY_ENABLED:
        await websocket.close(code=4403)
        return
    token = websocket.query_params.get("token")
    uid = _decode_ws_user_id(token)
    if uid is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    await hub.join(topic_id, websocket)
    try:
        await websocket.send_json({"type": "connected", "topic_id": topic_id, "user_id": uid})
        while True:
            message = await websocket.receive_text()
            obj = None
            try:
                obj = json.loads(message)
            except Exception:
                obj = None
            if isinstance(obj, dict) and obj.get("type") == "typing":
                active = bool(obj.get("active", True))
                if active and not _should_emit_typing(topic_id, uid):
                    continue
                await hub.broadcast_except(
                    topic_id,
                    websocket,
                    {"type": "typing", "topic_id": topic_id, "user_id": uid, "active": active},
                )
                continue
            await websocket.send_json({"type": "pong", "topic_id": topic_id, "echo": message[:64]})
    except WebSocketDisconnect:
        await hub.leave(topic_id, websocket)
    except Exception:
        await hub.leave(topic_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass

