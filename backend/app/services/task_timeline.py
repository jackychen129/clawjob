"""任务时间线：统一写入 Task.input_data['timeline']，供详情接口展示。"""
from __future__ import annotations

import copy
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm.attributes import flag_modified

if TYPE_CHECKING:
    from app.database.relational_db import Task


def append_timeline_event(task: "Task", event_type: str, summary: str) -> None:
    base = copy.deepcopy(task.input_data) if isinstance(task.input_data, dict) else {}
    tl = base.get("timeline")
    if not isinstance(tl, list):
        tl = []
    tl.append(
        {
            "at": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "summary": (summary or "")[:500],
        }
    )
    base["timeline"] = tl[-100:]
    task.input_data = base
    try:
        flag_modified(task, "input_data")
    except Exception:
        pass
