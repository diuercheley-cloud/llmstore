from typing import Any

from app.models.operations.reproducible_builds import SourceArtifactLineage
from app.services.operations.reproducible_builds.hash_utils import compute_lineage_hash, sha256_hex


class SourceArtifactLineageService:
    def create_lineage(self, manifest: Any, source_hash: str, artifact_hash: str) -> SourceArtifactLineage:
        logical_payload = {
            "client_id": str(manifest.client_id),
            "build_manifest_id": manifest.id,
            "source_hash": source_hash,
            "artifact_hash": artifact_hash,
            "source_reference": manifest.source_reference,
        }
        lineage_hash = compute_lineage_hash(logical_payload)
        lineage = SourceArtifactLineage(
            id=sha256_hex({"kind": "source_artifact_lineage_id", **logical_payload}),
            client_id=manifest.client_id,
            build_manifest_id=manifest.id,
            source_hash=source_hash,
            artifact_hash=artifact_hash,
            lineage_hash=lineage_hash,
            replay_verifiable=True,
            immutable_hash=sha256_hex({"kind": "source_artifact_lineage_immutable", "lineage_hash": lineage_hash}),
        )
        lineage._logical_payload = logical_payload
        return lineage

    def verify_lineage(self, lineage: SourceArtifactLineage) -> dict[str, Any]:
        logical_payload = getattr(lineage, "_logical_payload", None) or {
            "client_id": str(lineage.client_id),
            "build_manifest_id": lineage.build_manifest_id,
            "source_hash": lineage.source_hash,
            "artifact_hash": lineage.artifact_hash,
        }
        replayed_hash = compute_lineage_hash(logical_payload)
        verified = replayed_hash == lineage.lineage_hash and lineage.replay_verifiable
        return {
            "verified": verified,
            "lineage_hash": lineage.lineage_hash,
            "replayed_hash": replayed_hash,
            "verification_status": "passed" if verified else "blocked",
        }

    def validate_lineage_integrity(self, lineage: SourceArtifactLineage, expected_artifact_hash: str) -> dict[str, Any]:
        conflict = lineage.artifact_hash != expected_artifact_hash
        return {
            "integrity_ok": not conflict,
            "verification_status": "blocked" if conflict else "passed",
            "reason": "lineage conflict detected" if conflict else "lineage deterministic and replay-verifiable",
        }

    def explain_lineage(self, lineage: SourceArtifactLineage) -> dict[str, Any]:
        return {
            "source_hash": lineage.source_hash,
            "artifact_hash": lineage.artifact_hash,
            "lineage_hash": lineage.lineage_hash,
            "replay_verifiable": lineage.replay_verifiable,
            "notes": [
                "source-to-artifact lineage only",
                "deterministic lineage replay required",
                "lineage conflict blocks verification",
            ],
        }
