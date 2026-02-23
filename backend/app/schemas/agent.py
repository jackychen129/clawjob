"""
Agent schemas for Agent Arena
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

class AgentUpdate(BaseModel):
    """Schema for updating agent configuration"""
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    
class AgentSelfIterationConfig(BaseModel):
    """Configuration for agent self-iteration capabilities"""
    enabled: bool = True
    iteration_frequency: int = 3600  # seconds
    performance_threshold: float = 0.8
    learning_rate: float = 0.1
    max_iterations: int = 100
    
class AgentPerformanceMetrics(BaseModel):
    """Metrics for agent performance tracking"""
    task_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    response_time_avg: float = Field(default=0.0, ge=0.0)
    resource_usage: Dict[str, float] = Field(default_factory=dict)
    iteration_count: int = Field(default=0, ge=0)
    last_iteration: Optional[datetime] = None