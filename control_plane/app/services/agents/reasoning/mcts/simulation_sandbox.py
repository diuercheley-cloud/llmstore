# Owner: agent-platform
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SimulationSandbox:
    """
    Simulates tool calls and state transitions without real-world side effects.
    """

    def __init__(self, settings):
        self.settings = settings

    async def step(self, state: dict[str, Any], action: str) -> tuple[dict[str, Any], list[str]]:
        """
        Calculates the next state and possible actions after taking 'action'.
        """
        # Mock transition logic
        next_state = state.copy()
        next_state["steps"] = next_state.get("steps", 0) + 1

        # In a real implementation, this would use a model to predict tool results
        # or use a real sandbox (gVisor/Firecracker) with a 'read-only' or 'transactional' mode.

        possible_next_actions = ["tool_a", "tool_b", "final_answer"]

        if action == "final_answer":
            next_state["goal_achieved"] = True
            possible_next_actions = []

        return next_state, possible_next_actions
