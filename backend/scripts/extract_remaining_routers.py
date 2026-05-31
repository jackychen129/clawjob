#!/usr/bin/env python3
"""Extract remaining inline routes from main.py into dedicated routers."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app" / "main.py"
lines = MAIN.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def transform(code: str) -> str:
    return code.replace("@app.", "@router.")


# Line ranges from current main.py (1-based inclusive)
SECTIONS = {
    "stats": (271, 528),  # health through leaderboard (before blank lines)
    "agent_skills": (533, 573),
    "account_skill_tree": (576, 612),
    "stats_roi": (615, 632),
    "agent_templates_helpers": (635, 662),
    "agent_templates": (665, 794),
    "skill_models": (797, 831),
    "skill_helpers": (834, 888),
    "skills_packs": (891, 954),
    "well_known": (957, 1064),
    "skills_routes": (1067, 1354),
    "account_insights": (1366, 1374),
    "platform_admin": (1378, 1453),
    "preflight_runtime": (1456, 1505),
    "memory_tools": (1508, 1538),
    "webhook": (298, 305),
    "public": (352, 392),
    "activity_helper": (395, 399),
}

HEADERS = {
    "stats": '''"""Public stats, health, activity, leaderboard."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.systems import cache_db, relational_db, vector_db
from app.database.relational_db import Agent, Task, User, get_db
from app.domain.task_helpers import owner_display_name as _owner_display_name, task_is_public_listing
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["Public · 统计与动态"])

_CLAWJOB_ENTERPRISE = os.getenv("CLAWJOB_ENTERPRISE", "0").strip() not in ("0", "false", "no", "")


def _safe_int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except (TypeError, ValueError):
        return default


def _activity_agent_is_internal(agent: Agent, owner: Optional[User]) -> bool:
    from app.domain.agent_public import agent_is_public
    return not agent_is_public(agent, owner)


''',
    "public": '''"""Agent discovery: well-known manifest, public feeds, capabilities index."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.relational_db import Task, get_db

router = APIRouter(tags=["Public · Agent 发现"])

''',
    "webhooks": '''"""Inbound webhooks (showcase completion, etc.)."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["Webhooks · 回调"])

''',
    "skills": '''"""Skill marketplace, agent templates, scenario packs."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    Agent, PublishedAgentTemplate, PublishedSkill, SystemLog, Task, User, get_db,
)
from app.domain.skill_xp import task_related_skill
from app.domain.task_helpers import task_extra as _task_extra
from app.security import get_current_user
from app.services.preflight import enforce_preflight
from app.services.skill_contract import validate_contract, validate_payload
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["Skills · Skill 市场"])

''',
    "platform": '''"""Platform clearing account (admin key)."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    PlatformClearingAccount, PlatformCommissionRecord, get_db,
)
from app.domain.task_helpers import get_or_create_clearing_account
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["Admin · 平台账户"])

PLATFORM_ADMIN_KEY = os.getenv("PLATFORM_ADMIN_KEY", "").strip()


def _require_platform_admin(x_platform_admin_key: str = Header(None, alias="X-Platform-Admin-Key")):
    if not PLATFORM_ADMIN_KEY:
        raise HTTPException(status_code=503, detail="未配置 PLATFORM_ADMIN_KEY，无法管理中转账户")
    if x_platform_admin_key != PLATFORM_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="需要平台管理员密钥")


class ClearingAccountUpdateBody(BaseModel):
    alipay_account: str = None
    alipay_name: str = None


''',
    "runtime": '''"""Preflight, circuit breakers, memory & tool systems (legacy agent runtime)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.systems import memory_system, runtime_guard, tool_system
from app.database.relational_db import SystemLog, User, get_db
from app.security import get_current_user
from app.services.preflight import run_preflight

router = APIRouter(tags=["Legacy · Agent 运行时"])


class CircuitBreakerControlBody(BaseModel):
    host: str
    action: str  # reset | open | half_open | close


''',
}

OUT = ROOT / "app" / "routers"

# stats: health + public routes + activity helper + activity + leaderboard + roi
stats_body = (
    HEADERS["stats"]
    + transform(slice_lines(271, 296))  # health
    + "\n"
    + transform(slice_lines(308, 349))  # stats + recent-agents
    + transform(slice_lines(402, 528))  # activity + leaderboard
    + transform(slice_lines(615, 632))  # roi-series
)
(OUT / "stats.py").write_text(stats_body, encoding="utf-8")

# public: referral + opportunities + well-known + capabilities stub appended manually
public_body = (
    HEADERS["public"]
    + transform(slice_lines(352, 392))
    + transform(slice_lines(957, 1064))
)
(OUT / "public.py").write_text(public_body, encoding="utf-8")

# webhooks
webhooks_body = HEADERS["webhooks"] + transform(slice_lines(298, 305))
(OUT / "webhooks.py").write_text(webhooks_body, encoding="utf-8")

# skills: helpers + models + all skill routes + agent templates
skills_body = (
    HEADERS["skills"]
    + slice_lines(635, 662)  # helpers
    + slice_lines(797, 831)  # models
    + slice_lines(834, 888)  # github fetch
    + transform(slice_lines(665, 794))  # agent templates
    + transform(slice_lines(891, 954))  # packs
    + transform(slice_lines(1067, 1354))  # skills CRUD
)
(OUT / "skills.py").write_text(skills_body, encoding="utf-8")

# platform
platform_body = (
    HEADERS["platform"]
    + transform(slice_lines(1394, 1453))
)
(OUT / "platform.py").write_text(platform_body, encoding="utf-8")

# runtime
runtime_body = (
    HEADERS["runtime"]
    + transform(slice_lines(1456, 1505))
    + transform(slice_lines(1508, 1538))
)
(OUT / "runtime.py").write_text(runtime_body, encoding="utf-8")

# agent skills + account skill-tree + insights as append files for manual merge
extras = {
    "agents_skills_snippet.py": transform(slice_lines(533, 573)),
    "account_extras_snippet.py": transform(slice_lines(576, 612)) + transform(slice_lines(1366, 1374)),
}
for name, content in extras.items():
    (ROOT / "scripts" / name).write_text(content, encoding="utf-8")

print("Extracted routers to app/routers/")
print("Snippets for agents.py and account.py in scripts/")
