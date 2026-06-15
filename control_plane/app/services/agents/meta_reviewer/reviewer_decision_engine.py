# Owner: agent-platform
from typing import Any


class ReviewerDecisionEngine:
    def consolidate(self, findings: list[dict[str, Any]]) -> tuple[str, str]:
        """
        Consolidates findings into a final decision.
        """
        if not findings:
            return "allow", "No critical findings detected."

        max_severity = "low"
        severities = ["low", "medium", "high", "critical"]

        for f in findings:
            if severities.index(f["severity"]) > severities.index(max_severity):
                max_severity = f["severity"]

        if max_severity == "critical":
            return "block", "Critical ethical or security risk detected."
        elif max_severity == "high":
            return "require_human_approval", "High-severity policy or consistency issue detected."
        elif max_severity == "medium":
            return "require_revision", "Medium-severity consistency issue. Revision recommended."

        return "allow", "Low-severity findings detected. Proceeding with caution."
