"""Inbound webhooks (showcase completion, etc.)."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["Webhooks · 回调"])

@router.post("/webhooks/showcase-completion")
async def showcase_completion_webhook(request: Request):
    """系统展示任务（seed_open_tasks showcase）的完成回调：接受 POST，避免误用 GET-only /health 导致 405。"""
    try:
        await request.json()
    except Exception:
        pass
    return {"ok": True, "message": "showcase completion webhook received"}
