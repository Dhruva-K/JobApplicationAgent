"""
Unit tests for Extractor Agent.
"""

import pytest
from unittest.mock import Mock
from agents.extractor_agent import ExtractorAgent
from graph.memory import GraphMemory
from llm.llama_client import LLMClient


@pytest.fixture
def mock_graph_memory():
    """Create a mock GraphMemory instance."""
    return Mock(spec=GraphMemory)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLMClient instance."""
    return Mock(spec=LLMClient)


@pytest.fixture
def extractor_agent(mock_graph_memory, mock_llm_client):
    """Create an ExtractorAgent instance."""
    return ExtractorAgent(mock_graph_memory, mock_llm_client)


def test_extractor_agent_initialization(extractor_agent):
    """Test ExtractorAgent initialization."""
    assert extractor_agent is not None
    assert extractor_agent.graph_memory is not None
    assert extractor_agent.llm_client is not None


def test_extract_job_info(extractor_agent, mock_graph_memory, mock_llm_client):
    """Test job information extraction."""
    # Mock job data
    mock_graph_memory.get_job.return_value = {
        "job_id": "test_job",
        "description": "We are looking for a Python developer with 3+ years of experience."
    }
    
    # Mock LLM response
    mock_llm_client.generate_json.return_value = {
        "title": "Python Developer",
        "required_skills": ["Python", "Django"],
        "experience_level": "mid",
        "education_required": "Bachelor's"
    }
    
    # Mock skill creation
    mock_graph_memory.create_skill.return_value = "skill_123"
    
    result = extractor_agent.extract_job_info("test_job")
    
    assert result is not None
    assert "required_skills" in result


def test_extract_skills_only(extractor_agent, mock_llm_client):
    """Test skills-only extraction."""
    mock_llm_client.generate_json.return_value = ["Python", "Django", "PostgreSQL"]
    
    skills = extractor_agent.extract_skills_only("Looking for Python developer")
    
    assert isinstance(skills, list)
    assert len(skills) > 0

