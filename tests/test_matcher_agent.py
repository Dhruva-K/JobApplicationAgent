"""
Unit tests for Matcher Agent.
"""

import pytest
from unittest.mock import Mock
from agents.matcher_agent import MatcherAgent
from graph.memory import GraphMemory
from llm.llama_client import LLMClient
from utils.embeddings import EmbeddingGenerator


@pytest.fixture
def mock_graph_memory():
    """Create a mock GraphMemory instance."""
    return Mock(spec=GraphMemory)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLMClient instance."""
    return Mock(spec=LLMClient)


@pytest.fixture
def mock_embedding_generator():
    """Create a mock EmbeddingGenerator instance."""
    return Mock(spec=EmbeddingGenerator)


@pytest.fixture
def matcher_agent(mock_graph_memory, mock_llm_client, mock_embedding_generator):
    """Create a MatcherAgent instance."""
    return MatcherAgent(mock_graph_memory, mock_llm_client, mock_embedding_generator)


def test_matcher_agent_initialization(matcher_agent):
    """Test MatcherAgent initialization."""
    assert matcher_agent is not None
    assert matcher_agent.graph_memory is not None
    assert matcher_agent.llm_client is not None
    assert matcher_agent.embedding_generator is not None


def test_calculate_match_score(matcher_agent, mock_embedding_generator):
    """Test match score calculation."""
    user_skills = ["Python", "Django", "PostgreSQL"]
    job_skills = ["Python", "Django", "React"]
    job = {"title": "Software Engineer"}
    
    mock_embedding_generator.similarity.return_value = 0.8
    
    score = matcher_agent._calculate_match_score(user_skills, job_skills, job, use_semantic=True)
    
    assert 0.0 <= score <= 1.0
    assert score > 0.5  # Should have some match


def test_get_matched_skills(matcher_agent):
    """Test getting matched skills."""
    user_skills = ["Python", "Django", "PostgreSQL"]
    job_skills = ["Python", "Django", "React"]
    
    matched = matcher_agent._get_matched_skills(user_skills, job_skills)
    
    assert len(matched) == 2
    assert "Python" in matched or "python" in [s.lower() for s in matched]


def test_get_missing_skills(matcher_agent):
    """Test getting missing skills."""
    user_skills = ["Python", "Django"]
    job_skills = ["Python", "Django", "React", "TypeScript"]
    
    missing = matcher_agent._get_missing_skills(user_skills, job_skills)
    
    assert len(missing) >= 1
    assert "React" in missing or "react" in [s.lower() for s in missing]

