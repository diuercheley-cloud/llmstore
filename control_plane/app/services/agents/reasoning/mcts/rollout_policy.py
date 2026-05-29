# Owner: agent-platform
import random
from typing import List, Dict, Any

class RolloutPolicy:
    """
    Defines how the agent chooses actions during the simulation phase of MCTS.
    """
    def choose_action(self, state: Dict[str, Any], possible_actions: List[str]) -> str:
        """
        Uses a heuristic or random choice to simulate a path.
        """
        # In a real implementation, this might use a smaller LLM or a greedy heuristic
        if not possible_actions:
            return "stop"
        return random.choice(possible_actions)
