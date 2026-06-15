from datetime import UTC, datetime
from typing import Any


class PolicyTraceBuilder:
    """
    Generates explainability traces for policy evaluation.
    Tracks matched rules, failed rules, enforcement path, and remediation hints.
    """

    def __init__(self, evaluation_id: str, bundle_id: str):
        self.evaluation_id = evaluation_id
        self.bundle_id = bundle_id
        self.matched_rules: list[str] = []
        self.failed_rules: list[str] = []
        self.enforcement_path: list[dict[str, Any]] = []
        self.remediation_hints: list[dict[str, Any]] = []

    def add_matched_rule(self, rule_name: str, context: dict[str, Any]):
        self.matched_rules.append(rule_name)
        self.enforcement_path.append(
            {
                "step": "match",
                "rule": rule_name,
                "context": context,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def add_failed_rule(self, rule_name: str, reason: str):
        self.failed_rules.append(rule_name)
        self.enforcement_path.append(
            {
                "step": "fail",
                "rule": rule_name,
                "reason": reason,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def add_remediation_hint(self, code: str, hint: str):
        self.remediation_hints.append({"violation_code": code, "hint": hint})

    def finalize_trace(self, final_action: str) -> dict[str, Any]:
        self.enforcement_path.append(
            {
                "step": "final_decision",
                "action": final_action,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        return {
            "evaluation_id": self.evaluation_id,
            "bundle_id": self.bundle_id,
            "matched_rules": self.matched_rules,
            "failed_rules": self.failed_rules,
            "enforcement_path": self.enforcement_path,
            "remediation_hints": self.remediation_hints,
        }
