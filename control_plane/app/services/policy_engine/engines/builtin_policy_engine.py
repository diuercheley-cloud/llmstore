import uuid
import logging
from typing import List, Dict, Any

from app.services.policy_engine.base import (
    PolicyEngine, 
    PolicyContext, 
    PolicyDecision, 
    DecisionResult
)

logger = logging.getLogger(__name__)


class BuiltinPolicyEngine(PolicyEngine):
    def __init__(self, rules: List[Dict[str, Any]] = None):
        # Default simple rules
        self.rules = rules or [
            {
                "id": "rule-001",
                "action": "tool_call",
                "condition": lambda ctx: ctx.risk_score > 0.8,
                "result": DecisionResult.REQUIRE_APPROVAL,
                "reason": "High risk tool call requires approval."
            },
            {
                "id": "rule-002",
                "action": "tool_call",
                "condition": lambda ctx: ctx.data_classification == "secret",
                "result": DecisionResult.DENY,
                "reason": "Access to secret data via tool call is prohibited."
            },
            {
                "id": "rule-003",
                "action": "inference",
                "condition": lambda ctx: ctx.attestation_status == "none" and ctx.risk_score > 0.5,
                "result": DecisionResult.REQUIRE_ATTESTATION,
                "reason": "Inference with medium risk requires hardware attestation."
            }
        ]

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        decision_id = str(uuid.uuid4())
        
        for rule in self.rules:
            # Check action type
            if rule.get("action") and rule.get("action") != context.action_type:
                continue
                
            # Check condition
            condition = rule.get("condition")
            if condition and condition(context):
                return PolicyDecision(
                    result=rule["result"],
                    reason=rule["reason"],
                    engine=self.get_engine_name(),
                    decision_id=decision_id,
                    explanation=f"Matched rule {rule['id']}"
                )

        # Default fallback
        return PolicyDecision(
            result=DecisionResult.ALLOW,
            reason="No restrictive rules matched. Action allowed by default.",
            engine=self.get_engine_name(),
            decision_id=decision_id,
            explanation="Default allow"
        )

    def get_engine_name(self) -> str:
        return "builtin"
