"""
Agent data models for Agent Arena
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AgentConfig(BaseModel):
    """Configuration for creating an agent."""
    name: str = ""
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentMemory(BaseModel):
    """Agent memory record."""
    id: str = ""
    agent_id: str = ""
    memory_type: str = ""
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentPerformanceMetrics(BaseModel):
    """Performance metrics for agent self-assessment"""
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    response_time_avg: float = Field(default=0.0, ge=0.0)
    task_completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_efficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    collaboration_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
class Agent(BaseModel):
    """Core agent model"""
    id: str = ""
    name: str = ""
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    performance_metrics: AgentPerformanceMetrics = Field(default_factory=AgentPerformanceMetrics)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    config: Dict[str, Any] = Field(default_factory=dict)

    def set_databases(self, vector_db=None, relational_db=None, cache_db=None):
        pass

    def set_tool_registry(self, tool_registry):
        pass

    def set_memory_manager(self, memory_manager):
        pass

    async def execute_task(self, description: str):
        return {"status": "ok", "message": "Task execution not implemented"}