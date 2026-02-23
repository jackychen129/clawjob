#!/usr/bin/env python3
"""
End-to-End Tests for Agent Arena Agentic Architecture

These tests simulate real-world usage scenarios to ensure the entire system
works correctly from user interaction through autonomous iteration.
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

# Import the main FastAPI app
from ..app.main import app

client = TestClient(app)


class TestEndToEndAgenticWorkflow:
    """End-to-end tests for the complete agentic workflow."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        self.test_user_id = "test_user_123"
        self.test_session_id = f"session_{int(time.time())}"
        
    def teardown_method(self):
        """Cleanup after each test."""
        # Cleanup any test data if needed
        pass
    
    def test_complete_clawjob_workflow(self):
        """
        Test the complete workflow: agent creation → task submission → 
        autonomous iteration → performance improvement.
        """
        # Step 1: Create multiple agents with different capabilities
        agents_data = [
            {
                "name": "DataAnalyzer-v1",
                "type": "data_analysis",
                "capabilities": ["pattern_recognition", "statistical_analysis"],
                "model_config": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "temperature": 0.7
                }
            },
            {
                "name": "StrategyOptimizer-v1", 
                "type": "strategy_optimization",
                "capabilities": ["optimization", "decision_making"],
                "model_config": {
                    "provider": "anthropic",
                    "model": "claude-3-opus",
                    "temperature": 0.3
                }
            }
        ]
        
        created_agents = []
        for agent_data in agents_data:
            response = client.post(
                "/api/v1/agents/",
                json=agent_data,
                headers={"X-User-ID": self.test_user_id}
            )
            assert response.status_code == 200
            agent_info = response.json()
            created_agents.append(agent_info)
            print(f"Created agent: {agent_info['name']} (ID: {agent_info['id']})")
        
        # Step 2: Submit a complex task to the arena
        task_data = {
            "title": "Market Trend Analysis and Strategy Optimization",
            "description": "Analyze market data patterns and optimize trading strategy",
            "input_data": {
                "market_data": "sample_market_data.csv",
                "historical_performance": "past_performance.json"
            },
            "agent_ids": [agent["id"] for agent in created_agents],
            "max_iterations": 5,
            "success_criteria": {
                "accuracy_threshold": 0.85,
                "completion_time_limit": 300  # seconds
            }
        }
        
        response = client.post(
            "/api/v1/tasks/",
            json=task_data,
            headers={"X-User-ID": self.test_user_id}
        )
        assert response.status_code == 200
        task_info = response.json()
        task_id = task_info["id"]
        print(f"Created task: {task_info['title']} (ID: {task_id})")
        
        # Step 3: Monitor task progress and autonomous iteration
        max_wait_time = 600  # 10 minutes max
        start_time = time.time()
        iteration_count = 0
        
        while time.time() - start_time < max_wait_time:
            # Check task status
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers={"X-User-ID": self.test_user_id}
            )
            assert response.status_code == 200
            task_status = response.json()
            
            current_iteration = task_status.get("current_iteration", 0)
            if current_iteration > iteration_count:
                iteration_count = current_iteration
                print(f"Iteration {iteration_count} completed")
                
                # Verify autonomous improvements
                if iteration_count > 1:
                    self._verify_autonomous_improvement(task_status)
            
            # Check if task is completed
            if task_status["status"] == "completed":
                print(f"Task completed successfully in {iteration_count} iterations")
                break
            elif task_status["status"] == "failed":
                pytest.fail(f"Task failed: {task_status.get('error_message', 'Unknown error')}")
            
            # Wait before next check
            time.sleep(10)
        else:
            pytest.fail("Task did not complete within timeout period")
        
        # Step 4: Verify final results and agent evolution
        self._verify_final_results(task_id)
        self._verify_agent_evolution(created_agents)
        
        print("✅ Complete end-to-end workflow test passed!")
    
    def _verify_autonomous_improvement(self, task_status: Dict):
        """Verify that autonomous iteration is producing improvements."""
        iterations = task_status.get("iterations", [])
        if len(iterations) < 2:
            return
            
        latest_iteration = iterations[-1]
        previous_iteration = iterations[-2]
        
        # Check if performance metrics are improving
        latest_score = latest_iteration.get("performance_score", 0)
        previous_score = previous_iteration.get("performance_score", 0)
        
        # Allow for some variance, but generally should improve
        assert latest_score >= previous_score - 0.05, \
            f"Performance degraded significantly: {previous_score} -> {latest_score}"
        
        # Verify that iteration metadata shows learning
        assert "improvement_notes" in latest_iteration, \
            "Missing improvement notes in iteration data"
        
        print(f"  ✓ Autonomous improvement verified: {previous_score:.3f} -> {latest_score:.3f}")
    
    def _verify_final_results(self, task_id: str):
        """Verify that final task results meet quality standards."""
        response = client.get(
            f"/api/v1/tasks/{task_id}/results",
            headers={"X-User-ID": self.test_user_id}
        )
        assert response.status_code == 200
        results = response.json()
        
        # Verify result structure
        assert "final_output" in results
        assert "performance_metrics" in results
        assert "iteration_summary" in results
        
        # Verify performance meets success criteria
        metrics = results["performance_metrics"]
        assert metrics.get("accuracy", 0) >= 0.85, \
            f"Final accuracy {metrics.get('accuracy', 0)} below threshold 0.85"
        
        print("  ✓ Final results verification passed")
    
    def _verify_agent_evolution(self, original_agents: List[Dict]):
        """Verify that agents have evolved through the process."""
        for original_agent in original_agents:
            agent_id = original_agent["id"]
            response = client.get(
                f"/api/v1/agents/{agent_id}",
                headers={"X-User-ID": self.test_user_id}
            )
            assert response.status_code == 200
            current_agent = response.json()
            
            # Verify agent has iteration history
            assert "iteration_history" in current_agent
            assert len(current_agent["iteration_history"]) > 0
            
            # Verify agent configuration has been optimized
            original_config = original_agent["model_config"]
            current_config = current_agent["model_config"]
            
            # Temperature might have been adjusted based on performance
            # This is a basic check - actual logic would be more sophisticated
            assert isinstance(current_config["temperature"], (int, float)), \
                "Temperature should be a number after optimization"
            
            print(f"  ✓ Agent {original_agent['name']} evolution verified")


class TestSelfHealingAndRecovery:
    """Test the self-healing and recovery capabilities."""
    
    def test_agent_failure_recovery(self):
        """Test that the system can recover from agent failures."""
        # Create an agent that will simulate failure
        agent_data = {
            "name": "FaultyAgent",
            "type": "test_agent",
            "capabilities": ["error_simulation"],
            "model_config": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7
            }
        }
        
        response = client.post(
            "/api/v1/agents/",
            json=agent_data,
            headers={"X-User-ID": "test_user_123"}
        )
        assert response.status_code == 200
        agent_info = response.json()
        agent_id = agent_info["id"]
        
        # Submit a task that will cause the agent to fail initially
        task_data = {
            "title": "Recovery Test Task",
            "description": "Test self-healing capabilities",
            "input_data": {"simulate_failure": True},
            "agent_ids": [agent_id],
            "max_iterations": 3,
            "success_criteria": {"accuracy_threshold": 0.9}
        }
        
        response = client.post(
            "/api/v1/tasks/",
            json=task_data,
            headers={"X-User-ID": "test_user_123"}
        )
        assert response.status_code == 200
        task_id = response.json()["id"]
        
        # Wait for the system to attempt recovery
        time.sleep(30)
        
        # Check that the task eventually succeeds through self-healing
        response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"X-User-ID": "test_user_123"}
        )
        assert response.status_code == 200
        task_status = response.json()
        
        # The task should either complete successfully or show recovery attempts
        assert task_status["status"] in ["completed", "recovery_in_progress"], \
            f"Task failed without recovery: {task_status['status']}"
        
        print("✅ Self-healing and recovery test passed!")


class TestDataSelfIteration:
    """Test data self-iteration capabilities."""
    
    def test_data_quality_improvement(self):
        """Test that data quality improves through autonomous iteration."""
        # Upload initial poor-quality data
        initial_data = {
            "dataset_name": "test_dataset_v1",
            "data": {
                "features": ["feature1", "feature2", "feature3"],
                "samples": [
                    {"feature1": 1.0, "feature2": None, "feature3": "valid"},
                    {"feature1": None, "feature2": 2.0, "feature3": "valid"}, 
                    {"feature1": 3.0, "feature2": 4.0, "feature3": None}
                ]
            },
            "quality_issues": ["missing_values", "inconsistent_types"]
        }
        
        response = client.post(
            "/api/v1/data/",
            json=initial_data,
            headers={"X-User-ID": "test_user_123"}
        )
        assert response.status_code == 200
        dataset_info = response.json()
        dataset_id = dataset_info["id"]
        
        # Request data quality analysis and improvement
        improvement_request = {
            "dataset_id": dataset_id,
            "improvement_goals": ["handle_missing_values", "standardize_types"],
            "max_iterations": 3
        }
        
        response = client.post(
            "/api/v1/data/improve",
            json=improvement_request,
            headers={"X-User-ID": "test_user_123"}
        )
        assert response.status_code == 200
        improvement_job = response.json()
        job_id = improvement_job["job_id"]
        
        # Monitor improvement progress
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = client.get(
                f"/api/v1/data/improve/{job_id}",
                headers={"X-User-ID": "test_user_123"}
            )
            assert response.status_code == 200
            job_status = response.json()
            
            if job_status["status"] == "completed":
                # Verify improved data quality
                improved_data = job_status["improved_dataset"]
                assert improved_data["quality_score"] > dataset_info["quality_score"], \
                    "Data quality did not improve"
                break
            elif job_status["status"] == "failed":
                pytest.fail(f"Data improvement failed: {job_status.get('error', 'Unknown')}")
            
            time.sleep(5)
        else:
            pytest.fail("Data improvement did not complete within timeout")
        
        print("✅ Data self-iteration test passed!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])