"""
Agent Task System for Agentic Applications
Handles task creation, assignment, execution, and monitoring for AI agents.
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import asyncio
import json
import logging
from enum import Enum

from app.database.vector_db import VectorDB
from app.database.relational_db import RelationalDB  
from app.database.cache_db import CacheDB
from app.agents.agent_manager import AgentManager

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AgentTask:
    """Represents a task that can be executed by an AI agent."""
    
    def __init__(
        self,
        task_id: str,
        description: str,
        agent_id: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: int = 300,  # seconds
        dependencies: List[str] = None,
        context: Dict[str, Any] = None,
        tools: List[str] = None
    ):
        self.task_id = task_id
        self.description = description
        self.agent_id = agent_id
        self.priority = priority
        self.timeout = timeout
        self.dependencies = dependencies or []
        self.context = context or {}
        self.tools = tools or []
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for storage."""
        return {
            'task_id': self.task_id,
            'description': self.description,
            'agent_id': self.agent_id,
            'priority': self.priority.value,
            'timeout': self.timeout,
            'dependencies': self.dependencies,
            'context': self.context,
            'tools': self.tools,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': self.error
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentTask':
        """Create task from dictionary."""
        task = cls(
            task_id=data['task_id'],
            description=data['description'],
            agent_id=data['agent_id'],
            priority=TaskPriority(data['priority']),
            timeout=data['timeout'],
            dependencies=data['dependencies'],
            context=data['context'],
            tools=data['tools']
        )
        task.status = TaskStatus(data['status'])
        task.created_at = datetime.fromisoformat(data['created_at'])
        if data['started_at']:
            task.started_at = datetime.fromisoformat(data['started_at'])
        if data['completed_at']:
            task.completed_at = datetime.fromisoformat(data['completed_at'])
        task.result = data['result']
        task.error = data['error']
        return task

class TaskSystem:
    """Manages the lifecycle of agent tasks."""
    
    def __init__(self, vector_db=None, relational_db=None, cache_db=None):
        self.relational_db = relational_db or RelationalDB()
        self.vector_db = vector_db or VectorDB()
        self.cache_db = cache_db or CacheDB()
        self.agent_manager = AgentManager(self.vector_db, self.relational_db, self.cache_db)
        self.active_tasks: Dict[str, AgentTask] = {}
        self.task_queue: List[AgentTask] = []
        
    async def create_task(
        self,
        description: str,
        agent_id: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: int = 300,
        dependencies: List[str] = None,
        context: Dict[str, Any] = None,
        tools: List[str] = None
    ) -> str:
        """Create a new agent task."""
        from uuid import uuid4
        
        task_id = str(uuid4())
        task = AgentTask(
            task_id=task_id,
            description=description,
            agent_id=agent_id,
            priority=priority,
            timeout=timeout,
            dependencies=dependencies or [],
            context=context or {},
            tools=tools or []
        )
        
        # Store task in relational database
        await self.relational_db.store_task(task.to_dict())
        
        # Store task embedding in vector database for semantic search
        embedding = await self._generate_task_embedding(description)
        await self.vector_db.store_task_embedding(task_id, embedding, task.to_dict())
        
        # Add to cache for quick access
        await self.cache_db.set_task(task_id, task.to_dict())
        
        # Add to task queue
        self.task_queue.append(task)
        self.active_tasks[task_id] = task
        
        logger.info(f"Created task {task_id} for agent {agent_id}")
        return task_id
        
    async def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to a specific agent."""
        if task_id not in self.active_tasks:
            return False
            
        task = self.active_tasks[task_id]
        task.agent_id = agent_id
        
        # Update in all databases
        await self.relational_db.update_task(task_id, {'agent_id': agent_id})
        await self.cache_db.set_task(task_id, task.to_dict())
        
        logger.info(f"Assigned task {task_id} to agent {agent_id}")
        return True
        
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task using the assigned agent."""
        if task_id not in self.active_tasks:
            raise ValueError(f"Task {task_id} not found")
            
        task = self.active_tasks[task_id]
        
        # Check dependencies
        if not await self._check_dependencies(task):
            raise ValueError(f"Dependencies not satisfied for task {task_id}")
            
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        await self.relational_db.update_task(task_id, {
            'status': TaskStatus.RUNNING.value,
            'started_at': task.started_at.isoformat()
        })
        await self.cache_db.set_task(task_id, task.to_dict())
        
        try:
            # Get agent and execute task
            agent = await self.agent_manager.get_agent(task.agent_id)
            if not agent:
                raise ValueError(f"Agent {task.agent_id} not found")
                
            # Execute task with agent
            result = await self._execute_with_agent(agent, task)
            
            # Update task completion
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = result
            
            await self.relational_db.update_task(task_id, {
                'status': TaskStatus.COMPLETED.value,
                'completed_at': task.completed_at.isoformat(),
                'result': result
            })
            await self.cache_db.set_task(task_id, task.to_dict())
            
            # Store result in vector database for future reference
            result_embedding = await self._generate_result_embedding(str(result))
            await self.vector_db.store_result_embedding(task_id, result_embedding, result)
            
            logger.info(f"Completed task {task_id} with result: {result}")
            return result
            
        except Exception as e:
            # Handle task failure
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.error = str(e)
            
            await self.relational_db.update_task(task_id, {
                'status': TaskStatus.FAILED.value,
                'completed_at': task.completed_at.isoformat(),
                'error': str(e)
            })
            await self.cache_db.set_task(task_id, task.to_dict())
            
            logger.error(f"Failed task {task_id}: {e}")
            raise e
            
    async def query_similar_tasks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar tasks based on semantic similarity."""
        query_embedding = await self._generate_task_embedding(query)
        similar_tasks = await self.vector_db.search_similar_tasks(query_embedding, limit)
        return similar_tasks
        
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current status of a task."""
        # Try cache first
        cached_task = await self.cache_db.get_task(task_id)
        if cached_task:
            return cached_task
            
        # Fallback to relational database
        task_data = await self.relational_db.get_task(task_id)
        if task_data:
            await self.cache_db.set_task(task_id, task_data)
            return task_data
            
        raise ValueError(f"Task {task_id} not found")
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id not in self.active_tasks:
            return False
            
        task = self.active_tasks[task_id]
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
            
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        
        await self.relational_db.update_task(task_id, {
            'status': TaskStatus.CANCELLED.value,
            'completed_at': task.completed_at.isoformat()
        })
        await self.cache_db.set_task(task_id, task.to_dict())
        
        logger.info(f"Cancelled task {task_id}")
        return True
        
    async def _check_dependencies(self, task: AgentTask) -> bool:
        """Check if all task dependencies are completed."""
        for dep_id in task.dependencies:
            dep_status = await self.get_task_status(dep_id)
            if dep_status['status'] != TaskStatus.COMPLETED.value:
                return False
        return True
        
    async def _execute_with_agent(self, agent: Dict[str, Any], task: AgentTask) -> Any:
        """Execute task using the specified agent."""
        # This is a placeholder - actual implementation would call the agent's API
        # For now, we'll simulate agent execution
        
        # Simulate some processing time
        await asyncio.sleep(1)
        
        # Return mock result based on task description
        return {
            "task_id": task.task_id,
            "agent_id": task.agent_id,
            "result": f"Executed task: {task.description}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def _generate_task_embedding(self, text: str) -> List[float]:
        """Generate embedding for task text."""
        # Placeholder - in real implementation, this would use an embedding model
        # For now, return a mock embedding
        return [0.1, 0.2, 0.3, 0.4, 0.5]
        
    async def _generate_result_embedding(self, text: str) -> List[float]:
        """Generate embedding for task result."""
        # Placeholder - in real implementation, this would use an embedding model
        return [0.5, 0.4, 0.3, 0.2, 0.1]
        
    async def get_agent_tasks(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all tasks assigned to a specific agent."""
        return await self.relational_db.get_agent_tasks(agent_id, limit)
        
    async def get_task_metrics(self) -> Dict[str, Any]:
        """Get task execution metrics."""
        return await self.relational_db.get_task_metrics()