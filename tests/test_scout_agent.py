"""
Unit tests for Scout Agent.
"""

import pytest
from unittest.mock import Mock, patch
from agents.scout_agent import ScoutAgent
from graph.memory import GraphMemory
from core.config import Config


@pytest.fixture
def mock_graph_memory():
    """Create a mock GraphMemory instance."""
    return Mock(spec=GraphMemory)


@pytest.fixture
def mock_config():
    """Create a mock Config instance."""
    config = Mock(spec=Config)
    config.get_job_api_config.return_value = {
        "api_key": "test_key",
        "base_url": "https://test.api.com"
    }
    return config


@pytest.fixture
def scout_agent(mock_graph_memory, mock_config):
    """Create a ScoutAgent instance."""
    return ScoutAgent(mock_graph_memory, mock_config)


def test_scout_agent_initialization(scout_agent):
    """Test ScoutAgent initialization."""
    assert scout_agent is not None
    assert scout_agent.graph_memory is not None
    assert scout_agent.config is not None


@patch('agents.scout_agent.requests.get')
def test_search_jobs_jsearch(mock_get, scout_agent):
    """Test job search using JSearch API."""
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {
                "job_id": "test_job_1",
                "job_title": "Software Engineer",
                "employer_name": "Test Company",
                "job_description": "Test description",
                "job_city": "Remote"
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    # Test search
    jobs = scout_agent._search_jsearch("software engineer", None, None, 10)
    
    assert len(jobs) > 0
    assert jobs[0]["title"] == "Software Engineer"


def test_normalize_jsearch_job(scout_agent):
    """Test JSearch job normalization."""
    job_data = {
        "job_id": "test_123",
        "job_title": "Software Engineer",
        "employer_name": "Test Company",
        "job_description": "Test description",
        "job_city": "Remote"
    }
    
    normalized = scout_agent._normalize_jsearch_job(job_data)
    
    assert normalized is not None
    assert normalized["title"] == "Software Engineer"
    assert normalized["job_id"] == "test_123"


def test_store_jobs(scout_agent, mock_graph_memory):
    """Test storing jobs in graph."""
    jobs = [
        {
            "job_id": "test_1",
            "title": "Test Job",
            "company_id": "comp_1",
            "company_name": "Test Company"
        }
    ]
    
    mock_graph_memory.create_job.return_value = "test_1"
    mock_graph_memory.create_company.return_value = "comp_1"
    
    stored_ids = scout_agent.store_jobs(jobs)
    
    assert len(stored_ids) == 1
    assert stored_ids[0] == "test_1"

