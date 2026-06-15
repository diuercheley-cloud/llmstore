# Owner: agent-platform
import logging
from typing import Any


class PolicyDriftChecker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check(self, action: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Detects if the agent is deviating from its defined instructions or system policies.
        """
        findings = []

        # Check for high-risk actions without explicit approval in context
        is_high_risk = context.get("risk_level") == "high" or context.get("is_destructive", False)
        has_approval = context.get("human_approval_obtained", False)

        if is_high_risk and not has_approval:
            findings.append(
                {
                    "checker_type": "policy_drift",
                    "severity": "high",
                    "description": "High-risk tool execution attempted without explicit human approval.",
                    "evidence": {"action": action},
                }
            )

        return findings
