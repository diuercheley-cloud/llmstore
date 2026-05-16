from typing import Any

from app.models.operations.plugin_supply_chain import PluginArtifactLineage
from app.services.operations.plugin_supply_chain.hash_utils import compute_lineage_hash, sha256_hex


class PluginArtifactLineageService:
    def create_lineage(self, provenance_record: Any, parent_artifact_hash: str | None = None) -> PluginArtifactLineage:
        logical_payload = {
            "client_id": str(provenance_record.client_id),
            "provenance_record_id": provenance_record.id,
            "parent_artifact_hash": parent_artifact_hash,
            "provenance_hash": provenance_record.provenance_hash,
            "artifact_name": provenance_record.artifact_name,
            "artifact_version": provenance_record.artifact_version,
        }
        lineage_hash = compute_lineage_hash(logical_payload)
        lineage = PluginArtifactLineage(
            id=sha256_hex({"kind": "plugin_artifact_lineage_id", **logical_payload}),
            client_id=provenance_record.client_id,
            provenance_record_id=provenance_record.id,
            parent_artifact_hash=parent_artifact_hash,
            lineage_hash=lineage_hash,
            replay_verifiable=True,
            immutable_hash=sha256_hex({"kind": "plugin_artifact_lineage_immutable", "lineage_hash": lineage_hash}),
        )
        lineage._logical_payload = logical_payload
        return lineage

    def verify_lineage(self, lineage: PluginArtifactLineage, provenance_record: Any) -> dict[str, Any]:
        logical_payload = getattr(lineage, "_logical_payload", None) or {
            "client_id": str(lineage.client_id),
            "provenance_record_id": lineage.provenance_record_id,
            "parent_artifact_hash": lineage.parent_artifact_hash,
            "provenance_hash": provenance_record.provenance_hash,
            "artifact_name": provenance_record.artifact_name,
            "artifact_version": provenance_record.artifact_version,
        }
        replayed_hash = compute_lineage_hash(logical_payload)
        return {
            "verified": replayed_hash == lineage.lineage_hash,
            "lineage_hash": lineage.lineage_hash,
            "replayed_hash": replayed_hash,
            "replay_verifiable": lineage.replay_verifiable,
        }
