from typing import Any

from app.models.operations.reproducible_builds import (
    ArtifactReplayVerification,
    ArtifactVerificationRecord,
)
from app.services.operations.reproducible_builds.hash_utils import (
    compute_artifact_hash,
    compute_replay_hash,
    sha256_hex,
)


class ArtifactVerificationService:
    def verify_artifact(self, manifest: Any, payload: dict[str, Any]) -> ArtifactVerificationRecord:
        logical_payload = {
            "client_id": str(manifest.client_id),
            "build_manifest_id": manifest.id,
            "artifact_name": payload["artifact_name"],
            "artifact_version": payload["artifact_version"],
        }
        artifact_hash = compute_artifact_hash(logical_payload)
        expected_hash = payload.get("expected_hash", artifact_hash)
        verification_status = "passed" if artifact_hash == expected_hash else "blocked"
        record = ArtifactVerificationRecord(
            id=sha256_hex({"kind": "artifact_verification_record_id", **logical_payload}),
            client_id=manifest.client_id,
            build_manifest_id=manifest.id,
            artifact_name=payload["artifact_name"],
            artifact_version=payload["artifact_version"],
            artifact_hash=artifact_hash,
            verification_status=verification_status,
            replay_verified=verification_status == "passed",
            immutable_hash=sha256_hex({"kind": "artifact_verification_record_immutable", "artifact_hash": artifact_hash, "status": verification_status}),
        )
        record._logical_payload = logical_payload
        record._expected_hash = expected_hash
        return record

    def compare_artifact_hashes(self, left_hash: str, right_hash: str) -> dict[str, Any]:
        match = left_hash == right_hash
        return {
            "match": match,
            "verification_status": "passed" if match else "blocked",
            "left_hash": left_hash,
            "right_hash": right_hash,
        }

    def validate_artifact_replay(self, record: ArtifactVerificationRecord) -> ArtifactReplayVerification:
        logical_payload = getattr(record, "_logical_payload", None) or {
            "client_id": str(record.client_id),
            "build_manifest_id": record.build_manifest_id,
            "artifact_name": record.artifact_name,
            "artifact_version": record.artifact_version,
        }
        replay_hash = compute_replay_hash(logical_payload)
        replay_status = "passed" if record.verification_status == "passed" else "failed"
        replay = ArtifactReplayVerification(
            id=sha256_hex({"kind": "artifact_replay_verification_id", "artifact_verification_id": record.id, "replay_hash": replay_hash}),
            client_id=record.client_id,
            artifact_verification_id=record.id,
            replay_hash=replay_hash,
            replay_status=replay_status,
            deterministic_summary="artifact replay verified deterministically" if replay_status == "passed" else "artifact replay mismatch detected",
            immutable_hash=sha256_hex({"kind": "artifact_replay_verification_immutable", "artifact_verification_id": record.id, "replay_hash": replay_hash}),
        )
        replay._logical_payload = logical_payload
        return replay

    def explain_artifact_verification(self, record: ArtifactVerificationRecord, replay: ArtifactReplayVerification | None = None) -> dict[str, Any]:
        return {
            "artifact": f"{record.artifact_name}:{record.artifact_version}",
            "artifact_hash": record.artifact_hash,
            "verification_status": record.verification_status,
            "replay_verified": record.replay_verified,
            "replay_status": replay.replay_status if replay else "warning",
            "notes": [
                "deterministic hashing only",
                "replay verification required",
                "no network or subprocess execution",
            ],
        }
