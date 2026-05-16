from typing import Any

from app.services.operations.reproducible_builds.hash_utils import compute_artifact_hash, compute_build_manifest_hash, compute_lineage_hash, compute_replay_hash


class ArtifactReplayVerifier:
    def replay_build_manifest(self, manifest: Any) -> dict[str, Any]:
        logical_payload = getattr(manifest, "_logical_payload", None) or {
            "client_id": str(manifest.client_id),
            "build_name": manifest.build_name,
            "build_scope": manifest.build_scope,
            "source_reference": manifest.source_reference,
            "deterministic_version": manifest.deterministic_version,
            "build_environment_hash": manifest.build_environment_hash,
            "replay_safe": manifest.replay_safe,
        }
        return self.compare_replay_hashes(manifest.build_manifest_hash, compute_build_manifest_hash(logical_payload))

    def replay_artifact(self, record: Any) -> dict[str, Any]:
        logical_payload = getattr(record, "_logical_payload", None) or {
            "client_id": str(record.client_id),
            "build_manifest_id": record.build_manifest_id,
            "artifact_name": record.artifact_name,
            "artifact_version": record.artifact_version,
        }
        return self.compare_replay_hashes(record.artifact_hash, compute_artifact_hash(logical_payload))

    def replay_lineage(self, lineage: Any) -> dict[str, Any]:
        logical_payload = getattr(lineage, "_logical_payload", None) or {
            "client_id": str(lineage.client_id),
            "build_manifest_id": lineage.build_manifest_id,
            "source_hash": lineage.source_hash,
            "artifact_hash": lineage.artifact_hash,
        }
        return self.compare_replay_hashes(lineage.lineage_hash, compute_lineage_hash(logical_payload))

    def compare_replay_hashes(self, original: str, replayed: str) -> dict[str, Any]:
        replay_hash = compute_replay_hash({"original": original, "replayed": replayed})
        return {
            "match": original == replayed,
            "original": original,
            "replayed": replayed,
            "replay_hash": replay_hash,
            "deterministic_only": True,
        }
