"""Filter ops / auto daily reports from public community listings."""
from __future__ import annotations

import os
import re
from typing import Optional

from app.database.relational_db import Agent, ChatMessage

_OPS_AGENT_IDS: Optional[set] = None

_OPS_CONTENT_MARKERS = (
    "每日增长运营日报",
    "ClawJob 日报",
    "📊 ClawJob 日报",
    "ClawJob 每日增长运营",
)

_OPS_AUTHOR_NAME_RE = re.compile(r"clawjob[-_\s]?ops", re.I)


def _ops_agent_ids() -> set:
    global _OPS_AGENT_IDS
    if _OPS_AGENT_IDS is None:
        raw = os.getenv("CLAWJOB_OPS_AGENT_IDS", "103").strip()
        ids = set()
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        _OPS_AGENT_IDS = ids or {103}
    return _OPS_AGENT_IDS


def is_ops_internal_message(msg: ChatMessage, author: Optional[Agent] = None) -> bool:
    """True when message is automated ops recap (excluded from public hot feed / topic lists)."""
    intent = (msg.intent or "").strip().lower()
    if intent == "ops_report":
        return True
    md = (msg.content_md or "").strip()
    if not md:
        return False
    if any(marker in md for marker in _OPS_CONTENT_MARKERS):
        return True
    if author:
        if int(author.id) in _ops_agent_ids():
            if "日报" in md and ("Agent" in md or "agent_direct" in md or "/stats" in md):
                return True
        name = (author.name or "").strip()
        if name and _OPS_AUTHOR_NAME_RE.search(name):
            if "日报" in md or "每日增长" in md:
                return True
    return False
