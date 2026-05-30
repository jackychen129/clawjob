"""
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
