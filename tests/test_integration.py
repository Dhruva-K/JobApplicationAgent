"""
Integration tests for the Job Application Agent system.
"""

import pytest
from unittest.mock import Mock, patch
from workflow.job_application_graph import JobApplicationGraph
from core.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get_neo4j_config.return_value = {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "test",
        "database": "neo4j"
    }
    config.get_llm_config.return_value = {
        "provider": "ollama",
        "model_name": "llama3:8b",
        "base_url": "http://localhost:11434",
        "temperature": 0.7,
        "max_tokens": 2048
    }
    config.get.return_value = {}
    config.get_job_api_config.return_value = {
        "api_key": "test_key",
        "base_url": "https://test.api.com"
    }
    return config


@patch('workflow.job_application_graph.GraphMemory')
@patch('workflow.job_application_graph.create_llm_client')
@patch('workflow.job_application_graph.EmbeddingGenerator')
def test_workflow_initialization(mock_embedding, mock_llm, mock_graph, mock_config):
    """Test workflow initialization."""
    workflow = JobApplicationGraph(mock_config)
    
    assert workflow is not None
    assert workflow.scout_agent is not None
    assert workflow.extractor_agent is not None
    assert workflow.matcher_agent is not None
    assert workflow.writer_agent is not None
    assert workflow.tracker_agent is not None


@patch('workflow.job_application_graph.GraphMemory')
@patch('workflow.job_application_graph.create_llm_client')
@patch('workflow.job_application_graph.EmbeddingGenerator')
def test_search_jobs(mock_embedding, mock_llm, mock_graph, mock_config):
    """Test job search functionality."""
    workflow = JobApplicationGraph(mock_config)
    
    # Mock scout agent
    workflow.scout_agent.search_and_store = Mock(return_value=[
        {"job_id": "test1", "title": "Test Job"}
    ])
    
    jobs = workflow.search_jobs("software engineer")
    
    assert len(jobs) > 0
    assert jobs[0]["job_id"] == "test1"


@patch('workflow.job_application_graph.GraphMemory')
@patch('workflow.job_application_graph.create_llm_client')
@patch('workflow.job_application_graph.EmbeddingGenerator')
def test_get_matches(mock_embedding, mock_llm, mock_graph, mock_config):
    """Test job matching functionality."""
    workflow = JobApplicationGraph(mock_config)
    
    # Mock matcher agent
    workflow.matcher_agent.match_jobs = Mock(return_value=[
        {"job_id": "test1", "match_score": 0.9, "job": {"title": "Test Job"}}
    ])
    
    matches = workflow.get_matches("user1")
    
    assert len(matches) > 0
    assert matches[0]["match_score"] == 0.9

