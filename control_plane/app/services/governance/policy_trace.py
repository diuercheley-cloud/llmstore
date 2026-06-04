from datetime import datetime, timezone
from typing import Any, Dict, List


class PolicyTraceBuilder:
    """
    Generates explainability traces for policy evaluation.
    Tracks matched rules, failed rules, enforcement path, and remediation hints.
    """
    def __init__(self, evaluation_id: str, bundle_id: str):
        self.evaluation_id = evaluation_id
        self.bundle_id = bundle_id
        self.matched_rules: List[str] = []
        self.failed_rules: List[str] = []
        self.enforcement_path: List[Dict[str, Any]] = []
        self.remediation_hints: List[Dict[str, Any]] = []

    def add_matched_rule(self, rule_name: str, context: Dict[str, Any]):
        self.matched_rules.append(rule_name)
        self.enforcement_path.append({
            "step": "match",
            "rule": rule_name,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def add_failed_rule(self, rule_name: str, reason: str):
        self.failed_rules.append(rule_name)
        self.enforcement_path.append({
            "step": "fail",
            "rule": rule_name,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def add_remediation_hint(self, code: str, hint: str):
        self.remediation_hints.append({
            "violation_code": code,
            "hint": hint
        })

    def finalize_trace(self, final_action: str) -> Dict[str, Any]:
        self.enforcement_path.append({
            "step": "final_decision",
            "action": final_action,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return {
            "evaluation_id": self.evaluation_id,
            "bundle_id": self.bundle_id,
            "matched_rules": self.matched_rules,
            "failed_rules": self.failed_rules,
            "enforcement_path": self.enforcement_path,
            "remediation_hints": self.remediation_hints
        }
