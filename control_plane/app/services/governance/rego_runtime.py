import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class RegoRuntime:
    """
    Embedded Rego Runtime for sovereign evaluation.
    This simulates an embedded OPA execution without relying on an external SaaS.
    """

    def __init__(self, mode: str = "advisory"):
        self.mode = mode

    def load_bundle(self, bundle_content: str) -> str:
        """
        Parses and loads a signed policy bundle into the embedded runtime.
        Returns the rego_hash.
        """
        rego_hash = hashlib.sha256(bundle_content.encode("utf-8")).hexdigest()
        logger.info(f"Loaded rego bundle with hash: {rego_hash}")
        return rego_hash

    def evaluate(self, namespace: str, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a payload deterministically.
        Returns the raw result of the rego query, simulating OPA structured output.
        """
        # This is a mocked embedded evaluation engine that parses standard fields
        tenant_id = context.get("tenant_id")
        action = input_data.get("action", "unknown")
        
        # Simulated deterministic evaluation
        allowed = True
        violations = []
        matched_rules = []
        
        if "restrict" in action.lower():
            allowed = False
            violations.append({
                "code": f"{namespace}.RESTRICTED_ACTION",
                "severity": "high",
                "message": "Action is restricted by policy"
            })
            matched_rules.append("rule_restrict_action")
        else:
            matched_rules.append("rule_default_allow")
            
        return {
            "result": {
                "allow": allowed,
                "deny": not allowed,
                "violations": violations,
                "matched_rules": matched_rules,
                "namespace": namespace,
                "tenant_id": str(tenant_id) if tenant_id else None
            }
        }
