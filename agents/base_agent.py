from datetime import datetime
import logging
from typing import Optional, Any, Dict

# Import for agent communication (will be set by orchestrator)
try:
    from core.agent_communication import AgentMessage, MessageType
except ImportError:
    AgentMessage = None
    MessageType = None


class BaseAgent:
    """Base class for all agents with communication capabilities."""

    def __init__(self, name, graph_memory, role):
        """Initialize the agent.

        Args:
            name: The name of the agent.
            graph_memory: The graph memory instance (can be None for testing).
            role: The role of the agent.
        """
        self.name = name
        self.graph_memory = graph_memory
        self.role = role

        # Only create agent ID if graph_memory is available
        if graph_memory is not None:
            self.agent_id = self.graph_memory.create_agent(
                {
                    "agent_id": f"agent_{role}_{datetime.now().timestamp()}",
                    "role": role,
                    "status": "initialized",
                }
            )
        else:
            # For testing without graph_memory
            self.agent_id = f"agent_{role}_{datetime.now().timestamp()}"
        self.logger = logging.getLogger(name)

        # Communication bus (set by orchestrator)
        self.communication_bus: Optional[Any] = None

    def log(self, message):
        self.logger.info(f"[{self.role}] {message}")

    def update_status(self, status):
        self.graph_memory.update_agent_status(self.agent_id, status)

    def set_communication_bus(self, bus: Any):
        """Set the communication bus for inter-agent messaging.

        Args:
            bus: AgentCommunicationBus instance
        """
        self.communication_bus = bus
        self.logger.info(f"[{self.name}] Communication bus connected")

    async def handle_message(self, message: Any) -> Dict[str, Any]:
        """Handle incoming message from another agent.

        Args:
            message: AgentMessage instance

        Returns:
            Response dictionary
        """
        if not AgentMessage or not MessageType:
            self.logger.warning(f"[{self.name}] Communication not available")
            return {"error": "Communication not available"}

        self.logger.info(
            f"[{self.name}] Received {message.message_type.value} from {message.from_agent}"
        )

        # Route to appropriate handler
        if message.message_type == MessageType.REQUEST_DATA:
            return await self._handle_data_request(message.payload)
        elif message.message_type == MessageType.TASK_COMPLETE:
            return await self._handle_task_completion(message.payload)
        elif message.message_type == MessageType.NEEDS_HELP:
            return await self._handle_help_request(message.payload)
        elif message.message_type == MessageType.STATUS_UPDATE:
            return await self._handle_status_update(message.payload)
        else:
            return await self._handle_unknown_message(message)

    async def _handle_data_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data request from another agent.

        Args:
            payload: Request payload

        Returns:
            Response with requested data
        """
        # Subclasses can override
        return {"status": "not_implemented", "data": None}

    async def _handle_task_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task completion notification.

        Args:
            payload: Completion details

        Returns:
            Acknowledgment
        """
        self.logger.info(f"[{self.name}] Task completed: {payload.get('task_id')}")
        return {"status": "acknowledged"}

    async def _handle_help_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help request from another agent.

        Args:
            payload: Help request details

        Returns:
            Help response
        """
        # Subclasses can override
        return {"status": "not_implemented", "help": None}

    async def _handle_status_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status update from another agent.

        Args:
            payload: Status update details

        Returns:
            Acknowledgment
        """
        self.logger.debug(f"[{self.name}] Status update received: {payload}")
        return {"status": "acknowledged"}

    async def _handle_unknown_message(self, message: Any) -> Dict[str, Any]:
        """Handle unknown message type.

        Args:
            message: Unknown message

        Returns:
            Error response
        """
        self.logger.warning(
            f"[{self.name}] Unknown message type: {message.message_type.value}"
        )
        return {"error": "unknown_message_type", "type": message.message_type.value}

    async def send_to_agent(
        self,
        to_agent: str,
        message_type: Any,
        payload: Dict[str, Any],
        requires_response: bool = False,
    ) -> Optional[Any]:
        """Send message to another agent.

        Args:
            to_agent: Target agent name
            message_type: MessageType enum value
            payload: Message payload
            requires_response: Whether to wait for response

        Returns:
            Response if requires_response=True, else None
        """
        if not self.communication_bus:
            self.logger.warning(f"[{self.name}] No communication bus available")
            return None

        if not AgentMessage:
            self.logger.warning(f"[{self.name}] Communication not available")
            return None

        message = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            requires_response=requires_response,
        )

        try:
            response = await self.communication_bus.send_message(message)
            return response
        except Exception as e:
            self.logger.error(f"[{self.name}] Error sending message: {e}")
            return None

    def run(self):
        raise NotImplementedError("Subclasses must implement `run()`")
