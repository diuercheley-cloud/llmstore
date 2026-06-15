import hashlib
import json
from typing import Any


class SimulatedRemediationExecutionAdapter:
    """
    Simulates the execution of remediation steps.
    Never performs real infrastructure actions.
    """

    def __init__(self, version: str = "v1"):
        self.version = version

    def execute_step(self, step: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
        """
        Simulates a single remediation step.
        """
        action_type = step.get("action_type", "unknown")
        target_domain = step.get("target_domain", "unknown")
        target_ref = step.get("target_ref", "unknown")

        # Deterministic simulated result
        result_payload = {
            "action": action_type,
            "target": f"{target_domain}:{target_ref}",
            "status": "success",
            "dry_run": dry_run,
            "simulated_effect": f"Effect of {action_type} applied to {target_domain}",
            "adapter_version": self.version,
        }

        # Compute a stable hash for the result
        raw = json.dumps(result_payload, sort_keys=True, ensure_ascii=False, default=str)
        result_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        result_payload["simulated_result_hash"] = result_hash

        return result_payload

    def execute_plan(
        self, plan: dict[str, Any], steps: list[dict[str, Any]], dry_run: bool = True
    ) -> list[dict[str, Any]]:
        """
        Simulates a whole sequence of steps.
        """
        results = []
        for step in steps:
            results.append(self.execute_step(step, dry_run=dry_run))
        return results
