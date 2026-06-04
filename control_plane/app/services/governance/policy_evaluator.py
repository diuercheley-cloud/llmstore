import logging
import uuid
from typing import Any, Dict, Optional

from app.models.commercial_policy_runtime import (
    CommercialPolicyEvaluation,
    CommercialPolicyRuntimeBundle,
    CommercialPolicySimulation,
    CommercialPolicyViolation,
)
from app.services.governance.policy_trace import PolicyTraceBuilder
from app.services.governance.rego_runtime import RegoRuntime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class PolicyEvaluator:
    """
    Orchestrates policy evaluations:
    - Resolves conflicts and priority ordering.
    - Manages policy inheritance and tenant-scoped overrides.
    - Handles different modes: advisory, dry_run, enforce, sovereign_strict.
    """

    def __init__(self, db: Session):
        self.db = db

    def evaluate(
        self,
        namespace: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        mode: str = "enforce"
    ) -> Dict[str, Any]:
        """
        Performs an evaluation using the RegoRuntime.
        Records traces and violations to the database.
        """
        tenant_id = context.get("tenant_id")
        
        # 1. Resolve Policy Bundle (tenant override -> global)
        bundle = self._resolve_bundle(namespace, tenant_id)
        if not bundle:
            logger.warning(f"No policy bundle found for namespace {namespace}")
            return {"allowed": True, "reason": "no_policy"}

        # 2. Evaluate using Embedded Engine
        runtime = RegoRuntime(mode=mode)
        raw_result = runtime.evaluate(namespace, input_data, context)
        rego_res = raw_result.get("result", {})

        # 3. Build Trace
        eval_id = str(uuid.uuid4())
        trace_builder = PolicyTraceBuilder(evaluation_id=eval_id, bundle_id=str(bundle.id))
        
        for rule in rego_res.get("matched_rules", []):
            trace_builder.add_matched_rule(rule, {"namespace": namespace})

        violations = rego_res.get("violations", [])
        final_decision = "deny" if violations else "allow"
        
        # If in dry_run or advisory mode, don't actually enforce denial
        if final_decision == "deny" and mode in ("advisory", "dry_run"):
            final_decision = "warn"

        trace_data = trace_builder.finalize_trace(final_decision)

        # 4. Record Evaluation
        evaluation = CommercialPolicyEvaluation(
            id=uuid.UUID(eval_id),
            bundle_id=bundle.id,
            evaluation_mode=mode,
            enforcement_result=final_decision,
            decision_trace=trace_data,
            runtime_hash=bundle.rego_hash,
            tenant_id=tenant_id
        )
        self.db.add(evaluation)
        
        for v in violations:
            violation = CommercialPolicyViolation(
                evaluation_id=evaluation.id,
                tenant_id=tenant_id,
                violation_code=v.get("code", "UNKNOWN"),
                severity=v.get("severity", "medium"),
                remediation_hints={"message": v.get("message", "No hint available")}
            )
            self.db.add(violation)
            
            trace_builder.add_remediation_hint(v.get("code", "UNKNOWN"), v.get("message", ""))

        self.db.commit()
        return {
            "allowed": final_decision in ("allow", "warn"),
            "decision": final_decision,
            "violations": violations,
            "trace": trace_data
        }

    def simulate(
        self,
        simulation_name: str,
        namespace: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Runs a dry_run evaluation and records the output in the simulations table.
        """
        tenant_id = context.get("tenant_id")
        bundle = self._resolve_bundle(namespace, tenant_id)
        if not bundle:
            return {"error": "no_policy_bundle"}

        result = self.evaluate(namespace, input_data, context, mode="dry_run")
        
        sim = CommercialPolicySimulation(
            bundle_id=bundle.id,
            simulation_name=simulation_name,
            input_payload=input_data,
            expected_result=None,
            actual_result=result["decision"],
            diff_trace=result["trace"]
        )
        self.db.add(sim)
        self.db.commit()
        
        return result

    def _resolve_bundle(self, namespace: str, tenant_id: Optional[uuid.UUID]) -> Optional[CommercialPolicyRuntimeBundle]:
        # Attempt to find tenant-scoped bundle first
        if tenant_id:
            bundle = self.db.query(CommercialPolicyRuntimeBundle).filter_by(
                policy_namespace=namespace,
                tenant_id=tenant_id,
                is_active=True
            ).first()
            if bundle:
                return bundle
                
        # Fallback to global bundle
        bundle = self.db.query(CommercialPolicyRuntimeBundle).filter_by(
            policy_namespace=namespace,
            tenant_id=None,
            is_active=True
        ).first()
        return bundle
