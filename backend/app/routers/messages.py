"""Internal messaging APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import InternalMessage, Task, User, get_db
from app.security import get_current_user
from app.services import safety_pipeline as _safety
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["Messages · 站内信"])


class InternalMessageBody(BaseModel):
    recipient_user_id: Optional[int] = None
    recipient_username: str = ""
    title: str
    content: str
    related_task_id: Optional[int] = None

@router.post("/messages")
def send_internal_message(
    body: InternalMessageBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发送站内信：按用户 ID 或用户名发送。"""
    uid = int(current_user["user_id"])
    title = (body.title or "").strip()
    content = (body.content or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    try:
        safe_title = _safety.sanitize_text(None, title, source="message", user_id=uid)
        safe_content = _safety.sanitize_text(None, content, source="message", user_id=uid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"内容安全策略：{str(e)}")
    title = safe_title or title
    content = safe_content or content
    recipient = None
    if body.recipient_user_id is not None:
        recipient = db.query(User).filter(User.id == int(body.recipient_user_id)).first()
    elif (body.recipient_username or "").strip():
        recipient = db.query(User).filter(User.username == body.recipient_username.strip()).first()
    else:
        raise HTTPException(status_code=400, detail="请提供 recipient_user_id 或 recipient_username")
    if not recipient:
        raise HTTPException(status_code=404, detail="收件人不存在")
    if recipient.id == uid:
        raise HTTPException(status_code=400, detail="不能给自己发送站内信")
    related_task_id = int(body.related_task_id) if body.related_task_id is not None else None
    if related_task_id is not None:
        t = db.query(Task).filter(Task.id == related_task_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="关联任务不存在")
    msg = InternalMessage(
        sender_user_id=uid,
        recipient_user_id=recipient.id,
        title=title[:200],
        content=content[:5000],
        related_task_id=related_task_id,
        is_read=False,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "message": "发送成功"}


@router.get("/messages/inbox")
def list_inbox_messages(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我的站内信收件箱。"""
    uid = int(current_user["user_id"])
    q = db.query(InternalMessage).filter(InternalMessage.recipient_user_id == uid)
    if unread_only:
        q = q.filter(InternalMessage.is_read == False)  # noqa: E712
    rows = q.order_by(InternalMessage.created_at.desc()).offset(skip).limit(limit).all()
    out = []
    for m in rows:
        sender = db.query(User).filter(User.id == m.sender_user_id).first()
        out.append({
            "id": m.id,
            "title": m.title,
            "content": m.content,
            "sender_user_id": m.sender_user_id,
            "sender_username": sender.username if sender else "",
            "recipient_user_id": m.recipient_user_id,
            "related_task_id": m.related_task_id,
            "is_read": bool(m.is_read),
            "read_at": iso_utc(m.read_at),
            "created_at": iso_utc(m.created_at),
        })
    total = q.count()
    unread = db.query(InternalMessage).filter(
        InternalMessage.recipient_user_id == uid,
        InternalMessage.is_read == False,  # noqa: E712
    ).count()
    return {"items": out, "total": total, "unread": unread}


@router.get("/messages/sent")
def list_sent_messages(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我发送的站内信。"""
    uid = int(current_user["user_id"])
    rows = (
        db.query(InternalMessage)
        .filter(InternalMessage.sender_user_id == uid)
        .order_by(InternalMessage.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    out = []
    for m in rows:
        recipient = db.query(User).filter(User.id == m.recipient_user_id).first()
        out.append({
            "id": m.id,
            "title": m.title,
            "content": m.content,
            "recipient_user_id": m.recipient_user_id,
            "recipient_username": recipient.username if recipient else "",
            "related_task_id": m.related_task_id,
            "is_read": bool(m.is_read),
            "read_at": iso_utc(m.read_at),
            "created_at": iso_utc(m.created_at),
        })
    total = db.query(InternalMessage).filter(InternalMessage.sender_user_id == uid).count()
    return {"items": out, "total": total}


@router.post("/messages/{message_id}/read")
def mark_message_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """将收件箱中的站内信标记为已读。"""
    uid = int(current_user["user_id"])
    msg = db.query(InternalMessage).filter(InternalMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    if msg.recipient_user_id != uid:
        raise HTTPException(status_code=403, detail="仅收件人可标记已读")
    if not msg.is_read:
        msg.is_read = True
        msg.read_at = datetime.utcnow()
        db.commit()
    return {"ok": True, "id": msg.id, "is_read": True, "read_at": iso_utc(msg.read_at)}
