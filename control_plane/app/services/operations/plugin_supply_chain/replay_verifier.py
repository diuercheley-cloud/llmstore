from typing import Any

from app.services.operations.plugin_supply_chain.hash_utils import (
    compute_lineage_hash,
    compute_provenance_hash,
    compute_sbom_hash,
)


class PluginSupplyChainReplayVerifier:
    def verify_provenance(self, record: Any) -> dict[str, Any]:
        logical_payload = getattr(record, "_logical_payload", None) or {
            "client_id": str(record.client_id),
            "plugin_contract_id": record.plugin_contract_id,
            "artifact_name": record.artifact_name,
            "artifact_version": record.artifact_version,
            "provenance_scope": record.provenance_scope,
            "replay_safe": record.replay_safe,
        }
        return self.compare_hashes(record.provenance_hash, compute_provenance_hash(logical_payload))

    def verify_sbom(self, placeholder: Any) -> dict[str, Any]:
        logical_payload = getattr(placeholder, "_logical_payload", None) or {
            "client_id": str(placeholder.client_id),
            "provenance_record_id": placeholder.provenance_record_id,
            "sbom_format": placeholder.sbom_format,
            "dependency_summary_json": placeholder.dependency_summary_json,
            "denied_dependencies_json": sorted(placeholder.denied_dependencies_json),
            "reproducible_build": placeholder.reproducible_build,
            "offline_verifiable": placeholder.offline_verifiable,
            "signature_only": True,
        }
        return self.compare_hashes(placeholder.sbom_hash, compute_sbom_hash(logical_payload))

    def verify_lineage(self, lineage: Any, provenance_record: Any) -> dict[str, Any]:
        logical_payload = getattr(lineage, "_logical_payload", None) or {
            "client_id": str(lineage.client_id),
            "provenance_record_id": lineage.provenance_record_id,
            "parent_artifact_hash": lineage.parent_artifact_hash,
            "provenance_hash": provenance_record.provenance_hash,
            "artifact_name": provenance_record.artifact_name,
            "artifact_version": provenance_record.artifact_version,
        }
        return self.compare_hashes(lineage.lineage_hash, compute_lineage_hash(logical_payload))

    def compare_hashes(self, original: str, replayed: str) -> dict[str, Any]:
        return {"match": original == replayed, "original": original, "replayed": replayed}
