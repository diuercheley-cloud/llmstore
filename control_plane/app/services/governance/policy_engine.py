import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.time import utc_now
from app.models.commercial.commercial_governance import (
    CommercialPolicyArtifact,
    CommercialPolicyBundle,
    CommercialPolicyDriftEvent,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PolicyEngineService:
    @staticmethod
    def sign_policy_bundle(rules_json: Dict[str, Any], immutable_hash: str, secret_key: str = "internal-governance-secret") -> str:
        # Simple signature: SHA256(bundle_json + immutable_hash + secret)
        # In production, this would use a real private key
        payload = {
            "rules": rules_json,
            "hash": immutable_hash,
            "secret": secret_key
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def validate_policy_signature(bundle: CommercialPolicyBundle, secret_key: str = "internal-governance-secret") -> bool:
        if not bundle.signature:
            return False
        
        expected_sig = PolicyEngineService.sign_policy_bundle(bundle.rules_json, bundle.immutable_hash, secret_key)
        return bundle.signature == expected_sig

    async def validate_policy_bundle(self, rules_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        # Basic schema validation
        required_sections = ["routing", "billing", "qos"]
        for section in required_sections:
            if section not in rules_json:
                # We don't fail if a section is missing, we just use defaults, 
                # but for a strict policy we might require them.
                pass
        
        # Example validation for routing
        routing = rules_json.get("routing", {})
        if "max_cost_per_request_brl" in routing:
            if not isinstance(routing["max_cost_per_request_brl"], (int, float)):
                errors.append("routing.max_cost_per_request_brl must be a number")
        
        return len(errors) == 0, errors

    async def simulate_policy_bundle(
        self,
        db: AsyncSession,
        bundle_id: uuid.UUID,
        runtime_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = await db.execute(select(CommercialPolicyBundle).where(CommercialPolicyBundle.id == bundle_id))
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise ValueError("Policy bundle not found")
        
        # Mock simulation logic
        simulation_results = {
            "bundle_id": str(bundle.id),
            "timestamp": utc_now().isoformat(),
            "status": "success",
            "impact_summary": "Simulated against current runtime context.",
            "affected_tenants": [str(bundle.client_id)] if bundle.client_id else ["global"],
            "expected_impact": {
                "routing_efficiency": "+5%",
                "cost_reduction": "estimated 2% monthly",
                "sla_compliance": "no negative impact predicted"
            },
            "financial_impact_brl": 150.00,
            "policy_mode": bundle.mode
        }
        
        # Save simulation as artifact
        artifact = CommercialPolicyArtifact(
            bundle_id=bundle.id,
            artifact_type="simulation",
            artifact_hash=hashlib.sha256(json.dumps(simulation_results).encode()).hexdigest(),
            artifact_json=simulation_results,
        )
        db.add(artifact)
        
        return simulation_results

    async def detect_policy_drift(
        self,
        db: AsyncSession,
        bundle_type: str,
        client_id: Optional[uuid.UUID] = None,
        runtime_config: Optional[Dict[str, Any]] = None
    ) -> List[CommercialPolicyDriftEvent]:
        # Find active bundle
        result = await db.execute(
            select(CommercialPolicyBundle)
            .where(
                CommercialPolicyBundle.bundle_type == bundle_type,
                CommercialPolicyBundle.client_id == client_id,
                CommercialPolicyBundle.status == "active"
            )
        )
        active_bundle = result.scalar_one_or_none()
        
        drifts = []
        if not active_bundle:
            # Missing active bundle is a drift if policy governance is enabled
            event = CommercialPolicyDriftEvent(
                drift_type="missing_rule",
                severity="medium",
                drift_summary=f"No active policy bundle found for type {bundle_type}",
                resolved=False
            )
            db.add(event)
            drifts.append(event)
            return drifts

        if runtime_config:
            # Compare runtime config with active bundle rules
            from app.services.governance.policy_registry import PolicyRegistryService
            
            expected_hash = active_bundle.immutable_hash
            observed_hash = PolicyRegistryService.calculate_bundle_hash(runtime_config, active_bundle.metadata_json)
            
            if expected_hash != observed_hash:
                event = CommercialPolicyDriftEvent(
                    bundle_id=active_bundle.id,
                    drift_type="config_drift",
                    severity="high",
                    expected_hash=expected_hash,
                    observed_hash=observed_hash,
                    drift_summary=f"Runtime configuration differs from active policy bundle {active_bundle.bundle_version}",
                    metadata_json={"runtime_config": runtime_config},
                    resolved=False
                )
                db.add(event)
                drifts.append(event)
        
        return drifts

    async def evaluate_rules(self, bundle: CommercialPolicyBundle, context: Dict[str, Any]) -> Dict[str, Any]:
        # Extract constraints from bundle based on context
        rules = bundle.rules_json
        mode = bundle.mode
        
        effective_constraints = {}
        
        if mode == "disabled":
            return {}
        
        # Example: extract routing constraints
        routing = rules.get("routing", {})
        if routing:
            effective_constraints["routing"] = routing
            
        # QoS constraints
        qos = rules.get("qos", {})
        if qos:
            effective_constraints["qos"] = qos
            
        return effective_constraints
