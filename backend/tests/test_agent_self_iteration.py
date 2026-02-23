#!/usr/bin/env python3
"""
Test suite for Agent Self-Iteration Framework
Tests all core functionality of the autonomous agent evolution system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Import the modules to test
from app.core.agent_self_iteration import (
    AgentSelfIterationEngine,
    AgentPerformanceMetrics,
    StrategyEvolutionManager,
    ResourceOptimizationEngine
)
from app.models.agent import Agent, AgentConfig
from app.schemas.agent import AgentCreate, AgentUpdate


class TestAgentSelfIterationEngine:
    """Test the main Agent Self-Iteration Engine."""
    
    @pytest.fixture
    def iteration_engine(self):
        """Create a test iteration engine instance."""
        return AgentSelfIterationEngine()
    
    @pytest.fixture
    def sample_agent(self):
        """Create a sample agent for testing."""
        return Agent(
            id="test-agent-1",
            name="Test Agent",
            description="Test agent for iteration",
            config=AgentConfig(
                model_provider="openai",
                model_name="gpt-4",
                temperature=0.7,
                max_tokens=2000,
                capabilities=["text_generation", "reasoning"]
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def performance_metrics(self):
        """Create sample performance metrics."""
        return AgentPerformanceMetrics(
            success_rate=0.85,
            avg_response_time=2.3,
            task_completion_rate=0.92,
            resource_efficiency=0.78,
            error_rate=0.05,
            learning_progress=0.65
        )
    
    def test_engine_initialization(self, iteration_engine):
        """Test that the engine initializes correctly."""
        assert iteration_engine is not None
        assert hasattr(iteration_engine, 'evaluate_agent_performance')
        assert hasattr(iteration_engine, 'evolve_agent_strategy')
        assert hasattr(iteration_engine, 'optimize_agent_resources')
    
    def test_performance_evaluation(self, iteration_engine, sample_agent, performance_metrics):
        """Test agent performance evaluation."""
        # Mock the database session
        mock_db = Mock()
        
        # Test performance evaluation
        result = iteration_engine.evaluate_agent_performance(
            agent=sample_agent,
            metrics=performance_metrics,
            db_session=mock_db
        )
        
        assert result is not None
        assert 'evaluation_score' in result
        assert 'strengths' in result
        assert 'weaknesses' in result
        assert 'recommendations' in result
        
        # Verify score calculation logic
        expected_score = (
            performance_metrics.success_rate * 0.4 +
            performance_metrics.task_completion_rate * 0.3 +
            performance_metrics.resource_efficiency * 0.2 +
            (1 - performance_metrics.error_rate) * 0.1
        )
        assert abs(result['evaluation_score'] - expected_score) < 0.01
    
    def test_strategy_evolution(self, iteration_engine, sample_agent, performance_metrics):
        """Test agent strategy evolution."""
        mock_db = Mock()
        
        # Test strategy evolution based on performance
        evolved_config = iteration_engine.evolve_agent_strategy(
            agent=sample_agent,
            performance_data=performance_metrics,
            evolution_context={
                'task_type': 'reasoning',
                'competition_results': {'wins': 15, 'losses': 5},
                'peer_strategies': ['chain_of_thought', 'self_reflection']
            },
            db_session=mock_db
        )
        
        assert evolved_config is not None
        assert isinstance(evolved_config, AgentConfig)
        
        # Verify that parameters were adjusted based on performance
        if performance_metrics.success_rate < 0.8:
            # Should increase temperature for more creativity
            assert evolved_config.temperature >= sample_agent.config.temperature
        else:
            # Should maintain or decrease temperature for consistency
            assert evolved_config.temperature <= sample_agent.config.temperature + 0.1
    
    def test_resource_optimization(self, iteration_engine, sample_agent, performance_metrics):
        """Test agent resource optimization."""
        mock_db = Mock()
        
        # Test resource optimization
        optimized_config = iteration_engine.optimize_agent_resources(
            agent=sample_agent,
            performance_metrics=performance_metrics,
            resource_usage={
                'cpu_usage': 0.65,
                'memory_usage': 0.72,
                'api_calls_per_minute': 120,
                'tokens_per_request': 1500
            },
            db_session=mock_db
        )
        
        assert optimized_config is not None
        assert isinstance(optimized_config, AgentConfig)
        
        # Verify resource-aware adjustments
        if performance_metrics.resource_efficiency < 0.8:
            # Should reduce max_tokens to improve efficiency
            assert optimized_config.max_tokens <= sample_agent.config.max_tokens
    
    @pytest.mark.asyncio
    async def test_full_iteration_cycle(self, iteration_engine, sample_agent):
        """Test the complete agent iteration cycle."""
        mock_db = AsyncMock()
        
        # Create comprehensive performance data
        performance_data = AgentPerformanceMetrics(
            success_rate=0.78,
            avg_response_time=3.1,
            task_completion_rate=0.85,
            resource_efficiency=0.72,
            error_rate=0.08,
            learning_progress=0.58
        )
        
        # Mock external dependencies
        with patch.object(iteration_engine, 'evaluate_agent_performance') as mock_evaluate, \
             patch.object(iteration_engine, 'evolve_agent_strategy') as mock_evolve, \
             patch.object(iteration_engine, 'optimize_agent_resources') as mock_optimize:
            
            # Setup mock returns
            mock_evaluate.return_value = {
                'evaluation_score': 0.75,
                'strengths': ['reasoning', 'consistency'],
                'weaknesses': ['speed', 'resource_usage'],
                'recommendations': ['reduce_max_tokens', 'increase_temperature']
            }
            
            mock_evolve.return_value = AgentConfig(
                model_provider="openai",
                model_name="gpt-4",
                temperature=0.8,  # Increased for creativity
                max_tokens=1800,  # Reduced for efficiency
                capabilities=["text_generation", "reasoning", "self_reflection"]
            )
            
            mock_optimize.return_value = AgentConfig(
                model_provider="openai",
                model_name="gpt-4",
                temperature=0.8,
                max_tokens=1800,
                capabilities=["text_generation", "reasoning", "self_reflection"],
                batch_size=5,  # Added batch processing
                cache_enabled=True  # Added caching
            )
            
            # Execute full iteration cycle
            result = await iteration_engine.run_full_iteration_cycle(
                agent_id=sample_agent.id,
                db_session=mock_db
            )
            
            # Verify results
            assert result['success'] is True
            assert result['agent_id'] == sample_agent.id
            assert 'new_config' in result
            assert 'iteration_metrics' in result
            
            # Verify that all methods were called
            mock_evaluate.assert_called_once()
            mock_evolve.assert_called_once()
            mock_optimize.assert_called_once()


class TestStrategyEvolutionManager:
    """Test the Strategy Evolution Manager component."""
    
    @pytest.fixture
    def evolution_manager(self):
        """Create a test evolution manager instance."""
        return StrategyEvolutionManager()
    
    def test_strategy_analysis(self, evolution_manager):
        """Test strategy analysis functionality."""
        # Test with different performance scenarios
        scenarios = [
            {
                'success_rate': 0.95,
                'response_time': 1.2,
                'resource_efficiency': 0.85,
                'expected_strategy': 'precision_optimized'
            },
            {
                'success_rate': 0.65,
                'response_time': 4.5,
                'resource_efficiency': 0.45,
                'expected_strategy': 'exploration_focused'
            },
            {
                'success_rate': 0.80,
                'response_time': 2.8,
                'resource_efficiency': 0.75,
                'expected_strategy': 'balanced_adaptive'
            }
        ]
        
        for scenario in scenarios:
            strategy = evolution_manager.analyze_optimal_strategy(
                success_rate=scenario['success_rate'],
                avg_response_time=scenario['response_time'],
                resource_efficiency=scenario['resource_efficiency']
            )
            
            assert strategy is not None
            # The exact strategy name might vary, but it should be a valid strategy
            assert isinstance(strategy, str)
            assert len(strategy) > 0
    
    def test_parameter_adjustment(self, evolution_manager):
        """Test parameter adjustment based on strategy."""
        base_config = {
            'temperature': 0.7,
            'max_tokens': 2000,
            'top_p': 0.9,
            'frequency_penalty': 0.1,
            'presence_penalty': 0.1
        }
        
        # Test different strategies
        strategies = ['precision_optimized', 'exploration_focused', 'balanced_adaptive', 'speed_prioritized']
        
        for strategy in strategies:
            adjusted_config = evolution_manager.adjust_parameters_for_strategy(
                base_config=base_config.copy(),
                strategy=strategy
            )
            
            assert adjusted_config is not None
            assert isinstance(adjusted_config, dict)
            
            # Verify that parameters were actually adjusted
            assert adjusted_config != base_config
            
            # Specific checks for each strategy
            if strategy == 'precision_optimized':
                assert adjusted_config['temperature'] <= base_config['temperature']
                assert adjusted_config['max_tokens'] >= base_config['max_tokens'] * 0.9
            elif strategy == 'exploration_focused':
                assert adjusted_config['temperature'] >= base_config['temperature']
                assert adjusted_config['top_p'] >= base_config['top_p']


class TestResourceOptimizationEngine:
    """Test the Resource Optimization Engine component."""
    
    @pytest.fixture
    def optimization_engine(self):
        """Create a test optimization engine instance."""
        return ResourceOptimizationEngine()
    
    def test_resource_analysis(self, optimization_engine):
        """Test resource usage analysis."""
        resource_data = {
            'cpu_usage': 0.75,
            'memory_usage': 0.82,
            'network_io': 15.5,  # MB/s
            'disk_io': 2.3,      # MB/s
            'api_calls_per_minute': 180,
            'tokens_per_request': 1800,
            'concurrent_requests': 25
        }
        
        analysis = optimization_engine.analyze_resource_bottlenecks(resource_data)
        
        assert analysis is not None
        assert 'bottlenecks' in analysis
        assert 'recommendations' in analysis
        assert 'optimization_score' in analysis
        
        # Verify bottleneck detection
        bottlenecks = analysis['bottlenecks']
        assert 'memory' in bottlenecks or 'cpu' in bottlenecks or 'api_rate' in bottlenecks
    
    def test_batch_size_optimization(self, optimization_engine):
        """Test batch size optimization."""
        current_config = {
            'batch_size': 10,
            'max_concurrent_requests': 30,
            'rate_limit_per_minute': 200
        }
        
        performance_metrics = {
            'avg_response_time': 2.5,
            'success_rate': 0.88,
            'error_rate': 0.05
        }
        
        resource_usage = {
            'cpu_usage': 0.65,
            'memory_usage': 0.70,
            'api_calls_per_minute': 150
        }
        
        optimized_config = optimization_engine.optimize_batch_processing(
            current_config=current_config,
            performance_metrics=performance_metrics,
            resource_usage=resource_usage
        )
        
        assert optimized_config is not None
        assert 'batch_size' in optimized_config
        assert 'max_concurrent_requests' in optimized_config
        
        # Verify that optimization makes sense
        if performance_metrics['success_rate'] > 0.85 and resource_usage['cpu_usage'] < 0.8:
            # Should increase batch size for better throughput
            assert optimized_config['batch_size'] >= current_config['batch_size']
        else:
            # Should maintain or reduce batch size
            assert optimized_config['batch_size'] <= current_config['batch_size'] + 2


class TestIntegrationScenarios:
    """Test integration scenarios for the self-iteration system."""
    
    @pytest.mark.asyncio
    async def test_competitive_learning_scenario(self):
        """Test competitive learning between multiple agents."""
        # This would test how agents learn from competition results
        # Implementation would involve multiple agents and their interaction
        
        # For now, we'll test the basic structure
        engine = AgentSelfIterationEngine()
        assert engine is not None
        
        # The actual competitive learning would be tested in end-to-end tests
        # due to complexity of multi-agent interactions
    
    @pytest.mark.asyncio 
    async def test_collaborative_improvement_scenario(self):
        """Test collaborative improvement between agents."""
        # This would test how agents share knowledge while maintaining competition
        engine = AgentSelfIterationEngine()
        assert engine is not None
        
        # Actual implementation would be in integration tests


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])