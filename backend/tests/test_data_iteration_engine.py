"""
Unit tests for Data Iteration Engine
"""
import pytest
from unittest.mock import Mock, patch
from app.core.data_iteration_engine import DataIterationEngine

@pytest.fixture
def data_iteration_engine():
    """Create a DataIterationEngine instance for testing"""
    return DataIterationEngine()

@pytest.fixture
def sample_data():
    """Provide sample test data"""
    return {
        'field1': 'value1',
        'field2': 'value2', 
        'field3': None,
        'field4': '',
        'field5': 'value5'
    }

class TestDataIterationEngine:
    """Test cases for DataIterationEngine"""
    
    def test_init(self, data_iteration_engine):
        """Test DataIterationEngine initialization"""
        assert isinstance(data_iteration_engine, DataIterationEngine)
        assert data_iteration_engine.iteration_history == []
        assert data_iteration_engine.optimization_rules == {}
    
    def test_calculate_completeness(self, data_iteration_engine, sample_data):
        """Test completeness calculation"""
        completeness = data_iteration_engine._calculate_completeness(sample_data)
        # 3 out of 5 fields are non-empty (field3=None, field4="")
        expected = 3/5  # 0.6
        assert abs(completeness - expected) < 0.01
    
    def test_calculate_completeness_empty_data(self, data_iteration_engine):
        """Test completeness with empty data"""
        completeness = data_iteration_engine._calculate_completeness({})
        assert completeness == 0.0
    
    def test_calculate_consistency(self, data_iteration_engine, sample_data):
        """Test consistency calculation"""
        consistency = data_iteration_engine._calculate_consistency(sample_data)
        assert consistency == 1.0
    
    def test_calculate_accuracy(self, data_iteration_engine, sample_data):
        """Test accuracy calculation"""
        accuracy = data_iteration_engine._calculate_accuracy(sample_data)
        assert accuracy == 0.95
    
    def test_calculate_timeliness(self, data_iteration_engine, sample_data):
        """Test timeliness calculation"""
        timeliness = data_iteration_engine._calculate_timeliness(sample_data)
        assert timeliness == 0.98
    
    @pytest.mark.asyncio
    async def test_analyze_data_quality(self, data_iteration_engine, sample_data):
        """Test data quality analysis"""
        result = await data_iteration_engine.analyze_data_quality(sample_data)
        
        assert 'metrics' in result
        assert 'suggestions' in result
        assert 'timestamp' in result
        
        metrics = result['metrics']
        assert 'completeness' in metrics
        assert 'consistency' in metrics
        assert 'accuracy' in metrics
        assert 'timeliness' in metrics
        
        suggestions = result['suggestions']
        assert isinstance(suggestions, list)
    
    @pytest.mark.asyncio
    async def test_optimize_data_pipeline(self, data_iteration_engine):
        """Test data pipeline optimization"""
        feedback_data = {'agent_performance': 0.85, 'task_success_rate': 0.92}
        result = await data_iteration_engine.optimize_data_pipeline(feedback_data)
        
        assert 'pipeline_adjustments' in result
        assert 'expected_improvement' in result
        assert 'applied_rules' in result
        
        assert isinstance(result['pipeline_adjustments'], list)
        assert isinstance(result['expected_improvement'], float)
        assert isinstance(result['applied_rules'], list)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])