"""
Tests for AgentCommunicationBus and AgentMessage.
"""

import pytest
import asyncio
from datetime import datetime
from core.agent_communication import AgentMessage, MessageType, AgentCommunicationBus
from agents.base_agent import BaseAgent


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, name):
        super().__init__(name=name, graph_memory=None, role="test")
        self.received_messages = []

    async def handle_message(self, message: AgentMessage):
        """Store received messages."""
        self.received_messages.append(message)

        # Send response for REQUEST_DATA
        if message.message_type == MessageType.REQUEST_DATA:
            await self.send_to_agent(
                message.from_agent,
                MessageType.RESPONSE_DATA,
                {"result": "test_response"},
                requires_response=False,
            )

    def run(self):
        pass


class TestAgentMessage:
    """Test AgentMessage dataclass."""

    def test_message_creation(self):
        """Test basic message creation."""
        message = AgentMessage(
            from_agent="agent1",
            to_agent="agent2",
            message_type=MessageType.REQUEST_DATA,
            payload={"key": "value"},
        )

        assert message.from_agent == "agent1"
        assert message.to_agent == "agent2"
        assert message.message_type == MessageType.REQUEST_DATA
        assert message.payload == {"key": "value"}
        assert isinstance(message.timestamp, datetime)
        assert not message.requires_response

    def test_message_with_response(self):
        """Test message requiring response."""
        message = AgentMessage(
            from_agent="agent1",
            to_agent="agent2",
            message_type=MessageType.REQUEST_DATA,
            payload={},
            requires_response=True,
        )

        assert message.requires_response
        assert message.correlation_id is not None

    def test_message_to_dict(self):
        """Test message serialization."""
        message = AgentMessage(
            from_agent="agent1",
            to_agent="agent2",
            message_type=MessageType.NOTIFICATION,
            payload={"text": "hello"},
        )

        data = message.to_dict()

        assert data["from_agent"] == "agent1"
        assert data["to_agent"] == "agent2"
        assert data["message_type"] == "notification"  # enum value is lowercase
        assert data["payload"] == {"text": "hello"}
        assert "timestamp" in data

    def test_message_from_dict(self):
        """Test message deserialization."""
        data = {
            "from_agent": "agent1",
            "to_agent": "agent2",
            "message_type": "request_data",  # lowercase
            "payload": {"key": "value"},
            "requires_response": True,
            "correlation_id": "test123",
            "timestamp": "2024-01-01T12:00:00",
            "metadata": {},
        }

        message = AgentMessage.from_dict(data)

        assert message.from_agent == "agent1"
        assert message.to_agent == "agent2"
        assert message.message_type == MessageType.REQUEST_DATA
        assert message.requires_response
        assert message.correlation_id == "test123"


class TestAgentCommunicationBus:
    """Test AgentCommunicationBus."""

    @pytest.fixture
    def bus(self):
        """Create a fresh communication bus."""
        return AgentCommunicationBus()

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        return MockAgent("test_agent")

    def test_register_agent(self, bus, mock_agent):
        """Test agent registration."""
        bus.register_agent("test_agent", mock_agent)

        assert "test_agent" in bus.agents
        assert bus.agents["test_agent"] == mock_agent

    def test_register_duplicate_agent(self, bus, mock_agent):
        """Test registering duplicate agent raises error."""
        bus.register_agent("test_agent", mock_agent)

        with pytest.raises(ValueError, match="already registered"):
            bus.register_agent("test_agent", mock_agent)

    @pytest.mark.asyncio
    async def test_send_message(self, bus):
        """Test sending message between agents."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")

        bus.register_agent("agent1", agent1)
        bus.register_agent("agent2", agent2)

        agent1.set_communication_bus(bus)
        agent2.set_communication_bus(bus)

        # Send message
        await agent1.send_to_agent(
            "agent2",
            MessageType.NOTIFICATION,
            {"text": "hello"},
            requires_response=False,
        )

        # Wait for delivery
        await asyncio.sleep(0.1)

        # Check agent2 received it
        assert len(agent2.received_messages) == 1
        assert agent2.received_messages[0].from_agent == "agent1"
        assert agent2.received_messages[0].payload["text"] == "hello"

    @pytest.mark.asyncio
    async def test_send_message_to_unregistered_agent(self, bus, mock_agent):
        """Test sending to unregistered agent raises error."""
        bus.register_agent("agent1", mock_agent)
        mock_agent.set_communication_bus(bus)

        with pytest.raises(ValueError, match="not registered"):
            await mock_agent.send_to_agent(
                "nonexistent", MessageType.NOTIFICATION, {}, requires_response=False
            )

    @pytest.mark.asyncio
    async def test_broadcast(self, bus):
        """Test broadcasting to all agents."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")
        agent3 = MockAgent("agent3")

        for name, agent in [("agent1", agent1), ("agent2", agent2), ("agent3", agent3)]:
            bus.register_agent(name, agent)
            agent.set_communication_bus(bus)

        # Broadcast from agent1
        message = AgentMessage(
            from_agent="agent1",
            to_agent="broadcast",
            message_type=MessageType.NOTIFICATION,
            payload={"text": "broadcast_test"},
        )

        await bus.broadcast(message, exclude_sender=True)

        # Wait for delivery
        await asyncio.sleep(0.1)

        # agent1 should not receive (excluded)
        assert len(agent1.received_messages) == 0

        # agent2 and agent3 should receive
        assert len(agent2.received_messages) == 1
        assert len(agent3.received_messages) == 1

    def test_message_history(self, bus):
        """Test message history tracking."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")

        bus.register_agent("agent1", agent1)
        bus.register_agent("agent2", agent2)

        message = AgentMessage(
            from_agent="agent1",
            to_agent="agent2",
            message_type=MessageType.NOTIFICATION,
            payload={},
        )

        # Record message
        bus._record_message(message)

        # Check history
        history = bus.get_message_history("agent1")
        assert len(history) == 1
        assert history[0] == message

    def test_message_history_limit(self, bus):
        """Test message history has max size."""
        agent = MockAgent("agent1")
        bus.register_agent("agent1", agent)

        # Send 1100 messages (exceeds max 1000)
        for i in range(1100):
            message = AgentMessage(
                from_agent="agent1",
                to_agent="agent2",
                message_type=MessageType.NOTIFICATION,
                payload={"index": i},
            )
            bus._record_message(message)

        # Should only keep last 1000
        history = bus.get_message_history("agent1")
        assert len(history) == 1000
        assert history[-1].payload["index"] == 1099

    def test_agent_statistics(self, bus):
        """Test agent statistics tracking."""
        agent1 = MockAgent("agent1")
        bus.register_agent("agent1", agent1)

        # Send some messages
        for i in range(5):
            message = AgentMessage(
                from_agent="agent1",
                to_agent="agent2",
                message_type=MessageType.NOTIFICATION,
                payload={},
            )
            bus._record_message(message)

        # Get stats
        stats = bus.get_agent_stats("agent1")

        assert stats["total_sent"] == 5
        assert stats["total_received"] == 0
        assert "last_message_time" in stats

    def test_clear_history(self, bus):
        """Test clearing message history."""
        agent = MockAgent("agent1")
        bus.register_agent("agent1", agent)

        # Add messages
        for i in range(10):
            message = AgentMessage(
                from_agent="agent1",
                to_agent="agent2",
                message_type=MessageType.NOTIFICATION,
                payload={},
            )
            bus._record_message(message)

        # Clear
        bus.clear_history()

        # Check empty
        history = bus.get_message_history("agent1")
        assert len(history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
