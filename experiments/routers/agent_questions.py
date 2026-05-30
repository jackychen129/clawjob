"""
Agent Questions Router
Handles intelligent agent question and answer functionality with vector database integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.database.vector_db import VectorDB
from app.database.relational_db import RelationalDB
from app.agents.agent_manager import AgentManager
from app.security import get_current_user

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

class QuestionRequest(BaseModel):
    question: str
    agent_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    use_memory: bool = True
    use_tools: bool = True

class QuestionResponse(BaseModel):
    answer: str
    agent_id: str
    sources: List[Dict[str, Any]]
    confidence: float
    execution_time: float

@router.post("/ask", response_model=QuestionResponse)
async def ask_agent_question(
    request: QuestionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ask a question to an intelligent agent.
    
    The agent will:
    1. Search vector database for relevant context
    2. Use memory system to recall past interactions
    3. Execute tools if needed
    4. Generate intelligent response
    
    Args:
        request: Question request with optional agent ID and context
        current_user: Authenticated user
        
    Returns:
        QuestionResponse with answer and metadata
    """
    try:
        # Initialize systems
        vector_db = VectorDB()
        relational_db = RelationalDB()
        agent_manager = AgentManager()
        
        # Get or create agent
        if request.agent_id:
            agent = await agent_manager.get_agent(request.agent_id)
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent {request.agent_id} not found"
                )
        else:
            # Create temporary agent for this question
            agent = await agent_manager.create_temporary_agent(
                user_id=current_user["id"],
                context=request.context
            )
        
        # Process question with agentic capabilities
        response = await agent.process_question(
            question=request.question,
            use_memory=request.use_memory,
            use_tools=request.use_tools,
            user_context=current_user
        )
        
        return QuestionResponse(
            answer=response["answer"],
            agent_id=agent.id,
            sources=response.get("sources", []),
            confidence=response.get("confidence", 0.0),
            execution_time=response.get("execution_time", 0.0)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}"
        )

@router.post("/agents/{agent_id}/ask", response_model=QuestionResponse)
async def ask_specific_agent(
    agent_id: str,
    request: QuestionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ask a question to a specific agent.
    """
    request.agent_id = agent_id
    return await ask_agent_question(request, current_user)

@router.get("/agents/{agent_id}/memory")
async def get_agent_memory(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get memory history for a specific agent.
    """
    try:
        agent_manager = AgentManager()
        agent = await agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        memory = await agent.get_memory_history()
        return {"memory": memory}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving memory: {str(e)}"
        )