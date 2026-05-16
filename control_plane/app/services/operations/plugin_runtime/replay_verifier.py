import json
from typing import Any

from app.services.operations.plugin_runtime.hash_utils import compute_abi_contract_hash, compute_load_plan_hash, compute_replay_hash


class PluginReplayVerifier:
    def replay_contract(self, contract: Any) -> dict[str, Any]:
        logical_payload = getattr(contract, "_logical_payload", None) or {
            "client_id": str(contract.client_id),
            "plugin_name": contract.plugin_name,
            "plugin_version": contract.plugin_version,
            "abi_version": contract.abi_version,
            "schema_version": contract.schema_version,
            "contract_scope": contract.contract_scope,
            "contract_status": contract.contract_status,
            "deterministic_version": contract.deterministic_version,
        }
        replayed = compute_abi_contract_hash(logical_payload)
        return self.compare_replay_hashes(contract.contract_hash, replayed)

    def replay_load_plan(self, load_plan: Any) -> dict[str, Any]:
        logical_payload = {
            "client_id": str(load_plan.client_id),
            "abi_contract_id": load_plan.abi_contract_id,
            "load_order": json.loads(load_plan.load_order),
            "load_status": load_plan.load_status,
            "dry_run": load_plan.dry_run,
        }
        replayed = compute_load_plan_hash(logical_payload)
        return self.compare_replay_hashes(load_plan.load_plan_hash, replayed)

    def replay_capability_boundary(self, boundary: Any) -> dict[str, Any]:
        logical_payload = {
            "client_id": str(boundary.client_id),
            "abi_contract_id": boundary.abi_contract_id,
            "allowed_capabilities_json": sorted(boundary.allowed_capabilities_json),
            "denied_capabilities_json": sorted(boundary.denied_capabilities_json),
            "offline_only": boundary.offline_only,
        }
        replayed = compute_replay_hash(logical_payload)
        original = compute_replay_hash(logical_payload)
        return self.compare_replay_hashes(original, replayed)

    def compare_replay_hashes(self, original: str, replayed: str) -> dict[str, Any]:
        return {"match": original == replayed, "original": original, "replayed": replayed}
