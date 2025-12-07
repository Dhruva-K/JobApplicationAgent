"""
Agent Communication System - Message-based inter-agent communication.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages agents can exchange."""

    REQUEST_DATA = "request_data"
    RESPONSE_DATA = "response_data"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    NEEDS_HELP = "needs_help"
    STATUS_UPDATE = "status_update"
    NOTIFICATION = "notification"


@dataclass
class AgentMessage:
    """Standardized message format for agent-to-agent communication."""

    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: Dict[str, Any]
    requires_response: bool = False
    correlation_id: Optional[str] = None  # For tracking related messages
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate correlation_id if needed."""
        if self.requires_response and self.correlation_id is None:
            import uuid

            self.correlation_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "requires_response": self.requires_response,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create message from dictionary."""
        return cls(
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            message_type=MessageType(data["message_type"]),
            payload=data["payload"],
            requires_response=data.get("requires_response", False),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class AgentCommunicationBus:
    """Message bus for routing messages between agents."""

    def __init__(self):
        """Initialize communication bus."""
        self.agent_registry: Dict[str, Any] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[str, Callable] = {}
        self.message_history: list = []
        self.max_history = 1000
        self._running = False

        logger.info("[CommunicationBus] Initialized")

    def register_agent(self, agent_name: str, agent: Any):
        """Register agent to receive messages.

        Args:
            agent_name: Unique name for the agent
            agent: Agent instance with handle_message method
        """
        if agent_name in self.agent_registry:
            logger.warning(
                f"[CommunicationBus] Agent {agent_name} already registered, overwriting"
            )

        self.agent_registry[agent_name] = agent
        logger.info(f"[CommunicationBus] Registered agent: {agent_name}")

    def unregister_agent(self, agent_name: str):
        """Remove agent from registry.

        Args:
            agent_name: Name of agent to remove
        """
        if agent_name in self.agent_registry:
            del self.agent_registry[agent_name]
            logger.info(f"[CommunicationBus] Unregistered agent: {agent_name}")

    async def send_message(
        self, message: AgentMessage, timeout: Optional[float] = 30.0
    ) -> Optional[Any]:
        """Send message to target agent.

        Args:
            message: AgentMessage to send
            timeout: Timeout in seconds for response (if required)

        Returns:
            Response from target agent if requires_response=True, else None
        """
        # Validate target agent exists
        if message.to_agent not in self.agent_registry:
            logger.error(
                f"[CommunicationBus] Target agent not found: {message.to_agent}"
            )
            raise ValueError(f"Agent {message.to_agent} not registered")

        # Log message
        self._log_message(message)

        # Get target agent
        target_agent = self.agent_registry[message.to_agent]

        logger.info(
            f"[CommunicationBus] Sending {message.message_type.value} "
            f"from {message.from_agent} to {message.to_agent}"
        )

        try:
            # Send message to agent
            if message.requires_response:
                # Wait for response with timeout
                response = await asyncio.wait_for(
                    target_agent.handle_message(message), timeout=timeout
                )
                logger.info(
                    f"[CommunicationBus] Received response from {message.to_agent}"
                )
                return response
            else:
                # Fire and forget
                asyncio.create_task(target_agent.handle_message(message))
                return None

        except asyncio.TimeoutError:
            logger.error(
                f"[CommunicationBus] Timeout waiting for response from {message.to_agent}"
            )
            raise
        except Exception as e:
            logger.error(
                f"[CommunicationBus] Error sending message to {message.to_agent}: {e}",
                exc_info=True,
            )
            raise

    async def broadcast(
        self, message: AgentMessage, exclude_sender: bool = True
    ) -> Dict[str, Any]:
        """Broadcast message to all registered agents.

        Args:
            message: AgentMessage to broadcast
            exclude_sender: If True, don't send to message.from_agent

        Returns:
            Dictionary mapping agent names to their responses
        """
        logger.info(
            f"[CommunicationBus] Broadcasting {message.message_type.value} "
            f"from {message.from_agent}"
        )

        responses = {}
        tasks = []

        for agent_name, agent in self.agent_registry.items():
            # Skip sender if requested
            if exclude_sender and agent_name == message.from_agent:
                continue

            # Create message copy for each recipient
            agent_message = AgentMessage(
                from_agent=message.from_agent,
                to_agent=agent_name,
                message_type=message.message_type,
                payload=message.payload,
                requires_response=message.requires_response,
                correlation_id=message.correlation_id,
                metadata=message.metadata,
            )

            # Send to agent
            task = asyncio.create_task(agent.handle_message(agent_message))
            tasks.append((agent_name, task))

        # Wait for all responses
        for agent_name, task in tasks:
            try:
                response = await task
                responses[agent_name] = response
            except Exception as e:
                logger.error(
                    f"[CommunicationBus] Error broadcasting to {agent_name}: {e}"
                )
                responses[agent_name] = {"error": str(e)}

        return responses

    def _log_message(self, message: AgentMessage):
        """Log message to history.

        Args:
            message: Message to log
        """
        self.message_history.append(message.to_dict())

        # Maintain max history size
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history :]

    def get_message_history(
        self, agent_name: Optional[str] = None, limit: int = 100
    ) -> list:
        """Get message history.

        Args:
            agent_name: Filter by agent (sent or received), None for all
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        if agent_name:
            filtered = [
                msg
                for msg in self.message_history
                if msg["from_agent"] == agent_name or msg["to_agent"] == agent_name
            ]
            return filtered[-limit:]
        else:
            return self.message_history[-limit:]

    def get_agent_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics for each agent.

        Returns:
            Dictionary mapping agent names to stats (messages sent/received)
        """
        stats = {}

        for agent_name in self.agent_registry.keys():
            sent = sum(
                1 for msg in self.message_history if msg["from_agent"] == agent_name
            )
            received = sum(
                1 for msg in self.message_history if msg["to_agent"] == agent_name
            )

            stats[agent_name] = {
                "messages_sent": sent,
                "messages_received": received,
                "total": sent + received,
            }

        return stats

    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()
        logger.info("[CommunicationBus] Message history cleared")

    def list_agents(self) -> list:
        """Get list of registered agent names.

        Returns:
            List of agent names
        """
        return list(self.agent_registry.keys())
