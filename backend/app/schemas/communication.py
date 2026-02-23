"""Communication schemas for agent coordination."""
from typing import List, Any, Optional
from pydantic import BaseModel


class Message(BaseModel):
    """Message between agents."""
    sender: str
    recipients: List[str]
    content: str
    message_type: str = "general"
    metadata: Optional[dict] = None

    class Config:
        extra = "allow"


class ConsensusResult(BaseModel):
    """Result of a consensus process."""
    consensus_id: str
    success: bool
    result: Any
    participants: List[str]
    consensus_level: float = 0.0

    class Config:
        extra = "allow"


class KnowledgeExchange(BaseModel):
    """Knowledge exchange between agents."""
    source_agent_id: str = ""
    target_agent_id: str = ""
    content: str = ""
    exchange_type: str = "share"

    class Config:
        extra = "allow"
