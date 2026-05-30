#!/usr/bin/env python3
"""Rebuild split modules cleanly from main.py line ranges."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8").splitlines(keepends=True)


def sl(start: int, end: int) -> str:
    return "".join(MAIN[start - 1 : end])


def rename_helpers(code: str) -> str:
    mapping = [
        ("_FRONTEND_URL", "FRONTEND_URL"),
        ("_ensure_agents_category_column", "ensure_agents_category_column"),
        ("_CLAWJOB_SYSTEM_USERNAME", "CLAWJOB_SYSTEM_USERNAME"),
        ("_INTENT_RATE_LIMIT_WINDOW", "INTENT_RATE_LIMIT_WINDOW"),
        ("_INTENT_RATE_LIMIT_MAX", "INTENT_RATE_LIMIT_MAX"),
        ("_intent_rate_bucket", "intent_rate_bucket"),
        ("def _env_int", "def env_int"),
        ("def _env_float", "def env_float"),
        ("def _compute_publish_fee", "def compute_publish_fee"),
        ("def _task_verification_hours", "def task_verification_hours"),
        ("def _task_payment_breakdown", "def task_payment_breakdown"),
        ("def _push_task_to_discord", "def push_task_to_discord"),
        ("def _normalize_verification_method", "def normalize_verification_method"),
        ("def _validate_verification_submission", "def validate_verification_submission"),
        ("def _append_task_status_update_comment", "def append_task_status_update_comment"),
        ("def _get_or_create_clearing_account", "def get_or_create_clearing_account"),
        ("def _owner_display_name", "def owner_display_name"),
        ("def _get_or_create_clawjob_system_agent", "def get_or_create_clawjob_system_agent"),
        ("def _pay_task_reward", "def pay_task_reward"),
        ("def _maybe_settle_skill_revenue", "def maybe_settle_skill_revenue"),
        ("def _maybe_auto_confirm", "def maybe_auto_confirm"),
        ("def _task_extra", "def task_extra"),
        ("def _task_is_visible_to", "def task_is_visible_to"),
        ("def _task_is_public_listing", "def task_is_public_listing"),
        ("def _intent_rate_check", "def intent_rate_check"),
        ("def _require_auction_task", "def require_auction_task"),
        ("def _serialize_auction_state", "def serialize_auction_state"),
        ("def _award_bid_impl", "def award_bid_impl"),
        ("def _a2a_can_access_task", "def a2a_can_access_task"),
        ("def _can_view_task_runs", "def can_view_task_runs"),
        ("_task_related_skill", "task_related_skill"),
        ("_pay_task_reward", "pay_task_reward"),
        ("_normalize_verification_method", "normalize_verification_method"),
        ("_task_verification_hours", "task_verification_hours"),
        ("_env_int(", "env_int("),
        ("_env_float(", "env_float("),
        ("_require_auction_task(", "require_auction_task("),
        ("_serialize_auction_state(", "serialize_auction_state("),
        ("_award_bid_impl(", "award_bid_impl("),
    ]
    for old, new in mapping:
        code = code.replace(old, new)
    return code


def strip_embedded_models(code: str) -> str:
    """Remove Pydantic model classes accidentally included in route slices."""
    return re.sub(
        r"\nclass (?:CloseAuctionBody|PlaceBidBody|PostCommentBody|A2AMessageBody|"
        r"SubscribeTaskBody|RejectCompletionBody|ConfirmTaskBody|EscrowDisputeBody|"
        r"SubmitCompletionBody|PublishTaskBody|WorkflowPlanBody|BatchConfirmBody)\(BaseModel\):.*?"
        r"(?=\n(?:@router\.|def ))",
        "\n",
        code,
        flags=re.DOTALL,
    )


# --- skill_xp ---
skill_xp = rename_helpers(sl(428, 531))
(ROOT / "app/domain/skill_xp.py").write_text(
    '"""Skill XP helpers."""\nfrom __future__ import annotations\n\n'
    + "from datetime import datetime\nfrom typing import List, Optional\n\n"
    + "from sqlalchemy.orm import Session\n\n"
    + "from app.database.relational_db import Agent, PublishedSkill, Task\n\n"
    + skill_xp.replace("def _task_skills_for_xp", "def task_skills_for_xp")
    .replace("def _agent_skill_token", "def agent_skill_token")
    .replace("def _task_related_skill", "def task_related_skill")
    .replace("def _level_from_xp", "def level_from_xp")
    .replace("def _agent_skill_xp_map", "def agent_skill_xp_map")
    .replace("def _skill_decay_meta", "def skill_decay_meta")
    .replace("def _apply_skill_decay", "def apply_skill_decay"),
    encoding="utf-8",
)

# --- agent_helpers ---
agent_helpers = (
    sl(1182, 1186)  # CapabilityItem
    + sl(1189, 1201)  # RegisterAgentBody (skip duplicate comment)
    + sl(1204, 1228)
    + sl(1329, 1340)
    + sl(1441, 1445)
    + "class SendMessageBody(BaseModel):\n    content: str\n\n"
)
agent_helpers = agent_helpers.replace("def _ensure_agents_category_column", "def ensure_agents_category_column")
agent_helpers = agent_helpers.replace("_ensure_agents_category_column", "ensure_agents_category_column")
agent_helpers = agent_helpers.replace("def _norm_capabilities", "def norm_capabilities")
agent_helpers = agent_helpers.replace("def _published_skill_ids_by_token", "def published_skill_ids_by_token")
agent_helpers = agent_helpers.replace("def _get_my_agent", "def get_my_agent")
(ROOT / "app/domain/agent_helpers.py").write_text(
    '"""Agent domain helpers."""\nfrom __future__ import annotations\n\n'
    + "from typing import Any, List, Optional\n\n"
    + "from pydantic import BaseModel\n"
    + "from sqlalchemy import text\nfrom sqlalchemy.orm import Session\n\n"
    + "from app.database.relational_db import Agent, PublishedSkill, engine as db_engine\n\n"
    + agent_helpers,
    encoding="utf-8",
)

# --- task models ---
task_models = (
    sl(1673, 1713)
    + sl(1758, 1759)  # SubscribeTaskBody
    + sl(1762, 1763)  # RejectCompletionBody - partial, get full below
)
# Fix task_models to include all bodies
task_models = (
    sl(1673, 1713)
    + sl(1758, 1778)
    + sl(3251, 3255)
    + sl(3526, 3527)
    + sl(4509, 4512)
    + sl(4575, 4578)
    + sl(825, 827)
    + sl(4168, 4169)
)
(ROOT / "app/domain/task_models.py").write_text(
    '"""Task request/response models."""\nfrom __future__ import annotations\n\n'
    + "from typing import List, Optional\n\nfrom pydantic import BaseModel\n\n"
    + task_models,
    encoding="utf-8",
)

# --- task_helpers (functions only) ---
task_helpers_body = rename_helpers(
    sl(1575, 1667)  # constants through task_payment_breakdown
    + sl(1716, 1756)  # push_task_to_discord only
    + sl(1789, 2024)  # normalize through maybe_auto_confirm
    + sl(2027, 2084)
    + sl(2364, 2420)
    + sl(3258, 3287)
    + sl(3440, 3491)
    + sl(4563, 4571)
    + sl(4827, 4835)
)
task_helpers_body = task_helpers_body.replace(
    "from app.domain.agent_helpers import ensure_agents_category_column\n\n",
    "",
)
(ROOT / "app/domain/task_helpers.py").write_text(
    '"""Task domain helpers and constants."""\nfrom __future__ import annotations\n\n'
    + "import os\nimport time\nfrom datetime import datetime, timedelta\n"
    + "from typing import Any, Dict, List, Optional, Tuple\n\n"
    + "import httpx\nfrom fastapi import HTTPException\n"
    + "from sqlalchemy.orm import Session\nfrom sqlalchemy.orm.attributes import flag_modified\n\n"
    + "from app.database.relational_db import (\n"
    + "    Agent, CreditTransaction, PlatformClearingAccount, PlatformCommissionRecord,\n"
    + "    Task, TaskBid, TaskComment, User,\n)\n"
    + "from app.domain.agent_helpers import ensure_agents_category_column\n"
    + "from app.domain.skill_xp import task_related_skill\n"
    + "from app.services import reverse_auction as _ra\n"
    + "from app.services.escrow_tasks import apply_escrow_milestone_confirm, get_escrow\n"
    + "from app.services.task_timeline import append_timeline_event as _append_timeline_event\n"
    + "from app.utils.datetime_iso import iso_utc\n\n"
    + "CLAWJOB_SYSTEM_USERNAME = \"clawjob_system\"\n"
    + "CLAWJOB_SYSTEM_AGENT_NAME = \"clawjob-agent\"\n"
    + "FRONTEND_URL = os.getenv(\"FRONTEND_URL\", \"http://localhost:3000\").rstrip(\"/\")\n\n"
    + task_helpers_body,
    encoding="utf-8",
)

ROUTER_HEADER = '''"""Extracted from main.py — API paths unchanged."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.systems import runtime_guard, task_system
from app.database.relational_db import (
    Agent, CreditTransaction, ExecutionRun, ExecutionStep, Task, TaskBid,
    TaskComment, TaskSubscription, User, get_db,
)
from app.domain.agent_helpers import ensure_agents_category_column, get_my_agent, norm_capabilities, published_skill_ids_by_token, RegisterAgentBody, SendMessageBody
from app.domain.skill_xp import agent_skill_xp_map, level_from_xp
from app.domain.task_helpers import (
    CLAWJOB_SYSTEM_AGENT_NAME, CLAWJOB_SYSTEM_USERNAME, FRONTEND_URL,
    a2a_can_access_task, append_task_status_update_comment, award_bid_impl,
    can_view_task_runs, compute_publish_fee, get_or_create_clawjob_system_agent,
    intent_rate_check, maybe_auto_confirm, maybe_settle_skill_revenue, owner_display_name,
    pay_task_reward, push_task_to_discord, require_auction_task, serialize_auction_state,
    task_extra, task_is_public_listing, task_is_visible_to, task_payment_breakdown,
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

'''


def extract_routes(ranges: list[tuple[int, int]]) -> str:
    code = ""
    for s, e in ranges:
        code += sl(s, e).replace("@app.", "@router.")
    code = rename_helpers(code)
    return strip_embedded_models(code)


# tasks router
task_ranges = [
    (2087, 2128), (2423, 3171), (3289, 3817), (3872, 4233),
    (4236, 4322), (4325, 4363), (4515, 4560), (4581, 4683), (4686, 4925),
    (2463, 2679),
]
(ROOT / "app/routers/tasks.py").write_text(ROUTER_HEADER + extract_routes(task_ranges), encoding="utf-8")

# agents router - fix list_my_agents internal refs
agents_header = ROUTER_HEADER.replace('router = APIRouter()', 'router = APIRouter(tags=["agents"])')
agents_header = agents_header.replace("from app.domain.agent_helpers import ensure_agents_category_column, get_my_agent", "from app.domain.agent_helpers import ensure_agents_category_column, get_my_agent, published_skill_ids_by_token, RegisterAgentBody, SendMessageBody, norm_capabilities")
agent_ranges = [(1231, 1572), (2131, 2361)]
agents_code = extract_routes(agent_ranges)
agents_code = agents_code.replace("_published_skill_ids_by_token", "published_skill_ids_by_token")
agents_code = agents_code.replace("_norm_capabilities", "norm_capabilities")
agents_code = agents_code.replace("_get_my_agent", "get_my_agent")
(ROOT / "app/routers/agents.py").write_text(agents_header + agents_code, encoding="utf-8")

# messages
msg_header = '''"""Internal messaging APIs."""
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

router = APIRouter(tags=["messages"])


class InternalMessageBody(BaseModel):
    recipient_user_id: Optional[int] = None
    recipient_username: str = ""
    title: str
    content: str
    related_task_id: Optional[int] = None

'''
msg_code = sl(4366, 4506).replace("@app.", "@router.").replace("SendMessageBody", "InternalMessageBody")
(ROOT / "app/routers/messages.py").write_text(msg_header + msg_code, encoding="utf-8")

print("Rebuild complete")
