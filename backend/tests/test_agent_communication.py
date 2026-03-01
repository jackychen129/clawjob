"""
Unit tests for agent communication module.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import json
from datetime import datetime, timedelta

# Import the module to test
from app.core.agent_communication import (
    AgentCommunicationManager,
    MessageRouter,
    ConsensusBuilder,
    ConflictResolver,
    KnowledgeExchangeProtocol
)
from app.schemas.agent import AgentMessage, AgentConsensusRequest, AgentConflictResolution


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = Mock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.hgetall = AsyncMock()
    mock.hset = AsyncMock()
    return mock


@pytest.fixture
def communication_manager(mock_redis):
    """Create a communication manager instance for testing."""
    return AgentCommunicationManager(redis_client=mock_redis)


class TestAgentCommunicationManager:
    """Test the AgentCommunicationManager class."""
    
    @pytest.mark.asyncio
    async def test_send_message(self, communication_manager):
        """Test sending a message between agents."""
        message = AgentMessage(
            sender_id="agent_1",
            receiver_id="agent_2", 
            message_type="task_request",
            content={"task": "analyze_data", "data": {"sample": "data"}},
            priority="high"
        )
        
        await communication_manager.send_message(message)
        
        # Verify message was published to Redis
        communication_manager.redis_client.publish.assert_called_once()
        
        # Verify message was stored in history
        assert len(communication_manager.message_history) == 1
        assert communication_manager.message_history[0].sender_id == "agent_1"
    
    @pytest.mark.asyncio
    async def test_receive_message(self, communication_manager):
        """Test receiving a message."""
        message_data = {
            "sender_id": "agent_1",
            "receiver_id": "agent_2",
            "message_type": "task_response",
            "content": {"result": "success", "data": {"processed": "data"}},
            "priority": "normal",
            "timestamp": datetime.now().isoformat()
        }
        
        message = await communication_manager.receive_message(json.dumps(message_data))
        
        assert message.sender_id == "agent_1"
        assert message.receiver_id == "agent_2"
        assert message.message_type == "task_response"
    
    @pytest.mark.asyncio
    async def test_get_agent_messages(self, communication_manager):
        """Test retrieving messages for an agent."""
        # Send multiple messages
        message1 = AgentMessage(
            sender_id="agent_1",
            receiver_id="agent_2",
            message_type="task_request",
            content={"task": "task1"},
            priority="high"
        )
        message2 = AgentMessage(
            sender_id="agent_3", 
            receiver_id="agent_2",
            message_type="task_request",
            content={"task": "task2"},
            priority="normal"
        )
        
        await communication_manager.send_message(message1)
        await communication_manager.send_message(message2)
        
        # Retrieve messages for agent_2
        messages = await communication_manager.get_agent_messages("agent_2")
        
        assert len(messages) == 2
        assert messages[0].sender_id == "agent_1"  # High priority first
        assert messages[1].sender_id == "agent_3"


class TestMessageRouter:
    """Test the MessageRouter class."""
    
    def test_route_message_by_expertise(self):
        """Test routing messages based on agent expertise."""
        router = MessageRouter()
        
        # Register agents with different expertise
        router.register_agent("agent_ml", ["machine_learning", "data_analysis"])
        router.register_agent("agent_nlp", ["natural_language", "text_processing"])
        router.register_agent("agent_cv", ["computer_vision", "image_processing"])
        
        # Test routing a machine learning message
        message = AgentMessage(
            sender_id="user",
            receiver_id="",  # Will be routed
            message_type="task_request",
            content={"task": "train_model", "domain": "machine_learning"},
            priority="normal"
        )
        
        routed_message = router.route_message(message)
        assert routed_message.receiver_id == "agent_ml"
    
    def test_route_message_with_priority(self):
        """Test routing messages with priority handling."""
        router = MessageRouter()
        router.register_agent("agent_1", ["general"])
        router.register_agent("agent_2", ["general"])
        
        # High priority message should go to available agent
        message = AgentMessage(
            sender_id="user",
            receiver_id="",
            message_type="urgent_task",
            content={"task": "critical_analysis"},
            priority="high"
        )
        
        routed_message = router.route_message(message)
        assert routed_message.receiver_id in ["agent_1", "agent_2"]


class TestConsensusBuilder:
    """Test the ConsensusBuilder class."""
    
    @pytest.mark.asyncio
    async def test_build_consensus_simple(self):
        """Test building consensus with simple voting."""
        consensus_builder = ConsensusBuilder()
        
        request = AgentConsensusRequest(
            task_id="task_1",
            agent_ids=["agent_1", "agent_2", "agent_3"],
            proposals=[
                {"agent_id": "agent_1", "proposal": "solution_a"},
                {"agent_id": "agent_2", "proposal": "solution_b"}, 
                {"agent_id": "agent_3", "proposal": "solution_a"}
            ],
            consensus_method="majority_vote"
        )
        
        result = await consensus_builder.build_consensus(request)
        
        assert result.consensus_reached == True
        assert result.winning_proposal == "solution_a"
        assert result.confidence_score == 2.0 / 3.0
    
    @pytest.mark.asyncio
    async def test_build_consensus_weighted(self):
        """Test building consensus with weighted voting."""
        consensus_builder = ConsensusBuilder()
        
        request = AgentConsensusRequest(
            task_id="task_1",
            agent_ids=["agent_1", "agent_2", "agent_3"],
            proposals=[
                {"agent_id": "agent_1", "proposal": "solution_a", "weight": 0.8},
                {"agent_id": "agent_2", "proposal": "solution_b", "weight": 0.6},
                {"agent_id": "agent_3", "proposal": "solution_a", "weight": 0.9}
            ],
            consensus_method="weighted_vote"
        )
        
        result = await consensus_builder.build_consensus(request)
        
        assert result.consensus_reached == True
        assert result.winning_proposal == "solution_a"
        expected_weight = (0.8 + 0.9) / (0.8 + 0.6 + 0.9)
        assert abs(result.confidence_score - expected_weight) < 0.01


class TestConflictResolver:
    """Test the ConflictResolver class."""
    
    @pytest.mark.asyncio
    async def test_resolve_strategy_conflict(self):
        """Test resolving conflicting agent strategies."""
        resolver = ConflictResolver()
        
        conflict_request = AgentConflictResolution(
            task_id="task_1",
            conflicting_agents=["agent_1", "agent_2"],
            conflict_type="strategy_conflict",
            agent_strategies={
                "agent_1": {"approach": "conservative", "risk_tolerance": 0.2},
                "agent_2": {"approach": "aggressive", "risk_tolerance": 0.8}
            },
            resolution_method="compromise"
        )
        
        result = await resolver.resolve_conflict(conflict_request)
        
        assert result.resolution_successful == True
        assert "compromise" in result.resolved_strategy
        
        # Check that compromise is between the two extremes
        resolved_risk = result.resolved_strategy["risk_tolerance"]
        assert 0.2 < resolved_risk < 0.8


class TestKnowledgeExchangeProtocol:
    """Test the KnowledgeExchangeProtocol class."""
    
    @pytest.mark.asyncio
    async def test_secure_knowledge_exchange(self):
        """Test secure knowledge exchange between agents."""
        protocol = KnowledgeExchangeProtocol(security_level="high")
        
        knowledge_package = {
            "source_agent": "agent_expert",
            "knowledge_type": "model_weights",
            "data": {"weights": [0.1, 0.2, 0.3]},
            "access_level": "restricted",
            "expiration": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        # Encrypt and send knowledge
        encrypted_package = await protocol.encrypt_knowledge(knowledge_package)
        assert "encrypted_data" in encrypted_package
        
        # Receive and decrypt knowledge
        decrypted_package = await protocol.decrypt_knowledge(encrypted_package)
        assert decrypted_package["source_agent"] == "agent_expert"
        assert decrypted_package["data"]["weights"] == [0.1, 0.2, 0.3]
    
    @pytest.mark.asyncio
    async def test_knowledge_access_control(self):
        """Test knowledge access control mechanisms."""
        protocol = KnowledgeExchangeProtocol(security_level="high")
        
        # Agent with insufficient permissions should be denied
        access_request = {
            "requesting_agent": "agent_basic",
            "target_knowledge": "expert_model_weights",
            "agent_clearance": "basic",
            "required_clearance": "expert"
        }
        
        allowed = await protocol.check_access_permissions(access_request)
        assert allowed == False
        
        # Agent with sufficient permissions should be allowed
        access_request["agent_clearance"] = "expert"
        allowed = await protocol.check_access_permissions(access_request)
        assert allowed == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])