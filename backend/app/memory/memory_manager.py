"""Memory manager stub for agent memory."""
from typing import Dict, List, Any


class MemoryManager:
    def __init__(self, vector_db, relational_db):
        self.vector_db = vector_db
        self.relational_db = relational_db

    async def initialize(self):
        pass

    async def get_agent_memory(self, agent_id: str, query: str = None) -> List[Dict[str, Any]]:
        return []
