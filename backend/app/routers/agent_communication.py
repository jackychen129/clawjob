from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import Agent, CommunicationLog
from ..schemas import (
    AgentCommunicationCreate,
    AgentCommunicationResponse,
    CommunicationStatus,
    MessageRoute,
    ConsensusResult
)
from ..core.agent_communication import AgentCommunicationManager
from ..security import get_current_active_user

router = APIRouter(prefix="/api/v1/communication", tags=["agent-communication"])

@router.post("/send-message", response_model=AgentCommunicationResponse)
async def send_agent_message(
    message: AgentCommunicationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Send a message between agents with intelligent routing"""
    try:
        manager = AgentCommunicationManager(db)
        result = await manager.send_message(message)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.post("/build-consensus", response_model=ConsensusResult)
async def build_agent_consensus(
    agent_ids: List[str],
    task_description: str,
    consensus_threshold: float = 0.8,
    max_rounds: int = 5,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Build consensus among multiple agents for complex tasks"""
    try:
        manager = AgentCommunicationManager(db)
        result = await manager.build_consensus(
            agent_ids=agent_ids,
            task_description=task_description,
            consensus_threshold=consensus_threshold,
            max_rounds=max_rounds
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build consensus: {str(e)}"
        )

@router.get("/message-routes/{agent_id}", response_model=List[MessageRoute])
async def get_agent_message_routes(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get intelligent message routing recommendations for an agent"""
    try:
        manager = AgentCommunicationManager(db)
        routes = await manager.get_optimal_routes(agent_id)
        return routes
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get message routes: {str(e)}"
        )

@router.get("/status", response_model=CommunicationStatus)
async def get_communication_status(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get overall communication system health status"""
    try:
        manager = AgentCommunicationManager(db)
        status_info = await manager.get_system_status()
        return status_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get communication status: {str(e)}"
        )

@router.post("/resolve-conflict")
async def resolve_agent_conflict(
    conflicting_agents: List[str],
    conflict_context: str,
    resolution_strategy: str = "consensus",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Automatically resolve conflicts between competing agents"""
    try:
        manager = AgentCommunicationManager(db)
        result = await manager.resolve_conflict(
            agent_ids=conflicting_agents,
            context=conflict_context,
            strategy=resolution_strategy
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve conflict: {str(e)}"
        )