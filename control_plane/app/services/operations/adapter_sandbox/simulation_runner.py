import uuid
from typing import Any, Dict, List, Optional

from app.models.operations.adapter_sandbox import compute_deterministic_hash


class AdapterSandboxSimulationRunner:
    """
    Simulates the execution of adapter activities in a safe sandbox.
    """

    def prepare_run(self, manifest: Any, execution_id: Optional[uuid.UUID] = None, 
                    plan_id: Optional[uuid.UUID] = None, sandbox_mode: str = "simulation") -> Dict[str, Any]:
        """
        Creates initial run metadata.
        """
        input_data = {
            "manifest_id": str(manifest.id),
            "execution_id": str(execution_id) if execution_id else None,
            "plan_id": str(plan_id) if plan_id else None,
            "sandbox_mode": sandbox_mode
        }
        
        input_hash = compute_deterministic_hash(fields=input_data)
        
        return {
            "client_id": manifest.client_id,
            "manifest_id": manifest.id,
            "execution_id": execution_id,
            "plan_id": plan_id,
            "sandbox_mode": sandbox_mode,
            "dry_run": True, # Always True in Phase 73
            "status": "pending",
            "input_hash": input_hash
        }

    def simulate_step(self, context: Any, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates a single step result deterministically.
        """
        action_type = step.get("action_type", "unknown")
        target_domain = step.get("target_domain", "unknown")
        
        # Check approval
        if context.approval_required and not context.approval_verified:
            return {
                "result_status": "blocked",
                "simulated_output_json": {
                    "error": "Approval required but not verified",
                    "violation_type": "approval_missing"
                }
            }

        # Check gates
        if context.gates_required and not context.gates_verified:
            return {
                "result_status": "blocked",
                "simulated_output_json": {
                    "error": "Architectural gates required but not verified",
                    "violation_type": "gates_missing"
                }
            }

        # Check capability
        if not context.can_perform(action_type):
            return {
                "result_status": "denied",
                "simulated_output_json": {
                    "error": f"Capability '{action_type}' not allowed",
                    "violation": True
                }
            }

        # Deterministic simulation output
        output_payload = {
            "simulated_action": action_type,
            "target": target_domain,
            "status": "success",
            "dry_run": context.dry_run,
            "simulated_at": "2026-05-15T12:00:00Z", # Deterministic for Phase 73
            "adapter_version": "sandbox-v1"
        }
        
        return {
            "result_status": "success",
            "simulated_output_json": output_payload
        }

    def simulate_run(self, context: Any, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulates all steps in a run."""
        results = []
        for step in steps:
            results.append(self.simulate_step(context, step))
        return results

    def explain_run(self, run: Any, results: List[Dict[str, Any]]) -> str:
        """Human-readable explanation of the run."""
        summary = [
            f"Sandbox Run: {run.id}",
            f"Status: {run.status.upper()}",
            f"Mode: {run.sandbox_mode}",
            "",
            "Simulated Step Results:"
        ]
        
        for i, res in enumerate(results):
            summary.append(f"{i+1}. [{res['result_status'].upper()}] - {res['simulated_output_json'].get('simulated_action')}")
            
        return "\n".join(summary)
