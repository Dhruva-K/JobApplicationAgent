"""
Tests for ConversationState manager.
"""

import pytest
import time
from datetime import datetime, timedelta
from core.conversation_state import ConversationState, PipelineState


class TestConversationState:
    """Test ConversationState manager."""

    @pytest.fixture
    def state(self):
        """Create fresh ConversationState."""
        return ConversationState()

    def test_create_session(self, state):
        """Test session creation."""
        session_id = state.create_session("user123")

        assert session_id.startswith("session_user123_")
        assert "user123" in state.sessions
        assert state.sessions["user123"]["session_id"] == session_id

    def test_context_storage(self, state):
        """Test context save and retrieval."""
        state.create_session("user1")

        # Save context
        state.save_context("user1", "job_title", "Software Engineer")
        state.save_context("user1", "location", "San Francisco")

        # Retrieve
        assert state.get_context("user1", "job_title") == "Software Engineer"
        assert state.get_context("user1", "location") == "San Francisco"
        assert state.get_context("user1", "nonexistent") is None

    def test_clear_context(self, state):
        """Test clearing context."""
        state.create_session("user1")
        state.save_context("user1", "key1", "value1")
        state.save_context("user1", "key2", "value2")

        state.clear_context("user1")

        assert state.get_context("user1", "key1") is None
        assert state.get_context("user1", "key2") is None

    def test_pending_actions(self, state):
        """Test pending action management."""
        state.create_session("user1")

        # Set pending action
        state.set_pending_action("user1", "apply_to_jobs", {"job_ids": [1, 2, 3]})

        # Get pending action
        action = state.get_pending_action("user1")

        assert action is not None
        assert action["action_type"] == "apply_to_jobs"
        assert action["action_data"] == {"job_ids": [1, 2, 3]}
        assert "timestamp" in action

        # Clear
        state.clear_pending_action("user1")
        assert state.get_pending_action("user1") is None

    def test_pending_action_expiration(self, state):
        """Test pending actions expire after timeout."""
        state.create_session("user1")

        # Set action with 1 second expiration
        state.set_pending_action("user1", "test", {}, expires_in_seconds=1)

        # Should exist immediately
        assert state.get_pending_action("user1") is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be gone
        assert state.get_pending_action("user1") is None

    def test_pipeline_state(self, state):
        """Test pipeline state tracking."""
        state.create_session("user1")

        # Should start as IDLE
        assert state.get_pipeline_state("user1") == PipelineState.IDLE

        # Change state
        state.set_pipeline_state("user1", PipelineState.SEARCHING)
        assert state.get_pipeline_state("user1") == PipelineState.SEARCHING

        state.set_pipeline_state("user1", PipelineState.MATCHING)
        assert state.get_pipeline_state("user1") == PipelineState.MATCHING

        state.set_pipeline_state("user1", PipelineState.COMPLETED)
        assert state.get_pipeline_state("user1") == PipelineState.COMPLETED

    def test_job_selection(self, state):
        """Test job selection storage."""
        state.create_session("user1")

        job_ids = ["job1", "job2", "job3"]
        state.save_job_selection("user1", job_ids)

        retrieved = state.get_job_selection("user1")
        assert retrieved == job_ids

    def test_search_criteria(self, state):
        """Test search criteria storage."""
        state.create_session("user1")

        criteria = {
            "keywords": ["python", "django"],
            "location": "Remote",
            "experience": "senior",
        }

        state.save_search_criteria("user1", criteria)

        retrieved = state.get_search_criteria("user1")
        assert retrieved == criteria

    def test_conversation_history(self, state):
        """Test conversation history tracking."""
        state.create_session("user1")

        # Add messages
        state.add_to_history("user1", "Hello", role="user")
        state.add_to_history("user1", "Hi there!", role="assistant")
        state.add_to_history("user1", "Find jobs", role="user")

        # Get history
        history = state.get_history("user1")

        assert len(history) == 3
        assert history[0]["message"] == "Hello"
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert "timestamp" in history[0]

    def test_history_limit(self, state):
        """Test history has max size (100 messages)."""
        state.create_session("user1")

        # Add 150 messages
        for i in range(150):
            state.add_to_history("user1", f"Message {i}", role="user")

        # Should only keep last 100
        history = state.get_history("user1")
        assert len(history) == 100
        assert history[-1]["message"] == "Message 149"

    def test_message_count(self, state):
        """Test message counting."""
        state.create_session("user1")

        assert state.get_message_count("user1") == 0

        state.increment_message_count("user1")
        state.increment_message_count("user1")
        state.increment_message_count("user1")

        assert state.get_message_count("user1") == 3

    def test_session_info(self, state):
        """Test getting session info."""
        session_id = state.create_session("user1")

        # Add some data
        state.save_context("user1", "key", "value")
        state.set_pipeline_state("user1", PipelineState.SEARCHING)
        state.increment_message_count("user1")

        info = state.get_session_info("user1")

        assert info["session_id"] == session_id
        assert "created_at" in info
        assert info["message_count"] == 1
        assert info["pipeline_state"] == PipelineState.SEARCHING
        assert "has_pending_action" in info

    def test_cleanup_expired_sessions(self, state):
        """Test session cleanup."""
        # Create sessions
        state.create_session("user1")
        state.create_session("user2")

        # Manually set old timestamp for user1
        old_time = datetime.now() - timedelta(hours=25)
        state.sessions["user1"]["created_at"] = old_time

        # Cleanup
        state.cleanup_expired_sessions()

        # user1 should be gone, user2 should remain
        assert "user1" not in state.sessions
        assert "user2" in state.sessions

    def test_multiple_users(self, state):
        """Test multiple users with independent state."""
        state.create_session("user1")
        state.create_session("user2")

        # Set different data for each
        state.save_context("user1", "job", "Engineer")
        state.save_context("user2", "job", "Designer")

        state.set_pipeline_state("user1", PipelineState.SEARCHING)
        state.set_pipeline_state("user2", PipelineState.APPLYING)

        # Verify independence
        assert state.get_context("user1", "job") == "Engineer"
        assert state.get_context("user2", "job") == "Designer"

        assert state.get_pipeline_state("user1") == PipelineState.SEARCHING
        assert state.get_pipeline_state("user2") == PipelineState.APPLYING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
