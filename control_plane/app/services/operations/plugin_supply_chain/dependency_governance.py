import json
from typing import Any

from app.models.operations.plugin_supply_chain import (
    DependencyGovernancePolicy,
    PLUGIN_DEPENDENCY_VERIFICATION_STATUSES,
    PluginDependencyVerification,
)
from app.services.operations.plugin_supply_chain.hash_utils import canonical_json, sha256_hex

DENIED_DEPENDENCY_CLASSES = (
    "network_loaders",
    "remote_package_installers",
    "shell_based_installers",
    "dynamic_external_imports",
    "unverified_binary_artifacts",
)

DEFAULT_ALLOWED_DEPENDENCY_CLASSES = (
    "local_static_module",
    "bundled_manifest",
    "embedded_placeholder_metadata",
)


class DependencyGovernanceService:
    def create_policy(
        self,
        client_id: Any,
        policy_name: str = "default-plugin-supply-chain",
        denied_dependency_classes_json: list[str] | None = None,
        allowed_dependency_classes_json: list[str] | None = None,
        require_reproducible_builds: bool = True,
        require_offline_verification: bool = True,
        require_signature: bool = True,
    ) -> DependencyGovernancePolicy:
        denied = sorted(set(denied_dependency_classes_json or DENIED_DEPENDENCY_CLASSES))
        allowed = sorted(set(allowed_dependency_classes_json or DEFAULT_ALLOWED_DEPENDENCY_CLASSES))
        logical_payload = {
            "client_id": str(client_id),
            "policy_name": policy_name,
            "denied_dependency_classes_json": denied,
            "allowed_dependency_classes_json": allowed,
            "require_reproducible_builds": require_reproducible_builds,
            "require_offline_verification": require_offline_verification,
            "require_signature": require_signature,
        }
        immutable_hash = sha256_hex({"kind": "plugin_dependency_governance_policy", **logical_payload})
        policy = DependencyGovernancePolicy(
            id=sha256_hex({"kind": "plugin_dependency_governance_policy_id", **logical_payload}),
            client_id=client_id,
            policy_name=policy_name,
            denied_dependency_classes_json=denied,
            allowed_dependency_classes_json=allowed,
            require_reproducible_builds=require_reproducible_builds,
            require_offline_verification=require_offline_verification,
            require_signature=require_signature,
            immutable_hash=immutable_hash,
        )
        policy._logical_payload = logical_payload
        return policy

    def verify_dependencies(
        self,
        provenance_record: Any,
        dependency_summary_json: dict[str, Any],
        policy: DependencyGovernancePolicy,
        signature: str | None = None,
        reproducible_build: bool = True,
        offline_verifiable: bool = True,
    ) -> PluginDependencyVerification:
        classes = sorted(set(dependency_summary_json.get("dependency_classes", [])))
        denied_hits = sorted(set(classes).intersection(policy.denied_dependency_classes_json))
        status = "passed"
        notes: list[str] = []
        if denied_hits:
            status = "blocked"
            notes.append(f"denied dependency classes detected: {', '.join(denied_hits)}")
        if policy.require_reproducible_builds and not reproducible_build:
            status = "failed"
            notes.append("reproducible build marker missing")
        if policy.require_offline_verification and not offline_verifiable:
            status = "failed"
            notes.append("offline verification marker missing")
        if policy.require_signature and not signature:
            status = "warning" if status == "passed" else status
            notes.append("signature missing")
        if status not in PLUGIN_DEPENDENCY_VERIFICATION_STATUSES:
            raise ValueError("unsupported verification status")
        summary = {
            "dependency_classes": classes,
            "denied_hits": denied_hits,
            "allowed_dependency_classes": policy.allowed_dependency_classes_json,
            "signature_present": bool(signature),
            "reproducible_build": reproducible_build,
            "offline_verifiable": offline_verifiable,
            "notes": notes,
            "no_real_execution": True,
            "no_external_dependency_resolution": True,
        }
        logical_payload = {
            "client_id": str(provenance_record.client_id),
            "provenance_record_id": provenance_record.id,
            "verification_status": status,
            "dependency_summary": summary,
        }
        verification = PluginDependencyVerification(
            id=sha256_hex({"kind": "plugin_dependency_verification_id", **logical_payload}),
            client_id=provenance_record.client_id,
            provenance_record_id=provenance_record.id,
            verification_status=status,
            replay_safe=status in {"passed", "warning"},
            dependency_summary=canonical_json(summary),
            immutable_hash=sha256_hex({"kind": "plugin_dependency_verification_immutable", **logical_payload}),
        )
        verification._summary = summary
        return verification

    def explain_denied_classes(self) -> dict[str, Any]:
        return {
            "denied_dependency_classes": list(DENIED_DEPENDENCY_CLASSES),
            "blocked_controls": [
                "network loaders",
                "remote package installers",
                "shell-based installers",
                "dynamic external imports",
                "unverified binary artifacts",
            ],
            "offline_first": True,
            "real_package_manager": False,
        }
