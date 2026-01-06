"""
Base agent architecture for Trackit.

This module defines the foundation for all agents in the system.
It provides a consistent interface and state management pattern that's
compatible with LangGraph for future multi-agent expansion.

Author: Trackit Development
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    This class provides:
    - Consistent initialization pattern
    - State management (compatible with LangGraph)
    - Standard execute interface
    - Logging and debugging support

    All agents should inherit from this class and implement
    the execute() method.

    Example:
        >>> class MyAgent(BaseAgent):
        ...     def execute(self, **kwargs):
        ...         return {"status": "success"}
    """

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the agent.

        Args:
            name: Agent name (e.g., "RecordingAgent", "QueryAgent")
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}

        # State management for LangGraph compatibility
        # This allows agents to participate in multi-agent workflows
        self.state = {}

        # Execution statistics
        self.execution_count = 0
        self.last_execution = None

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's primary function.

        This method must be implemented by all agent subclasses.
        It should accept keyword arguments and return a result dictionary.

        Args:
            **kwargs: Agent-specific inputs

        Returns:
            Dictionary with:
                - success: Boolean indicating success/failure
                - data: Result data (if successful)
                - error: Error message (if failed)
                - metadata: Additional metadata

        Example:
            >>> def execute(self, user_input: str) -> Dict[str, Any]:
            ...     try:
            ...         result = process_input(user_input)
            ...         return {"success": True, "data": result}
            ...     except Exception as e:
            ...         return {"success": False, "error": str(e)}
        """
        pass

    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        Update the agent's internal state.

        This is used for multi-agent workflows where agents
        need to share state through the workflow.

        Args:
            state_update: Dictionary of state updates

        Example:
            >>> agent.update_state({"user_id": 123, "context": "morning"})
        """
        self.state.update(state_update)

    def get_state(self) -> Dict[str, Any]:
        """
        Get the agent's current state.

        Returns:
            Copy of the agent's state dictionary
        """
        return self.state.copy()

    def reset_state(self) -> None:
        """Reset the agent's state to empty."""
        self.state = {}

    def log_execution(self) -> None:
        """Record execution time and count."""
        self.execution_count += 1
        self.last_execution = datetime.now()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent execution statistics.

        Returns:
            Dictionary with execution stats
        """
        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "state_keys": list(self.state.keys())
        }

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', executions={self.execution_count})"


class AgentState:
    """
    Shared state container for multi-agent workflows.

    This is compatible with LangGraph's TypedDict pattern and
    allows agents to pass data through a workflow.

    Example:
        >>> state = AgentState()
        >>> state.update({"user_input": "今天跑了5公里"})
        >>> state.update({"extracted_data": {...}})
        >>> print(state.data)
        {'user_input': '今天跑了5公里', 'extracted_data': {...}}
    """

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent state.

        Args:
            initial_data: Optional initial state data
        """
        self.data = initial_data or {}

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update state with new data.

        Args:
            updates: Dictionary of state updates
        """
        self.data.update(updates)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from state.

        Args:
            key: State key
            default: Default value if key not found

        Returns:
            Value from state or default
        """
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """
        Check if a key exists in state.

        Args:
            key: State key to check

        Returns:
            True if key exists, False otherwise
        """
        return key in self.data

    def to_dict(self) -> Dict[str, Any]:
        """
        Get the complete state as dictionary.

        Returns:
            Copy of state data
        """
        return self.data.copy()

    def clear(self) -> None:
        """Clear all state data."""
        self.data = {}

    def __repr__(self) -> str:
        """String representation of state."""
        return f"AgentState({self.data})"


# Helper functions for agent workflows
def create_agent_workflow(
    agents: list[BaseAgent],
    workflow_type: str = "sequential"
) -> Dict[str, Any]:
    """
    Create a workflow configuration for multiple agents.

    This is a simple workflow orchestrator. For complex workflows,
    consider using LangGraph (implemented in Week 4).

    Args:
        agents: List of agents to include in workflow
        workflow_type: Type of workflow ("sequential", "parallel", "conditional")

    Returns:
        Workflow configuration dictionary

    Example:
        >>> agents = [agent1, agent2, agent3]
        >>> workflow = create_agent_workflow(agents, "sequential")
        >>> print(workflow["type"])
        sequential
    """
    return {
        "type": workflow_type,
        "agents": [agent.name for agent in agents],
        "agent_objects": agents,
        "created_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test: Base agent functionality
    print("Testing BaseAgent...")
    print("=" * 60)

    class TestAgent(BaseAgent):
        def execute(self, message: str) -> Dict[str, Any]:
            self.log_execution()
            return {
                "success": True,
                "data": f"Processed: {message}",
                "agent": self.name
            }

    agent = TestAgent(name="TestAgent", config={"debug": True})

    # Test execution
    result = agent.execute(message="Hello")
    print(f"Result: {result}")

    # Test state management
    agent.update_state({"user_id": 123, "context": "test"})
    print(f"State: {agent.get_state()}")

    # Test statistics
    print(f"Stats: {agent.get_stats()}")
    print(f"Repr: {agent}")

    # Test AgentState
    print("\n" + "=" * 60)
    print("Testing AgentState...")
    print("=" * 60)

    state = AgentState({"user_input": "今天跑了5公里"})
    state.update({"extracted": {"category": "运动"}})

    print(f"State data: {state.to_dict()}")
    print(f"Has 'extracted': {state.has('extracted')}")
    print(f"Get 'user_input': {state.get('user_input')}")
