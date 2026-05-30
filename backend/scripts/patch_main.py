#!/usr/bin/env python3
"""Patch main.py: wire routers, use core.systems, remove extracted code."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "app" / "main.py"
lines = MAIN_PATH.read_text(encoding="utf-8").splitlines(keepends=True)


def delete_ranges(ranges: list[tuple[int, int]]) -> None:
    """Delete 1-based inclusive line ranges (process high to low)."""
    for start, end in sorted(ranges, reverse=True):
        del lines[start - 1 : end]


# Ranges to remove (extracted to routers/domain). Verified against original main.py.
DELETE = [
    (428, 531),    # skill xp helpers -> domain/skill_xp.py
    (1182, 1572),  # agents register..candidates
    (1575, 4925),  # task helpers + task/agent/message/a2a routes through runs/export
]

delete_ranges(DELETE)

text = "".join(lines)

# Replace inline system init with core.systems import
old_init = """# Initialize database systems
vector_db = VectorDB()
relational_db = RelationalDB()
cache_db = CacheDB()

# Initialize agent systems
agent_manager = AgentManager(vector_db, relational_db, cache_db)
task_system = TaskSystem(vector_db, relational_db, cache_db)
memory_system = MemorySystem(vector_db, cache_db)
tool_system = ToolSystem(relational_db, cache_db)
runtime_guard = RuntimeCircuitGuard(
    threshold=int(os.getenv("WEBHOOK_CB_THRESHOLD", "3") or "3"),
    open_seconds=int(os.getenv("WEBHOOK_CB_OPEN_SECONDS", "60") or "60"),
)"""

new_init = """from app.core.systems import (
    agent_manager,
    cache_db,
    memory_system,
    relational_db,
    runtime_guard,
    task_system,
    tool_system,
    vector_db,
)"""

if old_init not in text:
    raise SystemExit("Could not find system init block in main.py")
text = text.replace(old_init, new_init)

# Add domain imports after security imports
domain_imports = """
from app.domain.skill_xp import (
    agent_skill_xp_map,
    apply_skill_decay,
    level_from_xp,
    skill_decay_meta,
    task_skills_for_xp,
)
from app.domain.task_helpers import (
    CLAWJOB_SYSTEM_USERNAME,
    get_or_create_clearing_account,
    task_is_public_listing,
)
"""
marker = "from app.routers import community as community_router\n"
if marker not in text:
    raise SystemExit("community router import marker not found")
text = text.replace(marker, marker + domain_imports)

# Include new routers
router_block = """app.include_router(community_router.router)
from app.routers import tasks as tasks_router
from app.routers import agents as agents_router
from app.routers import messages as messages_router

app.include_router(tasks_router.router)
app.include_router(agents_router.router)
app.include_router(messages_router.router)
"""
old_router = "app.include_router(community_router.router)\n"
if old_router not in text:
    raise SystemExit("community include_router not found")
text = text.replace(old_router, router_block)

# Fix activity/stats helper references
replacements = [
    ("_CLAWJOB_SYSTEM_USERNAME", "CLAWJOB_SYSTEM_USERNAME"),
    ("_task_is_public_listing", "task_is_public_listing"),
    ("_task_skills_for_xp", "task_skills_for_xp"),
    ("_level_from_xp", "level_from_xp"),
    ("_agent_skill_xp_map", "agent_skill_xp_map"),
    ("_skill_decay_meta", "skill_decay_meta"),
    ("_apply_skill_decay", "apply_skill_decay"),
    ("_get_or_create_clearing_account", "get_or_create_clearing_account"),
    ("_activity_agent_is_internal", "_activity_agent_is_internal"),  # stays local
]
for old, new in replacements:
    if old != new:
        text = text.replace(old, new)

# Remove unused heavy imports if still present (optional cleanup)
text = text.replace(
    "from app.agents.task_system import TaskSystem\n", ""
)
text = text.replace(
    "from app.agents.memory_system import MemorySystem\n", ""
)
text = text.replace(
    "from app.agents.tool_system import ToolSystem\n", ""
)
text = text.replace(
    "from app.services.runtime_guard import RuntimeCircuitGuard\n", ""
)

MAIN_PATH.write_text(text, encoding="utf-8")
print(f"Patched main.py -> {len(text.splitlines())} lines")
