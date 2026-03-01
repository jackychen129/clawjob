"""
Agent Manager for Agentic Applications
Manages intelligent agents with memory, tools, and reasoning capabilities.
"""
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import asyncio
import json
from datetime import datetime

from app.database.vector_db import VectorDB
from app.database.relational_db import RelationalDB  
from app.database.cache_db import CacheDB
from app.models.agent import Agent, AgentConfig
from app.tools.tool_registry import ToolRegistry
from app.memory.memory_manager import MemoryManager


@dataclass
class AgentTask:
    """Represents a task assigned to an agent."""
    task_id: str
    description: str
    agent_id: str
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = None
    completed_at: datetime = None
    result: Any = None
    error: str = None


class AgentManager:
    """Manages intelligent agents with agentic capabilities."""
    
    def __init__(self, vector_db=None, relational_db=None, cache_db=None):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.vector_db = vector_db or VectorDB()
        self.relational_db = relational_db or RelationalDB()
        self.cache_db = cache_db or CacheDB()
        self.tool_registry = ToolRegistry()
        self.memory_manager = MemoryManager(self.vector_db, self.relational_db)
        
    async def initialize(self):
        """Initialize all database connections and components."""
        await self.vector_db.initialize()
        await self.relational_db.initialize() 
        await self.cache_db.initialize()
        await self.tool_registry.initialize()
        await self.memory_manager.initialize()
        
    async def create_agent(self, config, current_user: dict = None) -> Agent:
        """Create a new intelligent agent with specified configuration."""
        if isinstance(config, dict):
            config = AgentConfig(**config)
        import uuid
        agent = Agent(
            id=str(uuid.uuid4()),
            name=config.name,
            description=config.description,
            capabilities=getattr(config, "capabilities", []) or [],
            config=getattr(config, "config", {}) or {},
        )
        agent.set_databases(
            vector_db=self.vector_db,
            relational_db=self.relational_db, 
            cache_db=self.cache_db
        )
        agent.set_tool_registry(self.tool_registry)
        agent.set_memory_manager(self.memory_manager)
        
        self.agents[agent.id] = agent
        return agent
        
    async def assign_task(self, agent_id: str, task_description: str) -> str:
        """Assign a task to an agent and return task ID."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        task_id = f"task_{datetime.now().timestamp()}"
        task = AgentTask(
            task_id=task_id,
            description=task_description,
            agent_id=agent_id,
            created_at=datetime.now()
        )
        self.tasks[task_id] = task
        
        # Start task execution
        asyncio.create_task(self._execute_task(task))
        return task_id
        
    async def _execute_task(self, task: AgentTask):
        """Execute a task assigned to an agent."""
        try:
            task.status = "running"
            agent = self.agents[task.agent_id]
            
            # Execute the task using the agent's reasoning capabilities
            result = await agent.execute_task(task.description)
            
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()
            
            # Store task result in databases
            await self._store_task_result(task)
            
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            task.completed_at = datetime.now()
            print(f"Task {task.task_id} failed: {e}")
            
    async def _store_task_result(self, task: AgentTask):
        """Store task result in appropriate databases."""
        # Store in relational DB for structured querying
        await self.relational_db.store_task_result(task)
        
        # Store in vector DB for semantic search
        await self.vector_db.store_task_embedding(
            task.task_id,
            task.description,
            task.result
        )
        
        # Cache recent results
        await self.cache_db.set(f"task:{task.task_id}", task.__dict__)
        
    async def query_similar_tasks(self, query: str, limit: int = 5) -> List[Dict]:
        """Query similar tasks using vector similarity search."""
        similar_tasks = await self.vector_db.similarity_search(query, limit)
        return similar_tasks
        
    async def get_agent(self, agent_id: str, current_user: dict = None) -> Optional[Agent]:
        """Get agent by id."""
        return self.agents.get(agent_id)

    async def list_agents(self, current_user: dict = None) -> List[Agent]:
        """List all agents."""
        return list(self.agents.values())

    async def delete_agent(self, agent_id: str, current_user: dict = None) -> bool:
        """Delete an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    async def get_agent_memory(self, agent_id: str, query: str = None) -> List[Dict]:
        """Get agent's memory, optionally filtered by query."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        return await self.memory_manager.get_agent_memory(agent_id, query)
        
    async def register_tool(self, tool_name: str, tool_func: Callable, description: str):
        """Register a new tool that agents can use."""
        await self.tool_registry.register_tool(tool_name, tool_func, description)
        
    async def shutdown(self):
        """Shutdown all database connections and components."""
        await self.vector_db.close()
        await self.relational_db.close()
        await self.cache_db.close()