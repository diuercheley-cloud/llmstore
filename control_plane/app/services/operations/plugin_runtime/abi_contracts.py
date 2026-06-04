from typing import Any

from app.models.operations.plugin_runtime import (
    PLUGIN_CONTRACT_SCOPES,
    PLUGIN_CONTRACT_STATUSES,
    PluginABIContract,
)
from app.services.operations.plugin_runtime.hash_utils import compute_abi_contract_hash, sha256_hex


class PluginABIContractService:
    def create_contract(self, plugin_metadata: dict[str, Any]) -> PluginABIContract:
        if not plugin_metadata.get("abi_version"):
            raise ValueError("abi_version is required")
        if not plugin_metadata.get("schema_version"):
            raise ValueError("schema_version is required")
        logical_payload = {
            "client_id": str(plugin_metadata["client_id"]),
            "plugin_name": plugin_metadata["plugin_name"],
            "plugin_version": plugin_metadata["plugin_version"],
            "abi_version": plugin_metadata["abi_version"],
            "schema_version": plugin_metadata["schema_version"],
            "contract_scope": plugin_metadata["contract_scope"],
            "contract_status": plugin_metadata.get("contract_status", "draft"),
            "deterministic_version": plugin_metadata.get("deterministic_version", "v1"),
        }
        contract_hash = compute_abi_contract_hash(logical_payload)
        contract = PluginABIContract(
            id=sha256_hex({"kind": "plugin_abi_contract_id", **logical_payload}),
            client_id=plugin_metadata["client_id"],
            plugin_name=plugin_metadata["plugin_name"],
            plugin_version=plugin_metadata["plugin_version"],
            abi_version=plugin_metadata["abi_version"],
            schema_version=plugin_metadata["schema_version"],
            contract_scope=plugin_metadata["contract_scope"],
            contract_status=logical_payload["contract_status"],
            deterministic_version=logical_payload["deterministic_version"],
            contract_hash=contract_hash,
            immutable_hash=sha256_hex({"kind": "plugin_abi_contract_immutable", "contract_hash": contract_hash}),
        )
        contract._logical_payload = logical_payload
        return contract

    def validate_contract(self, contract: PluginABIContract) -> dict[str, Any]:
        valid_scope = contract.contract_scope in PLUGIN_CONTRACT_SCOPES
        valid_status = contract.contract_status in PLUGIN_CONTRACT_STATUSES
        load_blocked = contract.contract_status in {"blocked", "revoked"}
        return {
            "valid": valid_scope and valid_status and bool(contract.abi_version) and bool(contract.schema_version),
            "load_blocked": load_blocked,
            "placeholder_certified_is_real": False,
            "reasons": [
                reason
                for reason, enabled in (
                    ("unsupported contract scope", not valid_scope),
                    ("unsupported contract status", not valid_status),
                    ("abi_version is required", not bool(contract.abi_version)),
                    ("schema_version is required", not bool(contract.schema_version)),
                    ("blocked or revoked contracts cannot be loaded", load_blocked),
                )
                if enabled
            ],
        }

    def block_contract(self, contract: PluginABIContract, reason: str) -> PluginABIContract:
        if not reason.strip():
            raise ValueError("reason is required")
        contract.contract_status = "blocked"
        contract._state_reason = reason.strip()
        return contract

    def deprecate_contract(self, contract: PluginABIContract, reason: str) -> PluginABIContract:
        if not reason.strip():
            raise ValueError("reason is required")
        contract.contract_status = "deprecated"
        contract._state_reason = reason.strip()
        return contract

    def explain_contract(self, contract: PluginABIContract) -> dict[str, Any]:
        validation = self.validate_contract(contract)
        return {
            "plugin_name": contract.plugin_name,
            "plugin_version": contract.plugin_version,
            "abi_version": contract.abi_version,
            "schema_version": contract.schema_version,
            "contract_scope": contract.contract_scope,
            "contract_status": contract.contract_status,
            "contract_hash": contract.contract_hash,
            "validation": validation,
            "notes": [
                "blocked/revoked cannot be loaded",
                "placeholder_certified is not real certification",
                "plugin execution requires explicit activation plus isolation policy",
            ],
        }
