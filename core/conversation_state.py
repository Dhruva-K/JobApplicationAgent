"""
Conversation State Management - Track context across multiple turns.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """States for different pipeline stages."""

    IDLE = "idle"
    SEARCHING = "searching"
    MATCHING = "matching"
    GENERATING_DOCS = "generating_docs"
    APPLYING = "applying"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    ERROR = "error"


class ConversationState:
    """Manage conversation context and pending actions."""

    def __init__(self):
        """Initialize conversation state manager."""
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
        self.pending_actions: Dict[str, Dict[str, Any]] = {}
        self.pipeline_states: Dict[str, PipelineState] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}

        logger.info("[ConversationState] Initialized")

    def create_session(self, user_id: str) -> str:
        """Create new session for user.

        Args:
            user_id: User identifier

        Returns:
            Session ID
        """
        session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.user_contexts[user_id] = {}
        self.pending_actions[user_id] = {}
        self.pipeline_states[user_id] = PipelineState.IDLE
        self.session_data[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
        }

        logger.info(
            f"[ConversationState] Created session {session_id} for user {user_id}"
        )
        return session_id

    def save_context(self, user_id: str, key: str, value: Any):
        """Save context value for user.

        Args:
            user_id: User identifier
            key: Context key
            value: Value to store
        """
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {}

        self.user_contexts[user_id][key] = value
        logger.debug(f"[ConversationState] Saved context for {user_id}: {key}")

    def get_context(self, user_id: str, key: str, default: Any = None) -> Any:
        """Retrieve context value for user.

        Args:
            user_id: User identifier
            key: Context key
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        return self.user_contexts.get(user_id, {}).get(key, default)

    def get_all_context(self, user_id: str) -> Dict[str, Any]:
        """Get all context for user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of all context values
        """
        return self.user_contexts.get(user_id, {})

    def clear_context(self, user_id: str, key: Optional[str] = None):
        """Clear context for user.

        Args:
            user_id: User identifier
            key: Specific key to clear, or None to clear all
        """
        if key:
            if user_id in self.user_contexts and key in self.user_contexts[user_id]:
                del self.user_contexts[user_id][key]
                logger.debug(f"[ConversationState] Cleared context {key} for {user_id}")
        else:
            if user_id in self.user_contexts:
                self.user_contexts[user_id].clear()
                logger.info(f"[ConversationState] Cleared all context for {user_id}")

    def set_pending_action(
        self,
        user_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        expires_in_seconds: Optional[int] = 3600,
    ):
        """Store action waiting for user confirmation.

        Args:
            user_id: User identifier
            action_type: Type of action (e.g., 'apply_to_jobs', 'send_email')
            action_data: Data needed to execute the action
            expires_in_seconds: Expiration time in seconds (default 1 hour)
        """
        if user_id not in self.pending_actions:
            self.pending_actions[user_id] = {}

        self.pending_actions[user_id] = {
            "action_type": action_type,
            "action_data": action_data,
            "created_at": datetime.now(),
            "expires_at": (
                datetime.now().timestamp() + expires_in_seconds
                if expires_in_seconds
                else None
            ),
        }

        logger.info(
            f"[ConversationState] Set pending action '{action_type}' for {user_id}"
        )

    def get_pending_action(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get pending action for user.

        Args:
            user_id: User identifier

        Returns:
            Pending action dictionary or None
        """
        action = self.pending_actions.get(user_id)

        if action:
            # Check if expired
            if (
                action.get("expires_at")
                and datetime.now().timestamp() > action["expires_at"]
            ):
                logger.info(f"[ConversationState] Pending action expired for {user_id}")
                self.clear_pending_action(user_id)
                return None

        return action

    def clear_pending_action(self, user_id: str):
        """Clear pending action for user.

        Args:
            user_id: User identifier
        """
        if user_id in self.pending_actions:
            del self.pending_actions[user_id]
            logger.info(f"[ConversationState] Cleared pending action for {user_id}")

    def set_pipeline_state(self, user_id: str, state: PipelineState):
        """Set current pipeline state for user.

        Args:
            user_id: User identifier
            state: Pipeline state
        """
        self.pipeline_states[user_id] = state
        logger.info(
            f"[ConversationState] Set pipeline state for {user_id}: {state.value}"
        )

    def get_pipeline_state(self, user_id: str) -> PipelineState:
        """Get current pipeline state for user.

        Args:
            user_id: User identifier

        Returns:
            Current pipeline state
        """
        return self.pipeline_states.get(user_id, PipelineState.IDLE)

    def add_to_history(
        self,
        user_id: str,
        message: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add message to conversation history.

        Args:
            user_id: User identifier
            message: Message content
            role: Role (user/assistant)
            metadata: Optional metadata
        """
        history_key = f"{user_id}_history"

        if history_key not in self.session_data:
            self.session_data[history_key] = []

        self.session_data[history_key].append(
            {
                "message": message,
                "role": role,
                "timestamp": datetime.now(),
                "metadata": metadata or {},
            }
        )

        # Keep only last 100 messages
        if len(self.session_data[history_key]) > 100:
            self.session_data[history_key] = self.session_data[history_key][-100:]

    def get_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for user.

        Args:
            user_id: User identifier
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        history_key = f"{user_id}_history"
        history = self.session_data.get(history_key, [])
        return history[-limit:]

    def save_job_selection(self, user_id: str, job_ids: List[str]):
        """Save selected jobs for user.

        Args:
            user_id: User identifier
            job_ids: List of selected job IDs
        """
        self.save_context(user_id, "selected_jobs", job_ids)
        self.save_context(user_id, "selection_time", datetime.now())
        logger.info(
            f"[ConversationState] Saved {len(job_ids)} selected jobs for {user_id}"
        )

    def get_job_selection(self, user_id: str) -> List[str]:
        """Get selected jobs for user.

        Args:
            user_id: User identifier

        Returns:
            List of job IDs
        """
        return self.get_context(user_id, "selected_jobs", [])

    def save_search_criteria(self, user_id: str, criteria: Dict[str, Any]):
        """Save search criteria for user.

        Args:
            user_id: User identifier
            criteria: Search criteria dictionary
        """
        self.save_context(user_id, "search_criteria", criteria)
        logger.info(f"[ConversationState] Saved search criteria for {user_id}")

    def get_search_criteria(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get search criteria for user.

        Args:
            user_id: User identifier

        Returns:
            Search criteria dictionary or None
        """
        return self.get_context(user_id, "search_criteria")

    def increment_message_count(self, user_id: str):
        """Increment message count for user session.

        Args:
            user_id: User identifier
        """
        # Find session for this user
        for session_id, data in self.session_data.items():
            if isinstance(data, dict) and data.get("user_id") == user_id:
                data["message_count"] = data.get("message_count", 0) + 1
                data["last_activity"] = datetime.now()
                return

        # No session found, create one
        self.create_session(user_id)

    def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for user.

        Args:
            user_id: User identifier

        Returns:
            Session info dictionary or None
        """
        for session_id, data in self.session_data.items():
            if data.get("user_id") == user_id:
                return {"session_id": session_id, **data}
        return None

    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up old sessions.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        now = datetime.now()
        expired = []

        for session_id, data in self.session_data.items():
            last_activity = data.get("last_activity")
            if last_activity:
                age_hours = (now - last_activity).total_seconds() / 3600
                if age_hours > max_age_hours:
                    expired.append(session_id)

        for session_id in expired:
            user_id = self.session_data[session_id].get("user_id")
            del self.session_data[session_id]

            # Clean up related data
            if user_id:
                self.clear_context(user_id)
                self.clear_pending_action(user_id)
                if user_id in self.pipeline_states:
                    del self.pipeline_states[user_id]

        if expired:
            logger.info(
                f"[ConversationState] Cleaned up {len(expired)} expired sessions"
            )
