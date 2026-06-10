# Owner: agent-platform
import logging
from typing import Any, Dict, Optional

from app.models.agents.agent_workflows import AgentWorkflowRun

logger = logging.getLogger(__name__)

class WorkflowBranchingManager:
    """
    Handles complex branching conditions for agent workflows.
    Evaluates context, results, and external signals to determine the next path.
    """
    
    def __init__(self, run: AgentWorkflowRun):
        self.run = run

    def evaluate_condition(self, condition_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluates a condition based on the provided configuration.
        config: {
            "type": "policy_result|tool_result|memory_value|eval_score|human_approval",
            "target": "name_of_policy_or_tool",
            "operator": "eq|gt|lt|contains",
            "value": expected_value
        }
        """
        cond_type = condition_config.get("type")
        target = condition_config.get("target")
        operator = condition_config.get("operator", "eq")
        expected_value = condition_config.get("value")

        actual_value = None

        if cond_type == "policy_result":
            actual_value = context.get("policies", {}).get(target, {}).get("result")
        elif cond_type == "tool_result":
            actual_value = context.get("tools", {}).get(target, {}).get("output")
        elif cond_type == "memory_value":
            actual_value = context.get("memory", {}).get(target)
        elif cond_type == "eval_score":
            actual_value = context.get("evals", {}).get(target, {}).get("score")
        elif cond_type == "human_approval":
            actual_value = context.get("approvals", {}).get(target, {}).get("status")
        else:
            logger.warning(f"Unknown condition type: {cond_type}")
            return False

        return self._compare(actual_value, operator, expected_value)

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        try:
            if operator == "eq":
                return actual == expected
            elif operator == "neq":
                return actual != expected
            elif operator == "gt":
                return actual > expected
            elif operator == "lt":
                return actual < expected
            elif operator == "gte":
                return actual >= expected
            elif operator == "lte":
                return actual <= expected
            elif operator == "contains":
                return expected in actual if actual else False
            elif operator == "exists":
                return actual is not None
            else:
                return False
        except Exception as e:
            logger.error(f"Error during comparison: {e}")
            return False

    def resolve_branch(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
        """
        For a 'condition' node, evaluates all branches and returns the key of the target node.
        node_config should contain 'branches': [{"condition": {...}, "target": "node_key"}]
        """
        branches = node_config.get("branches", [])
        for branch in branches:
            condition = branch.get("condition")
            if not condition or self.evaluate_condition(condition, context):
                return branch.get("target")
        
        return node_config.get("default_target")
