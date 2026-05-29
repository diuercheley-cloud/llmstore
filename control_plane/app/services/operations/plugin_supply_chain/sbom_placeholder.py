from typing import Any

from app.models.operations.plugin_supply_chain import PluginSBOMPlaceholder
from app.services.operations.plugin_supply_chain.hash_utils import compute_sbom_hash, sha256_hex


class PluginSBOMPlaceholderService:
    def generate_sbom_placeholder(
        self,
        provenance_record: Any,
        dependency_summary_json: dict[str, Any],
        denied_dependencies_json: list[str],
        sbom_format: str = "placeholder_v1",
        reproducible_build: bool = True,
        offline_verifiable: bool = True,
    ) -> PluginSBOMPlaceholder:
        from app.core.config import get_settings
        if get_settings().app_env == "production":
            raise RuntimeError("Placeholder SBOM is blocked in production mode.")

        logical_payload = {
            "client_id": str(provenance_record.client_id),
            "provenance_record_id": provenance_record.id,
            "sbom_format": sbom_format,
            "dependency_summary_json": dependency_summary_json,
            "denied_dependencies_json": sorted(denied_dependencies_json),
            "reproducible_build": reproducible_build,
            "offline_verifiable": offline_verifiable,
            "placeholder_only": True,
        }
        sbom_hash = compute_sbom_hash(logical_payload)
        immutable_hash = sha256_hex({"kind": "plugin_supply_chain_sbom_immutable", "sbom_hash": sbom_hash})
        placeholder = PluginSBOMPlaceholder(
            id=sha256_hex({"kind": "plugin_supply_chain_sbom_id", **logical_payload}),
            client_id=provenance_record.client_id,
            provenance_record_id=provenance_record.id,
            sbom_format=sbom_format,
            dependency_summary_json=dependency_summary_json,
            denied_dependencies_json=sorted(denied_dependencies_json),
            reproducible_build=reproducible_build,
            offline_verifiable=offline_verifiable,
            sbom_hash=sbom_hash,
            immutable_hash=immutable_hash,
        )
        placeholder._logical_payload = logical_payload
        return placeholder

    def validate_sbom_placeholder(self, placeholder: PluginSBOMPlaceholder) -> dict[str, Any]:
        from app.core.config import get_settings
        if get_settings().app_env == "production":
            raise RuntimeError("Placeholder SBOM is blocked in production mode.")

        logical_payload = getattr(placeholder, "_logical_payload", None) or {
            "client_id": str(placeholder.client_id),
            "provenance_record_id": placeholder.provenance_record_id,
            "sbom_format": placeholder.sbom_format,
            "dependency_summary_json": placeholder.dependency_summary_json,
            "denied_dependencies_json": sorted(placeholder.denied_dependencies_json),
            "reproducible_build": placeholder.reproducible_build,
            "offline_verifiable": placeholder.offline_verifiable,
            "placeholder_only": True,
        }
        replay_hash = compute_sbom_hash(logical_payload)
        valid = replay_hash == placeholder.sbom_hash
        return {
            "valid": valid,
            "placeholder_only": True,
            "offline_verifiable": placeholder.offline_verifiable,
            "reproducible_build": placeholder.reproducible_build,
            "original_hash": placeholder.sbom_hash,
            "replayed_hash": replay_hash,
        }

    def explain_sbom(self, placeholder: PluginSBOMPlaceholder) -> dict[str, Any]:
        return {
            "sbom_format": placeholder.sbom_format,
            "placeholder_only": True,
            "formal_sbom": False,
            "offline_verifiable": placeholder.offline_verifiable,
            "reproducible_build": placeholder.reproducible_build,
            "notes": [
                "placeholder SBOM only",
                "no external dependency resolver",
                "deterministic metadata only",
            ],
        }
