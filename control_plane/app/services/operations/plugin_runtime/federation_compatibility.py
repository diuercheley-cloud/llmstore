from typing import Any

from app.models.operations.plugin_runtime import PluginFederationCompatibility
from app.services.operations.plugin_runtime.hash_utils import compute_compatibility_hash, sha256_hex


class PluginFederationCompatibilityService:
    def evaluate_federation_compatibility(self, contract: Any, source_environment: str, target_environment: str) -> PluginFederationCompatibility:
        replay_safe = self.validate_federation_safe(contract)
        if contract.contract_status in {"blocked", "revoked"}:
            status = "blocked"
        elif not replay_safe:
            status = "incompatible"
        elif source_environment == target_environment:
            status = "compatible"
        else:
            status = "warning"
        logical_payload = {
            "client_id": str(contract.client_id),
            "abi_contract_id": contract.id,
            "source_environment": source_environment,
            "target_environment": target_environment,
            "federation_status": status,
            "replay_safe": replay_safe,
        }
        compatibility_hash = compute_compatibility_hash(logical_payload)
        return PluginFederationCompatibility(
            id=sha256_hex({"kind": "plugin_federation_compatibility_id", **logical_payload}),
            client_id=contract.client_id,
            abi_contract_id=contract.id,
            source_environment=source_environment,
            target_environment=target_environment,
            federation_status=status,
            compatibility_hash=compatibility_hash,
            replay_safe=replay_safe,
            immutable_hash=sha256_hex({"kind": "plugin_federation_compatibility_immutable", "compatibility_hash": compatibility_hash}),
        )

    def validate_federation_safe(self, contract: Any) -> bool:
        return contract.contract_status not in {"blocked", "revoked"} and bool(contract.abi_version) and bool(contract.schema_version)

    def build_federation_compatibility_summary(self, contract: Any) -> dict[str, Any]:
        return {
            "contract_id": contract.id,
            "replay_safe_required": True,
            "placeholder_trust_only": True,
            "phase77_conceptual_alignment": True,
        }

    def explain_federation_compatibility(self, result: PluginFederationCompatibility) -> dict[str, Any]:
        return {
            "abi_contract_id": result.abi_contract_id,
            "federation_status": result.federation_status,
            "replay_safe": result.replay_safe,
            "notes": [
                "replay_safe is required",
                "placeholder trust only",
                "incompatible blocks federation compatibility",
            ],
        }
