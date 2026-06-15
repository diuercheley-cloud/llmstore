from typing import Any

from app.models.operations.federation_sync import FederationConflictResolution
from app.services.operations.federation_sync.hash_utils import sha256_hex


class FederationConflictResolutionService:
    def detect_conflicts(self, source_bundle: Any, target_bundle: Any) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        if source_bundle.lineage_hash != target_bundle.lineage_hash:
            conflicts.append({"conflict_type": "lineage_conflict", "replay_safe": False})
        if source_bundle.bundle_hash != target_bundle.bundle_hash:
            conflicts.append({"conflict_type": "bundle_hash_conflict", "replay_safe": False})
        if source_bundle.replay_hash != target_bundle.replay_hash:
            conflicts.append({"conflict_type": "replay_conflict", "replay_safe": False})
        if getattr(source_bundle, "bundle_type", "") != getattr(target_bundle, "bundle_type", ""):
            conflicts.append({"conflict_type": "version_conflict", "replay_safe": True})
        return conflicts

    def resolve_conflict(
        self, conflict: dict[str, Any], strategy: str
    ) -> FederationConflictResolution:
        conflict_type = conflict["conflict_type"]
        if (
            conflict_type == "lineage_conflict"
            and strategy != "reject"
            or conflict_type == "replay_conflict"
            or strategy == "manual_review_required"
        ):
            status = "blocked"
            replay_safe = False
        else:
            status = (
                "resolved"
                if strategy in {"reject", "deterministic_merge", "keep_source", "keep_target"}
                else "proposed"
            )
            replay_safe = strategy == "deterministic_merge" and conflict_type not in {
                "lineage_conflict",
                "replay_conflict",
            }
        return FederationConflictResolution(
            id=sha256_hex(
                {
                    "kind": "federation_conflict_id",
                    "conflict_type": conflict_type,
                    "strategy": strategy,
                }
            ),
            client_id=conflict["client_id"],
            session_id=conflict["session_id"],
            conflict_type=conflict_type,
            resolution_strategy=strategy,
            resolution_status=status,
            replay_safe=replay_safe,
            immutable_hash=sha256_hex(
                {
                    "kind": "federation_conflict_immutable",
                    "conflict_type": conflict_type,
                    "strategy": strategy,
                    "status": status,
                }
            ),
        )

    def validate_resolution(self, resolution: FederationConflictResolution) -> dict[str, Any]:
        blocked = resolution.resolution_status == "blocked"
        return {
            "valid": not blocked or resolution.resolution_strategy == "reject",
            "blocked": blocked,
            "finalize_blocked": blocked
            or resolution.resolution_strategy == "manual_review_required",
            "replay_safe": resolution.replay_safe,
        }

    def explain_resolution(self, resolution: FederationConflictResolution) -> dict[str, Any]:
        return {
            "conflict_type": resolution.conflict_type,
            "resolution_strategy": resolution.resolution_strategy,
            "resolution_status": resolution.resolution_status,
            "rules": [
                "deterministic_merge is deterministic",
                "lineage conflicts cannot be ignored",
                "replay conflict blocks verification",
                "manual review blocks finalize_session",
            ],
        }
