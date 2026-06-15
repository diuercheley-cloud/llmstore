# Owner: agent-platform
from typing import Any


class ValueEstimator:
    """
    Estimates the value (reward) of a final state in a simulation.
    """

    def estimate(self, state: dict[str, Any], context: dict[str, Any]) -> float:
        """
        Scores the state between 0.0 (failure) and 1.0 (success).
        """
        # Heuristic example
        score = 0.5
        if state.get("goal_achieved"):
            score = 1.0
        elif state.get("error_occurred"):
            score = 0.0

        # Penalize cost/steps
        score -= state.get("steps", 0) * 0.01

        return max(0.0, min(1.0, score))
