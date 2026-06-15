# Owner: agent-platform
import math
from typing import Any, Optional


class StateNode:
    """
    Represents a node in the MCTS search tree.
    """

    def __init__(
        self, state: dict[str, Any], parent: Optional["StateNode"] = None, action: str | None = None
    ):
        self.state = state
        self.parent = parent
        self.action = action  # The action that led to this state

        self.children: list[StateNode] = []
        self.visits = 0
        self.total_value = 0.0

        # Possible actions from this state that haven't been expanded yet
        self.untried_actions: list[str] = []

    @property
    def avg_value(self) -> float:
        return self.total_value / self.visits if self.visits > 0 else 0.0

    def uct_score(self, exploration_weight: float = 1.41) -> float:
        """
        Upper Confidence Bound applied to Trees (UCT).
        """
        if self.visits == 0:
            return float("inf")

        return self.avg_value + exploration_weight * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

    def select_child(self) -> "StateNode":
        """
        Selects the child with the highest UCT score.
        """
        return max(self.children, key=lambda c: c.uct_score())

    def update(self, value: float):
        """
        Updates node statistics.
        """
        self.visits += 1
        self.total_value += value
