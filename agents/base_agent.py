from datetime import datetime
import logging


class BaseAgent:
    """Base class for all agents."""

    def __init__(self, name, graph_memory, role):
        """Initialize the agent.

        Args:
            name: The name of the agent.
            graph_memory: The graph memory instance.
            role: The role of the agent.
        """
        self.name = name
        self.graph_memory = graph_memory
        self.role = role
        self.agent_id = self.graph_memory.create_agent(
            {
                "agent_id": f"agent_{role}_{datetime.now().timestamp()}",
                "role": role,
                "status": "initialized",
            }
        )
        self.logger = logging.getLogger(name)

    def log(self, message):
        self.logger.info(f"[{self.role}] {message}")

    def update_status(self, status):
        self.graph_memory.update_agent_status(self.agent_id, status)

    def run(self):
        raise NotImplementedError("Subclasses must implement `run()`")
