#!/usr/bin/env python3
"""One-shot refactor: extract tasks/agents/messages routers from main.py."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app" / "main.py"
lines = MAIN.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(start: int, end: int) -> str:
    """1-based inclusive line numbers."""
    return "".join(lines[start - 1 : end])


def transform_route_block(code: str) -> str:
    return code.replace("@app.", "@router.")


# --- task_domain.py: helpers + models used by tasks router and main activity/stats ---
TASK_DOMAIN_START = 1575  # VERIFICATION_HOURS_DEFAULT
TASK_DOMAIN_END = 2027    # end of _task_extra
TASK_DOMAIN_EXTRA = [
    (2364, 2420),   # visibility helpers + intent rate
    (3251, 3256),   # PlaceBidBody
    (3258, 3491),   # auction helpers
    (4563, 4571),   # _a2a_can_access_task
    (4827, 4835),   # _can_view_task_runs
]
TASK_MODELS = [
    (1673, 1713),   # EscrowMilestoneIn, AuctionConfigIn, PublishTaskBody
    (1766, 1786),   # EscrowDisputeBody, SubmitCompletionBody, ConfirmTaskBody (not SendMessageBody)
    (3526, 3527),   # CloseAuctionBody
    (4509, 4512),   # PostCommentBody
    (4575, 4578),   # A2AMessageBody
    (825, 827),     # WorkflowPlanBody
]

task_domain_parts = [slice_lines(TASK_DOMAIN_START, TASK_DOMAIN_END)]
for s, e in TASK_MODELS:
    task_domain_parts.append(slice_lines(s, e))
for s, e in TASK_DOMAIN_EXTRA:
    task_domain_parts.append(slice_lines(s, e))

task_domain_header = '''"""
Task domain helpers, constants, and request models shared by routers and main.
"""
from __future__ import annotations

import copy
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.relational_db import (
    Agent,
    CreditTransaction,
    PlatformClearingAccount,
    PlatformCommissionRecord,
    Task,
    TaskBid,
    TaskComment,
    User,
    engine as db_engine,
)
from app.services import reverse_auction as _ra
from app.services.escrow_tasks import get_escrow
from app.services.task_timeline import append_timeline_event as _append_timeline_event
from app.utils.datetime_iso import iso_utc
from app.domain.agent_helpers import ensure_agents_category_column

'''

task_domain_body = "".join(task_domain_parts)
# Fix references to private helpers moved to agent_helpers
task_domain_body = task_domain_body.replace("_ensure_agents_category_column()", "ensure_agents_category_column()")
task_domain_body = task_domain_body.replace("_ensure_agents_category_column", "ensure_agents_category_column")
task_domain_body = task_domain_body.replace("_CLAWJOB_SYSTEM_USERNAME", "CLAWJOB_SYSTEM_USERNAME")
task_domain_body = task_domain_body.replace("_INTENT_RATE_LIMIT_WINDOW", "INTENT_RATE_LIMIT_WINDOW")
task_domain_body = task_domain_body.replace("_INTENT_RATE_LIMIT_MAX", "INTENT_RATE_LIMIT_MAX")
task_domain_body = task_domain_body.replace("_intent_rate_bucket", "intent_rate_bucket")

(ROOT / "app" / "domain").mkdir(exist_ok=True)
(ROOT / "app" / "domain" / "__init__.py").write_text("", encoding="utf-8")

# agent_helpers.py
agent_helpers_code = slice_lines(1204, 1445)
agent_helpers_code = agent_helpers_code.replace("def _ensure_agents_category_column", "def ensure_agents_category_column")
agent_helpers_code = agent_helpers_code.replace("_ensure_agents_category_column", "ensure_agents_category_column")
agent_helpers_header = '''"""
Agent domain helpers shared by agents router and task domain.
"""
from __future__ import annotations

from typing import Any, List, Optional

import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database.relational_db import (
    Agent,
    PublishedAgentTemplate,
    PublishedSkill,
    Task,
    SystemLog,
    User,
    engine as db_engine,
    get_db,
)
from app.services.preflight import enforce_preflight
from app.utils.datetime_iso import iso_utc

'''
(ROOT / "app" / "domain" / "agent_helpers.py").write_text(
    agent_helpers_header + agent_helpers_code, encoding="utf-8"
)

# constants in task_domain - extract CLAWJOB_SYSTEM from 1843-1844, 2388
constants_snip = slice_lines(1843, 1844) + slice_lines(2388, 2407)
task_domain_body = constants_snip + "\n\n" + task_domain_body

(ROOT / "app" / "domain" / "task_helpers.py").write_text(
    task_domain_header + task_domain_body, encoding="utf-8"
)

# --- systems.py ---
systems_code = '''"""
Shared runtime system instances (DB layers, agent subsystems).
"""
import os

from app.database.vector_db import VectorDB
from app.database.relational_db import RelationalDB
from app.database.cache_db import CacheDB
from app.agents.agent_manager import AgentManager
from app.agents.task_system import TaskSystem
from app.agents.memory_system import MemorySystem
from app.agents.tool_system import ToolSystem
from app.services.runtime_guard import RuntimeCircuitGuard

vector_db = VectorDB()
relational_db = RelationalDB()
cache_db = CacheDB()

agent_manager = AgentManager(vector_db, relational_db, cache_db)
task_system = TaskSystem(vector_db, relational_db, cache_db)
memory_system = MemorySystem(vector_db, cache_db)
tool_system = ToolSystem(relational_db, cache_db)
runtime_guard = RuntimeCircuitGuard(
    threshold=int(os.getenv("WEBHOOK_CB_THRESHOLD", "3") or "3"),
    open_seconds=int(os.getenv("WEBHOOK_CB_OPEN_SECONDS", "60") or "60"),
)
'''
(ROOT / "app" / "core").mkdir(exist_ok=True)
(ROOT / "app" / "core" / "__init__.py").write_text("", encoding="utf-8")
(ROOT / "app" / "core" / "systems.py").write_text(systems_code, encoding="utf-8")

COMMON_ROUTER_IMPORTS = '''"""
Extracted from main.py — keep API paths unchanged.
"""
from __future__ import annotations

import copy
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.systems import runtime_guard, task_system
from app.database.relational_db import (
    Agent,
    CreditTransaction,
    ExecutionRun,
    ExecutionStep,
    InternalMessage,
    PlatformClearingAccount,
    PlatformCommissionRecord,
    Task,
    TaskBid,
    TaskComment,
    TaskSubscription,
    User,
    get_db,
)
from app.domain.agent_helpers import (
    RegisterAgentBody,
    SendMessageBody as AgentSendMessageBody,
    ensure_agents_category_column,
    get_my_agent,
    norm_capabilities,
    published_skill_ids_by_token,
)
from app.domain.task_helpers import (
    CLAWJOB_SYSTEM_AGENT_NAME,
    CLAWJOB_SYSTEM_USERNAME,
    A2AMessageBody,
    AuctionConfigIn,
    CloseAuctionBody,
    ConfirmTaskBody,
    EscrowDisputeBody,
    EscrowMilestoneIn,
    PlaceBidBody,
    PostCommentBody,
    PublishTaskBody,
    SubmitCompletionBody,
    WorkflowPlanBody,
    FRONTEND_URL,
    a2a_can_access_task,
    append_task_status_update_comment,
    award_bid_impl,
    can_view_task_runs,
    compute_publish_fee,
    get_or_create_clearing_account,
    get_or_create_clawjob_system_agent,
    intent_rate_check,
    maybe_auto_confirm,
    maybe_settle_skill_revenue,
    owner_display_name,
    pay_task_reward,
    push_task_to_discord,
    require_auction_task,
    serialize_auction_state,
    task_extra,
    task_is_public_listing,
    task_is_visible_to,
    task_payment_breakdown,
    task_verification_hours,
    validate_verification_submission,
)
from app.security import get_current_user, get_current_user_optional
from app.services import execution_sandbox as _sandbox
from app.services import reverse_auction as _ra
from app.services import safety_pipeline as _safety
from app.services import step_replay as _replay
from app.services.escrow_tasks import (
    apply_escrow_milestone_confirm,
    build_escrow_plan,
    get_escrow,
    save_escrow_to_task,
)
from app.services.preflight import enforce_preflight, run_preflight
from app.services.task_timeline import append_timeline_event as _append_timeline_event
from app.services.workflow_dag import predecessors, validate_workflow_dag
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["tasks"])

'''

# Rename helpers in task_helpers for public import (script post-process)
th_path = ROOT / "app" / "domain" / "task_helpers.py"
th_text = th_path.read_text(encoding="utf-8")
renames = [
    ("_FRONTEND_URL", "FRONTEND_URL"),
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
    ("def _compute_publish_fee", "def compute_publish_fee"),
    ("def _task_verification_hours", "def task_verification_hours"),
    ("def _task_payment_breakdown", "def task_payment_breakdown"),
    ("_intent_rate_bucket", "intent_rate_bucket"),
    ("_INTENT_RATE_LIMIT_WINDOW", "INTENT_RATE_LIMIT_WINDOW"),
    ("_INTENT_RATE_LIMIT_MAX", "INTENT_RATE_LIMIT_MAX"),
]
for old, new in renames:
    th_text = th_text.replace(old, new)
th_path.write_text(th_text, encoding="utf-8")

# Rename agent helpers for public export
ah_path = ROOT / "app" / "domain" / "agent_helpers.py"
ah_text = ah_path.read_text(encoding="utf-8")
# Extract RegisterAgentBody - it's before ensure function in original
# Add explicit exports at end
agent_renames = [
    ("class RegisterAgentBody", "class RegisterAgentBody"),
    ("def _norm_capabilities", "def norm_capabilities"),
    ("def _published_skill_ids_by_token", "def published_skill_ids_by_token"),
    ("def _get_my_agent", "def get_my_agent"),
    ("class SendMessageBody", "class SendMessageBody"),
]
for old, new in agent_renames:
    ah_text = ah_text.replace(old, new)
# Remove route handlers from agent_helpers - they shouldn't be there
# The slice 1204-1445 includes routes - need to fix
# Re-slice: only helpers 1204-1228, 1329-1445, models 1189-1201
agent_helpers_only = (
    slice_lines(1189, 1228)
    + slice_lines(1329, 1445)
)
agent_helpers_only = agent_helpers_only.replace("def _ensure_agents_category_column", "def ensure_agents_category_column")
agent_helpers_only = agent_helpers_only.replace("_ensure_agents_category_column", "ensure_agents_category_column")
agent_helpers_only = agent_helpers_only.replace("def _norm_capabilities", "def norm_capabilities")
agent_helpers_only = agent_helpers_only.replace("def _published_skill_ids_by_token", "def published_skill_ids_by_token")
agent_helpers_only = agent_helpers_only.replace("def _get_my_agent", "def get_my_agent")
ah_path.write_text(agent_helpers_header + agent_helpers_only, encoding="utf-8")

# --- tasks router: line ranges for endpoints ---
TASK_ROUTE_RANGES = [
    (2423, 2906),   # draft-from-intent through publish task
    (2909, 3171),   # workflows + cancel
    (3289, 3817),   # bids through submit-completion
    (3872, 4233),   # verification-chain through batch-confirm
    (4236, 4322),   # get task + list comments
    (4325, 4363),   # forum recent-posts
    (4515, 4560),   # post comment
    (4581, 4683),   # a2a
    (4686, 4925),   # execute + runs
]
tasks_routes = ""
for s, e in TASK_ROUTE_RANGES:
    tasks_routes += transform_route_block(slice_lines(s, e))

# Fix helper references in tasks routes
helper_map = [
    ("_maybe_auto_confirm", "maybe_auto_confirm"),
    ("_task_extra", "task_extra"),
    ("_task_is_visible_to", "task_is_visible_to"),
    ("_task_is_public_listing", "task_is_public_listing"),
    ("_CLAWJOB_SYSTEM_USERNAME", "CLAWJOB_SYSTEM_USERNAME"),
    ("_intent_rate_check", "intent_rate_check"),
    ("_compute_publish_fee", "compute_publish_fee"),
    ("_push_task_to_discord", "push_task_to_discord"),
    ("_FRONTEND_URL", "FRONTEND_URL"),
    ("_get_or_create_clawjob_system_agent", "get_or_create_clawjob_system_agent"),
    ("_pay_task_reward", "pay_task_reward"),
    ("_maybe_settle_skill_revenue", "maybe_settle_skill_revenue"),
    ("_require_auction_task", "require_auction_task"),
    ("_serialize_auction_state", "serialize_auction_state"),
    ("_award_bid_impl", "award_bid_impl"),
    ("_task_verification_hours", "task_verification_hours"),
    ("_validate_verification_submission", "validate_verification_submission"),
    ("_append_task_status_update_comment", "append_task_status_update_comment"),
    ("_task_payment_breakdown", "task_payment_breakdown"),
    ("_a2a_can_access_task", "a2a_can_access_task"),
    ("_can_view_task_runs", "can_view_task_runs"),
    ("_get_or_create_clearing_account", "get_or_create_clearing_account"),
]
for old, new in helper_map:
    tasks_routes = tasks_routes.replace(old, new)

(ROOT / "app" / "routers" / "tasks.py").write_text(
    COMMON_ROUTER_IMPORTS + tasks_routes, encoding="utf-8"
)

# Also add list endpoints that were before publish (2087-2128 is agents/{id}/tasks - goes to agents)
# tasks/mine, created-by-me, list, estimate - lines 2087-2128 agents tasks -> agents
# 2463-2632 list tasks
extra_task_ranges = [(2087, 2128), (2463, 2680)]  # mine is 2087? check - 2087 is tasks/mine
# 2087 = tasks/mine, 2131 = agents/{id}/tasks
TASK_ROUTE_RANGES2 = [
    (2087, 2128),   # tasks/mine
    (2463, 2632),   # estimate + list + created-by-me start
]
# 2635-2680 created-by-me continues, 2680 post tasks already in first block
tasks_routes2 = transform_route_block(slice_lines(2087, 2128) + slice_lines(2463, 2679))
for old, new in helper_map:
    tasks_routes2 = tasks_routes2.replace(old, new)

tasks_content = (ROOT / "app" / "routers" / "tasks.py").read_text(encoding="utf-8")
# Insert after router = line
insert_at = tasks_content.find("router = APIRouter")
insert_at = tasks_content.find("\n", insert_at) + 1
tasks_content = tasks_content[:insert_at] + "\n" + tasks_routes2 + tasks_content[insert_at:]
(ROOT / "app" / "routers" / "tasks.py").write_text(tasks_content, encoding="utf-8")

# --- agents router ---
AGENTS_IMPORTS = '''"""
Agent registration and management APIs (extracted from main.py).
"""
from __future__ import annotations

import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database.relational_db import (
    Agent,
    PublishedAgentTemplate,
    PublishedSkill,
    Task,
    User,
    get_db,
)
from app.domain.agent_helpers import (
    RegisterAgentBody,
    SendMessageBody,
    ensure_agents_category_column,
    get_my_agent,
    norm_capabilities,
    published_skill_ids_by_token,
)
from app.domain.task_helpers import (
    CLAWJOB_SYSTEM_USERNAME,
    maybe_auto_confirm,
    owner_display_name,
    task_extra,
)
from app.security import get_current_user
from app.services.preflight import enforce_preflight
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["agents"])

'''

agent_route_ranges = [
    (1231, 1497),   # register through send-message
    (1500, 1572),   # candidates
    (2131, 2361),   # agent tasks, reputation, cases, profile, task-radar
]
agents_routes = ""
for s, e in agent_route_ranges:
    agents_routes += transform_route_block(slice_lines(s, e))

agent_helper_map = [
    ("_ensure_agents_category_column", "ensure_agents_category_column"),
    ("_norm_capabilities", "norm_capabilities"),
    ("_published_skill_ids_by_token", "published_skill_ids_by_token"),
    ("_get_my_agent", "get_my_agent"),
    ("_maybe_auto_confirm", "maybe_auto_confirm"),
    ("_task_extra", "task_extra"),
    ("_owner_display_name", "owner_display_name"),
    ("_agent_skill_xp_map", "_agent_skill_xp_map"),  # stays in main for now - need import
    ("_level_from_xp", "_level_from_xp"),
]
# candidates uses _agent_skill_xp_map and _level_from_xp from main - import from main skill helpers
# Add import for skill xp from a small module - they're in main lines 428-524
# Include in agents router by importing from app.domain.skill_xp
skill_xp_code = slice_lines(428, 531)
skill_xp_header = '''"""Skill XP helpers (from main.py)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.database.relational_db import Agent, PublishedSkill, Task

'''
(ROOT / "app" / "domain" / "skill_xp.py").write_text(skill_xp_header + skill_xp_code, encoding="utf-8")
agents_routes = agents_routes.replace("_agent_skill_xp_map", "agent_skill_xp_map")
agents_routes = agents_routes.replace("_level_from_xp", "level_from_xp")
sx_path = ROOT / "app" / "domain" / "skill_xp.py"
sx_text = sx_path.read_text(encoding="utf-8").replace("def _agent_skill_xp_map", "def agent_skill_xp_map").replace("def _level_from_xp", "def level_from_xp").replace("def _task_skills_for_xp", "def task_skills_for_xp").replace("def _agent_skill_token", "def agent_skill_token").replace("def _task_related_skill", "def task_related_skill").replace("def _skill_decay_meta", "def skill_decay_meta").replace("def _apply_skill_decay", "def apply_skill_decay")
sx_path.write_text(sx_text, encoding="utf-8")

AGENTS_IMPORTS = AGENTS_IMPORTS.replace(
    "from app.utils.datetime_iso import iso_utc\n",
    "from app.domain.skill_xp import agent_skill_xp_map, level_from_xp\nfrom app.utils.datetime_iso import iso_utc\n",
)

for old, new in agent_helper_map:
    if old.startswith("_agent") or old.startswith("_level"):
        continue
    agents_routes = agents_routes.replace(old, new)

(ROOT / "app" / "routers" / "agents.py").write_text(AGENTS_IMPORTS + agents_routes, encoding="utf-8")

# --- messages router ---
MESSAGES_IMPORTS = '''"""
Internal messaging APIs (extracted from main.py).
"""
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

messages_routes = transform_route_block(slice_lines(4366, 4506))
messages_routes = messages_routes.replace("SendMessageBody", "InternalMessageBody")
messages_routes = messages_routes.replace("body: SendMessageBody", "body: InternalMessageBody")

(ROOT / "app" / "routers" / "messages.py").write_text(MESSAGES_IMPORTS + messages_routes, encoding="utf-8")

print("Created routers and domain modules. Now patch main.py manually or run patch_main.py")
