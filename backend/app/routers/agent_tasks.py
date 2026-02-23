"""
Agent Tasks API Router
Handles task creation, management, and execution for agentic applications.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from app.security import get_current_user
from app.agents.task_system import TaskSystem
from app.database.relational_db import get_db_session

router = APIRouter(prefix="/api/agents/tasks", tags=["agent-tasks"])

class TaskCreateRequest(BaseModel):
    """Request model for creating a new task."""
    title: str
    description: str
    agent_id: str
    priority: Optional[str] = "medium"
    deadline: Optional[str] = None
    tools: Optional[List[str]] = None
    context: Optional[dict] = None

class TaskUpdateRequest(BaseModel):
    """Request model for updating an existing task."""
    status: Optional[str] = None
    priority: Optional[str] = None
    result: Optional[str] = None
    metadata: Optional[dict] = None

class TaskResponse(BaseModel):
    """Response model for task information."""
    id: str
    title: str
    description: str
    agent_id: str
    status: str
    priority: str
    created_at: str
    updated_at: str
    deadline: Optional[str] = None
    result: Optional[str] = None
    metadata: dict

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_request: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
    db_session = Depends(get_db_session)
):
    """
    Create a new task for an agent.
    
    Args:
        task_request: Task creation request data
        current_user: Authenticated user information
        db_session: Database session
        
    Returns:
        Created task information
        
    Raises:
        HTTPException: If agent doesn't exist or task creation fails
    """
    try:
        task_system = TaskSystem(db_session)
        task = await task_system.create_task(
            title=task_request.title,
            description=task_request.description,
            agent_id=task_request.agent_id,
            user_id=current_user["id"],
            priority=task_request.priority,
            deadline=task_request.deadline,
            tools=task_request.tools,
            context=task_request.context
        )
        
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            agent_id=task.agent_id,
            status=task.status,
            priority=task.priority,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            deadline=task.deadline.isoformat() if task.deadline else None,
            result=task.result,
            metadata=task.metadata or {}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db_session = Depends(get_db_session)
):
    """
    Get tasks for the current user, optionally filtered by agent, status, or priority.
    
    Args:
        agent_id: Filter tasks by agent ID
        status: Filter tasks by status
        priority: Filter tasks by priority
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip (for pagination)
        current_user: Authenticated user information
        db_session: Database session
        
    Returns:
        List of tasks matching the filters
    """
    try:
        task_system = TaskSystem(db_session)
        tasks = await task_system.get_tasks(
            user_id=current_user["id"],
            agent_id=agent_id,
            status=status,
            priority=priority,
            limit=limit,
            offset=offset
        )
        
        return [
            TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                agent_id=task.agent_id,
                status=task.status,
                priority=task.priority,
                created_at=task.created_at.isoformat(),
                updated_at=task.updated_at.isoformat(),
                deadline=task.deadline.isoformat() if task.deadline else None,
                result=task.result,
                metadata=task.metadata or {}
            )
            for task in tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db_session = Depends(get_db_session)
):
    """
    Get a specific task by ID.
    
    Args:
        task_id: ID of the task to retrieve
        current_user: Authenticated user information
        db_session: Database session
        
    Returns:
        Task information
        
    Raises:
        HTTPException: If task doesn't exist or user doesn't have access
    """
    try:
        task_system = TaskSystem(db_session)
        task = await task_system.get_task(task_id, current_user["id"])
        
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
            
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            agent_id=task.agent_id,
            status=task.status,
            priority=task.priority,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            deadline=task.deadline.isoformat() if task.deadline else None,
            result=task.result,
            metadata=task.metadata or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db_session = Depends(get_db_session)
):
    """
    Update a task's status, priority, or other properties.
    
    Args:
        task_id: ID of the task to update
        task_update: Task update request data
        current_user: Authenticated user information
        db_session: Database session
        
    Returns:
        Updated task information
        
    Raises:
        HTTPException: If task doesn't exist or user doesn't have access
    """
    try:
        task_system = TaskSystem(db_session)
        task = await task_system.update_task(
            task_id=task_id,
            user_id=current_user["id"],
            status=task_update.status,
            priority=task_update.priority,
            result=task_update.result,
            metadata=task_update.metadata
        )
        
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
            
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            agent_id=task.agent_id,
            status=task.status,
            priority=task.priority,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            deadline=task.deadline.isoformat() if task.deadline else None,
            result=task.result,
            metadata=task.metadata or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db_session = Depends(get_db_session)
):
    """
    Delete a task.
    
    Args:
        task_id: ID of the task to delete
        current_user: Authenticated user information
        db_session: Database session
        
    Raises:
        HTTPException: If task doesn't exist or user doesn't have access
    """
    try:
        task_system = TaskSystem(db_session)
        success = await task_system.delete_task(task_id, current_user["id"])
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{task_id}/execute", response_model=TaskResponse)
async def execute_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db_session = Depends(get_db_session)
):
    """
    Execute a task using the assigned agent.
    
    Args:
        task_id: ID of the task to execute
        current_user: Authenticated user information
        db_session: Database session
        
    Returns:
        Updated task information with execution results
        
    Raises:
        HTTPException: If task doesn't exist, user doesn't have access, or execution fails
    """
    try:
        task_system = TaskSystem(db_session)
        task = await task_system.execute_task(task_id, current_user["id"])
        
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
            
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            agent_id=task.agent_id,
            status=task.status,
            priority=task.priority,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            deadline=task.deadline.isoformat() if task.deadline else None,
            result=task.result,
            metadata=task.metadata or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))