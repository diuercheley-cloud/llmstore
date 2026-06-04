from typing import Any

from app.models.operations.plugin_runtime import PluginRuntimeCompatibilityCheck
from app.services.operations.compatibility_contracts.semantic_versioning import (
    SemanticVersioningService,
)
from app.services.operations.compatibility_contracts.validation import validate_schema_compatibility
from app.services.operations.plugin_runtime.hash_utils import compute_compatibility_hash, sha256_hex


class PluginRuntimeCompatibilityEnforcer:
    def __init__(self) -> None:
        self.semver = SemanticVersioningService()

    def check_runtime_compatibility(self, contract: Any, runtime_version: str) -> dict[str, Any]:
        version_report = self.check_semantic_version_policy(contract)
        order = self.semver.compare_versions(contract.plugin_version, runtime_version)
        if contract.contract_status in {"blocked", "revoked"}:
            status = "blocked"
            reason = f"contract_status={contract.contract_status}"
        elif not version_report["valid"]:
            status = "incompatible"
            reason = version_report["reason"]
        elif contract.plugin_version != runtime_version and order["same_major"]:
            status = "warning"
            reason = "runtime version differs within same major; review required before activation"
        elif contract.plugin_version == runtime_version:
            status = "compatible"
            reason = "exact runtime match"
        else:
            status = "incompatible"
            reason = "runtime version mismatch"
        return {
            "runtime_version": runtime_version,
            "compatibility_status": status,
            "replay_safe": status != "blocked",
            "federation_safe": status == "compatible",
            "reason": reason,
        }

    def check_schema_compatibility(self, contract: Any) -> dict[str, Any]:
        return validate_schema_compatibility(contract.schema_version, contract.schema_version)

    def check_semantic_version_policy(self, contract: Any) -> dict[str, Any]:
        try:
            parsed = self.semver.parse_version(contract.plugin_version)
        except ValueError as exc:
            return {"valid": False, "reason": str(exc)}
        if parsed["major"] < 1:
            return {"valid": False, "reason": "semantic version governance requires stable major version"}
        return {"valid": True, "reason": "semantic version governance passed"}

    def enforce_compatibility(self, contract: Any, runtime_version: str | None = None) -> PluginRuntimeCompatibilityCheck:
        runtime_version = runtime_version or contract.plugin_version
        runtime_report = self.check_runtime_compatibility(contract, runtime_version)
        schema_report = self.check_schema_compatibility(contract)
        reason = f"{runtime_report['reason']}; schema={schema_report['summary']}"
        logical_payload = {
            "client_id": str(contract.client_id),
            "abi_contract_id": contract.id,
            "runtime_version": runtime_version,
            "compatibility_status": runtime_report["compatibility_status"],
            "replay_safe": runtime_report["replay_safe"],
            "federation_safe": runtime_report["federation_safe"],
            "reason": reason,
        }
        immutable_hash = compute_compatibility_hash(logical_payload)
        return PluginRuntimeCompatibilityCheck(
            id=sha256_hex({"kind": "plugin_runtime_compatibility_check_id", **logical_payload}),
            client_id=contract.client_id,
            abi_contract_id=contract.id,
            runtime_version=runtime_version,
            compatibility_status=runtime_report["compatibility_status"],
            replay_safe=runtime_report["replay_safe"],
            federation_safe=runtime_report["federation_safe"],
            reason=reason,
            immutable_hash=immutable_hash,
        )

    def explain_compatibility(self, result: PluginRuntimeCompatibilityCheck) -> dict[str, Any]:
        return {
            "abi_contract_id": result.abi_contract_id,
            "runtime_version": result.runtime_version,
            "compatibility_status": result.compatibility_status,
            "activation_requires_review": result.compatibility_status == "warning",
            "load_plan_blocked": result.compatibility_status in {"incompatible", "blocked"},
            "reason": result.reason,
        }
