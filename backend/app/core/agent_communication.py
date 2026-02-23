"""
Agentic Communication and Coordination Layer
Enables intelligent message routing, consensus building, and knowledge sharing between agents.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import asyncio
import json
from datetime import datetime
import logging

from ..models.agent import Agent
from ..schemas.communication import Message, ConsensusResult, KnowledgeExchange

logger = logging.getLogger(__name__)

@dataclass
class CommunicationChannel:
    """Represents a communication channel between agents."""
    channel_id: str
    participants: List[str]  # List of agent IDs
    message_history: List[Message]
    created_at: datetime
    is_active: bool = True

class AgenticCommunicationManager:
    """
    Manages all inter-agent communication with intelligent routing and coordination.
    """
    
    def __init__(self):
        self.channels: Dict[str, CommunicationChannel] = {}
        self.agent_expertise_map: Dict[str, List[str]] = {}  # agent_id -> expertise areas
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.consensus_tasks: Dict[str, asyncio.Task] = {}
        
    async def register_agent(self, agent: Agent) -> None:
        """Register an agent with its expertise areas for intelligent routing."""
        self.agent_expertise_map[agent.id] = agent.expertise_areas or []
        logger.info(f"Registered agent {agent.id} with expertise: {agent.expertise_areas}")
        
    async def send_message(self, message: Message) -> bool:
        """Send a message with intelligent routing based on content and expertise."""
        try:
            # Determine routing strategy based on message type
            if message.message_type == "task_collaboration":
                recipients = await self._find_collaborative_agents(message)
            elif message.message_type == "knowledge_request":
                recipients = await self._find_expert_agents(message)
            elif message.message_type == "consensus_building":
                recipients = await self._initiate_consensus_process(message)
            else:
                # Default broadcast to all registered agents
                recipients = list(self.agent_expertise_map.keys())
            
            # Route message to appropriate recipients
            for recipient in recipients:
                await self._deliver_message(message, recipient)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def _find_collaborative_agents(self, message: Message) -> List[str]:
        """Find agents suitable for collaborative task solving."""
        # Analyze message content to determine required expertise
        required_expertise = self._extract_required_expertise(message.content)
        
        # Find agents with complementary expertise
        suitable_agents = []
        for agent_id, expertise in self.agent_expertise_map.items():
            if any(expertise_area in required_expertise for expertise_area in expertise):
                suitable_agents.append(agent_id)
                
        # Ensure diversity in agent selection for better collaboration
        return suitable_agents[:5]  # Limit to top 5 most relevant agents
        
    async def _find_expert_agents(self, message: Message) -> List[str]:
        """Find domain experts for knowledge requests."""
        # Extract domain/topic from knowledge request
        topic = self._extract_knowledge_topic(message.content)
        
        # Rank agents by expertise relevance
        agent_scores = {}
        for agent_id, expertise in self.agent_expertise_map.items():
            score = sum(1 for exp in expertise if topic.lower() in exp.lower())
            if score > 0:
                agent_scores[agent_id] = score
                
        # Return top 3 experts
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        return [agent_id for agent_id, _ in sorted_agents[:3]]
        
    async def _initiate_consensus_process(self, message: Message) -> List[str]:
        """Initiate a consensus building process among relevant agents."""
        consensus_id = f"consensus_{datetime.now().timestamp()}"
        
        # Identify all agents that should participate in consensus
        participants = list(self.agent_expertise_map.keys())
        
        # Create consensus task
        consensus_task = asyncio.create_task(
            self._run_consensus_process(consensus_id, message, participants)
        )
        self.consensus_tasks[consensus_id] = consensus_task
        
        return participants
        
    async def _run_consensus_process(
        self, 
        consensus_id: str, 
        initial_message: Message, 
        participants: List[str]
    ) -> ConsensusResult:
        """Run the actual consensus building algorithm."""
        try:
            # Phase 1: Gather initial responses from all participants
            responses = await self._gather_consensus_responses(initial_message, participants)
            
            # Phase 2: Iterative refinement until consensus or timeout
            max_iterations = 5
            current_responses = responses
            iteration = 0
            
            while iteration < max_iterations:
                consensus_level = self._calculate_consensus_level(current_responses)
                if consensus_level >= 0.8:  # 80% agreement threshold
                    break
                    
                # Share current state with all participants for refinement
                refinement_message = Message(
                    sender="consensus_manager",
                    recipients=participants,
                    content=f"Consensus refinement needed. Current agreement: {consensus_level:.2f}",
                    message_type="consensus_refinement",
                    metadata={"current_responses": current_responses}
                )
                
                refined_responses = await self._gather_consensus_responses(
                    refinement_message, participants
                )
                current_responses = refined_responses
                iteration += 1
                
            # Phase 3: Generate final consensus result
            final_result = self._generate_consensus_result(current_responses)
            
            logger.info(f"Consensus process {consensus_id} completed with level: {consensus_level:.2f}")
            return final_result
            
        except Exception as e:
            logger.error(f"Consensus process {consensus_id} failed: {e}")
            return ConsensusResult(
                consensus_id=consensus_id,
                success=False,
                result="Consensus failed due to error",
                participants=participants,
                consensus_level=0.0
            )
    
    async def _gather_consensus_responses(
        self, 
        message: Message, 
        participants: List[str]
    ) -> List[Dict[str, Any]]:
        """Gather responses from all consensus participants."""
        responses = []
        tasks = []
        
        for participant in participants:
            task = asyncio.create_task(
                self._request_agent_response(message, participant)
            )
            tasks.append(task)
            
        # Wait for all responses with timeout
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.warning("Consensus response gathering timed out")
            
        return [resp for resp in responses if not isinstance(resp, Exception)]
        
    def _calculate_consensus_level(self, responses: List[Dict[str, Any]]) -> float:
        """Calculate the level of agreement among responses."""
        if len(responses) <= 1:
            return 1.0
            
        # Simple similarity calculation (in real implementation, use semantic similarity)
        unique_responses = len(set(str(resp) for resp in responses))
        total_responses = len(responses)
        
        return 1.0 - (unique_responses - 1) / (total_responses - 1) if total_responses > 1 else 1.0
        
    def _generate_consensus_result(self, responses: List[Dict[str, Any]]) -> ConsensusResult:
        """Generate the final consensus result from responses."""
        # In real implementation, this would use more sophisticated aggregation
        most_common_response = max(responses, key=responses.count) if responses else {}
        
        return ConsensusResult(
            consensus_id=f"consensus_{datetime.now().timestamp()}",
            success=True,
            result=most_common_response,
            participants=list(self.agent_expertise_map.keys()),
            consensus_level=self._calculate_consensus_level(responses)
        )
        
    async def _request_agent_response(self, message: Message, agent_id: str) -> Dict[str, Any]:
        """Request a response from a specific agent."""
        # This would integrate with the actual agent execution system
        # For now, return a mock response
        return {
            "agent_id": agent_id,
            "response": f"Mock response from {agent_id} to: {message.content[:50]}...",
            "confidence": 0.8,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _deliver_message(self, message: Message, recipient: str) -> None:
        """Deliver a message to a specific recipient agent."""
        # This would integrate with the agent's message handling system
        logger.debug(f"Delivering message to {recipient}: {message.content[:100]}...")
        
        # Add to message queue for processing
        await self.message_queue.put((recipient, message))
        
    def _extract_required_expertise(self, content: str) -> List[str]:
        """Extract required expertise areas from message content."""
        # Simple keyword extraction (in real implementation, use NLP)
        keywords = ["analysis", "trading", "prediction", "optimization", "security"]
        found_keywords = []
        
        content_lower = content.lower()
        for keyword in keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
                
        return found_keywords or ["general"]
        
    def _extract_knowledge_topic(self, content: str) -> str:
        """Extract the main topic from a knowledge request."""
        # Simple topic extraction (in real implementation, use topic modeling)
        return content.split("?")[0] if "?" in content else content[:50]
        
    async def get_message_queue(self) -> asyncio.Queue:
        """Get the message queue for external consumption."""
        return self.message_queue
        
    async def shutdown(self) -> None:
        """Gracefully shutdown the communication manager."""
        # Cancel all consensus tasks
        for task in self.consensus_tasks.values():
            if not task.done():
                task.cancel()
                
        logger.info("Agentic communication manager shutdown complete")

# Global instance for application-wide access
communication_manager = AgenticCommunicationManager()