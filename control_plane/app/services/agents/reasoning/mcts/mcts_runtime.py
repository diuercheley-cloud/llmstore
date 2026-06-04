# Owner: agent-platform
import logging
import random
import time
from typing import Any, Dict, List

from app.core.config import get_settings

from .rollout_policy import RolloutPolicy
from .simulation_sandbox import SimulationSandbox
from .state_node import StateNode
from .value_estimator import ValueEstimator

logger = logging.getLogger(__name__)

class MCTSRuntime:
    def __init__(self):
        self.settings = get_settings()
        self.rollout_policy = RolloutPolicy()
        self.value_estimator = ValueEstimator()
        self.sandbox = SimulationSandbox(self.settings)

    async def run_search(
        self, 
        initial_state: Dict[str, Any], 
        possible_actions: List[str],
        max_rollouts: int = 50,
        max_depth: int = 10,
        max_time_seconds: float = 5.0
    ) -> str:
        """
        Executes Monte Carlo Tree Search to find the best next action.
        """
        if not self.settings.agent_mcts_reasoning_enabled:
            raise PermissionError("MCTS Reasoning is disabled.")

        root = StateNode(initial_state)
        root.untried_actions = possible_actions
        
        start_time = time.time()
        
        for i in range(max_rollouts):
            if (time.time() - start_time) > max_time_seconds:
                logger.warning("MCTS Search timed out.")
                break
                
            # 1. Selection
            node = root
            depth = 0
            while not node.untried_actions and node.children and depth < max_depth:
                node = node.select_child()
                depth += 1
                
            # 2. Expansion
            if node.untried_actions and depth < max_depth:
                action = node.untried_actions.pop()
                next_state, next_possible_actions = await self.sandbox.step(node.state, action)
                child = StateNode(next_state, parent=node, action=action)
                child.untried_actions = next_possible_actions
                node.children.append(child)
                node = child
                
            # 3. Simulation (Rollout)
            rollout_state = node.state
            rollout_depth = depth
            while rollout_depth < max_depth:
                # Need possible actions for rollout
                # For simplicity, we just use a fixed list or mock
                mock_actions = ["tool_a", "tool_b", "final_answer"]
                action = self.rollout_policy.choose_action(rollout_state, mock_actions)
                if action == "stop" or action == "final_answer":
                    break
                rollout_state, _ = await self.sandbox.step(rollout_state, action)
                rollout_depth += 1
                
            # 4. Backpropagation
            reward = self.value_estimator.estimate(rollout_state, initial_state)
            while node:
                node.update(reward)
                node = node.parent

        # Return the action of the child with most visits
        if not root.children:
             return random.choice(possible_actions) if possible_actions else "stop"
             
        best_child = max(root.children, key=lambda c: c.visits)
        logger.info(f"MCTS selected action {best_child.action} after {i+1} rollouts. Score: {best_child.avg_value}")
        
        return best_child.action
