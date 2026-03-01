"""
Integration tests for the complete agentic architecture.
Tests the interaction between all new components.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.data_iteration_engine import DataIterationEngine
from app.core.agent_self_iteration import AgentSelfIterationManager
from app.core.agent_communication import AgentCommunicationManager
from app.core.health_monitor import HealthMonitor

client = TestClient(app)

class TestAgenticIntegration:
    """Integration tests for the complete agentic system."""
    
    def test_complete_agent_lifecycle(self):
        """Test the complete lifecycle of an agent with self-iteration."""
        # 1. Create initial agent configuration
        agent_config = {
            "name": "test-agent-integration",
            "model": "gpt-4",
            "capabilities": ["text-generation", "reasoning"],
            "initial_strategy": "conservative"
        }
        
        # 2. Submit a task to the agent
        task_data = {
            "task_id": "integration-test-001",
            "description": "Analyze market trends for AI stocks",
            "complexity": "medium",
            "deadline": "2026-02-16T10:00:00Z"
        }
        
        # 3. Simulate agent execution and performance tracking
        iteration_manager = AgentSelfIterationManager()
        communication_manager = AgentCommunicationManager()
        
        # Initial performance baseline
        initial_performance = {
            "accuracy": 0.75,
            "speed": 0.8,
            "resource_usage": 0.6
        }
        
        # 4. Trigger self-iteration based on performance
        improved_config = iteration_manager.analyze_and_improve(
            agent_id="test-agent-integration",
            performance_metrics=initial_performance,
            task_complexity="medium"
        )
        
        # 5. Verify improvements were made
        assert improved_config is not None
        assert "strategy" in improved_config
        assert "resource_allocation" in improved_config
        
        # 6. Test communication with other agents
        message = {
            "sender": "test-agent-integration",
            "recipients": ["collaborator-agent"],
            "content": "Requesting collaboration on market analysis",
            "priority": "high",
            "task_context": task_data
        }
        
        routing_result = communication_manager.route_message(message)
        assert routing_result["status"] == "routed"
        assert "delivery_status" in routing_result
        
        # 7. Verify data iteration engine integration
        data_engine = DataIterationEngine()
        feedback_data = {
            "agent_id": "test-agent-integration",
            "task_id": "integration-test-001",
            "outcome": "success",
            "performance_score": 0.85,
            "lessons_learned": ["Better market data needed", "Faster response time required"]
        }
        
        iteration_result = data_engine.process_feedback(feedback_data)
        assert iteration_result["status"] == "processed"
        assert "data_improvements" in iteration_result
        
        # 8. Check overall system health
        health_monitor = HealthMonitor()
        health_status = health_monitor.get_system_health()
        assert health_status["overall_status"] == "healthy"
        assert health_status["components"]["agents"] == "operational"
        assert health_status["components"]["data_pipeline"] == "operational"
        
    def test_multi_agent_collaboration(self):
        """Test multiple agents collaborating with self-iteration."""
        # Create multiple agents with different specializations
        agents = [
            {
                "name": "market-analyst",
                "specialization": "financial-analysis",
                "model": "gpt-4"
            },
            {
                "name": "tech-analyst", 
                "specialization": "technology-trends",
                "model": "claude-3"
            },
            {
                "name": "risk-analyst",
                "specialization": "risk-assessment",
                "model": "gemini-pro"
            }
        ]
        
        # Simulate collaborative task
        collaborative_task = {
            "task_id": "collab-test-001",
            "description": "Comprehensive AI industry analysis",
            "required_specializations": ["financial-analysis", "technology-trends", "risk-assessment"],
            "complexity": "high"
        }
        
        communication_manager = AgentCommunicationManager()
        
        # Coordinate agents through communication manager
        coordination_message = {
            "sender": "system",
            "recipients": [agent["name"] for agent in agents],
            "content": "Initiate collaborative analysis",
            "task_context": collaborative_task,
            "coordination_type": "collaborative"
        }
        
        result = communication_manager.coordinate_collaboration(coordination_message)
        assert result["status"] == "coordinated"
        assert len(result["participating_agents"]) == 3
        
        # Verify each agent can self-iterate based on collaboration results
        iteration_manager = AgentSelfIterationManager()
        for agent in agents:
            performance_data = {
                "accuracy": 0.8 + (hash(agent["name"]) % 10) * 0.01,
                "collaboration_effectiveness": 0.75,
                "specialization_accuracy": 0.9
            }
            
            improved_config = iteration_manager.analyze_and_improve(
                agent_id=agent["name"],
                performance_metrics=performance_data,
                task_complexity="high",
                collaboration_context=True
            )
            
            assert improved_config is not None
            
    def test_end_to_end_agentic_workflow(self):
        """Test complete end-to-end workflow with all agentic features."""
        # 1. Submit complex task through API
        response = client.post("/tasks/", json={
            "description": "Predict Q1 2026 AI market trends",
            "complexity": "high",
            "deadline": "2026-03-31T23:59:59Z",
            "required_capabilities": ["market-analysis", "trend-prediction", "risk-assessment"]
        })
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # 2. Monitor task progress through health monitoring
        health_monitor = HealthMonitor()
        task_health = health_monitor.monitor_task_health(task_id)
        assert task_health["status"] in ["active", "processing", "completed"]
        
        # 3. Simulate agent performance feedback
        feedback_response = client.post(f"/feedback/{task_id}", json={
            "agent_id": "primary-analyst",
            "performance_score": 0.88,
            "accuracy": 0.92,
            "speed": 0.75,
            "resource_efficiency": 0.85,
            "lessons_learned": ["Need better real-time data", "Improve prediction algorithms"]
        })
        
        assert feedback_response.status_code == 200
        
        # 4. Verify data iteration engine processed feedback
        data_engine = DataIterationEngine()
        recent_iterations = data_engine.get_recent_iterations(limit=1)
        assert len(recent_iterations) > 0
        
        # 5. Check that agents have been updated with new strategies
        iteration_manager = AgentSelfIterationManager()
        agent_status = iteration_manager.get_agent_status("primary-analyst")
        assert agent_status["last_iteration"] is not None
        assert agent_status["current_strategy"] != "initial"
        
        # 6. Verify communication logs show proper coordination
        communication_manager = AgentCommunicationManager()
        task_messages = communication_manager.get_task_messages(task_id)
        assert len(task_messages) > 0
        
        # 7. Final system health check
        final_health = health_monitor.get_system_health()
        assert final_health["overall_status"] == "healthy"
        
    def test_autonomous_optimization_cycle(self):
        """Test the autonomous optimization cycle."""
        # Initialize the complete agentic system
        data_engine = DataIterationEngine()
        iteration_manager = AgentSelfIterationManager()
        communication_manager = AgentCommunicationManager()
        health_monitor = HealthMonitor()
        
        # Simulate multiple iterations
        for cycle in range(3):
            # Generate synthetic performance data
            performance_data = {
                "cycle": cycle,
                "baseline_performance": 0.7 + (cycle * 0.05),
                "bottlenecks": ["data_quality", "response_time"] if cycle == 0 else ["response_time"],
                "opportunities": ["better_algorithms", "more_training_data"]
            }
            
            # Process through data iteration engine
            data_improvements = data_engine.suggest_improvements(performance_data)
            assert "suggested_changes" in data_improvements
            
            # Apply improvements to agents
            agent_updates = iteration_manager.apply_data_improvements(
                agent_ids=["test-agent-1", "test-agent-2"],
                improvements=data_improvements
            )
            
            assert len(agent_updates) == 2
            
            # Verify communication about changes
            change_notification = {
                "sender": "system",
                "recipients": ["all-agents"],
                "content": f"Data pipeline improvements applied in cycle {cycle}",
                "change_type": "data_improvement",
                "improvements": data_improvements
            }
            
            comm_result = communication_manager.broadcast_system_update(change_notification)
            assert comm_result["delivered_count"] >= 2
            
            # Check health after changes
            health_after = health_monitor.get_system_health()
            assert health_after["components"]["data_pipeline"] == "optimized"
            
        # Verify final state shows improvement
        final_performance = health_monitor.get_performance_metrics()
        assert final_performance["average_accuracy"] > 0.7
        assert final_performance["optimization_cycles"] == 3

# Additional integration scenarios
class TestEdgeCases:
    """Test edge cases and error handling in agentic integration."""
    
    def test_agent_failure_recovery(self):
        """Test recovery when an agent fails during self-iteration."""
        iteration_manager = AgentSelfIterationManager()
        
        # Simulate agent failure
        failed_agent_data = {
            "agent_id": "failed-agent",
            "error_type": "model_timeout",
            "last_successful_iteration": 5,
            "failure_context": {"task_id": "failed-task-001", "model": "unavailable-model"}
        }
        
        recovery_plan = iteration_manager.handle_agent_failure(failed_agent_data)
        assert recovery_plan["status"] == "recovery_initiated"
        assert "fallback_strategy" in recovery_plan
        
    def test_data_corruption_handling(self):
        """Test handling of corrupted data in iteration pipeline."""
        data_engine = DataIterationEngine()
        
        corrupted_data = {
            "agent_id": "test-agent",
            "task_id": "corrupted-task",
            "performance_score": "invalid_string",  # Should be numeric
            "accuracy": None,  # Missing data
            "timestamp": "2026-02-15T15:30:00Z"
        }
        
        result = data_engine.process_feedback(corrupted_data)
        assert result["status"] == "error_handled"
        assert "validation_errors" in result
        
    def test_communication_overload_protection(self):
        """Test protection against communication overload."""
        communication_manager = AgentCommunicationManager()
        
        # Send many messages rapidly
        messages = []
        for i in range(100):
            messages.append({
                "sender": f"agent-{i}",
                "recipients": ["target-agent"],
                "content": f"Message {i}",
                "priority": "low"
            })
        
        # Should handle gracefully without crashing
        results = []
        for msg in messages[:10]:  # Test first 10
            result = communication_manager.route_message(msg)
            results.append(result)
            
        assert len(results) == 10
        # Some messages might be queued or rate-limited
        assert all(r["status"] in ["routed", "queued", "rate_limited"] for r in results)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])