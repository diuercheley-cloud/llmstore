import logging
from typing import Any, Dict, List

from app.models.agents import AgentEvalFailure

logger = logging.getLogger(__name__)

class PolicyOptimizer:
    def optimize_policy(self, current_policy: Dict[str, Any], failures: List[AgentEvalFailure]) -> Dict[str, Any]:
        """
        Generates policy rule improvements to avoid security/policy violations or handle denials.
        """
        optimized_policy = dict(current_policy) if current_policy else {}

        # Default rules structure if empty
        if "denied_tools" not in optimized_policy:
            optimized_policy["denied_tools"] = []
        if "approval_tools" not in optimized_policy:
            optimized_policy["approval_tools"] = []

        # Analyze safety failures
        for f in failures:
            if f.failure_type in ["safety_failure", "secret_leak"]:
                # If a secret leaked or safety issue occurred, deny the offending tool or require approval
                offending_tool = f.details.get("tool_name")
                if offending_tool:
                    if offending_tool not in optimized_policy["approval_tools"]:
                        optimized_policy["approval_tools"].append(offending_tool)
                        logger.info(f"Adding '{offending_tool}' to approval rules to prevent safety failure.")

        return optimized_policy
