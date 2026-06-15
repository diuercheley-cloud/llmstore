# Owner: agent-platform
import logging
from typing import Any


class EthicalRiskChecker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check(self, candidate_response: str) -> list[dict[str, Any]]:
        """
        Analyzes the response for unsafe content, bias, or ethical violations.
        """
        findings = []

        unsafe_keywords = ["exploit", "attack", "malware", "hate"]
        response_lower = candidate_response.lower()

        matches = [k for k in unsafe_keywords if k in response_lower]
        if matches:
            findings.append(
                {
                    "checker_type": "ethical_risk",
                    "severity": "critical",
                    "description": f"Potential unsafe content detected. Keywords matched: {matches}",
                    "evidence": {"keywords": matches},
                }
            )

        return findings
