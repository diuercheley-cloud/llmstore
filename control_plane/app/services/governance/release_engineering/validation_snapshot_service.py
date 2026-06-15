import hashlib
import json
from datetime import UTC, datetime
from typing import Any


class ValidationSnapshotService:
    def create_snapshot(
        self, baseline_id: str, scope: str, results: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Creates a deterministic validation snapshot.
        """
        snapshot_data = {
            "baseline_id": baseline_id,
            "validation_scope": scope,
            "validation_results": results,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        snapshot_json = json.dumps(snapshot_data, sort_keys=True)
        snapshot_hash = hashlib.sha256(snapshot_json.encode()).hexdigest()

        snapshot_data["snapshot_hash"] = snapshot_hash
        snapshot_data["immutable_hash"] = snapshot_hash  # Same for baseline

        return snapshot_data

    def verify_snapshot(self, snapshot: dict[str, Any]) -> bool:
        """
        Verifies the integrity of a validation snapshot.
        """
        data_to_verify = snapshot.copy()
        snapshot_hash = data_to_verify.pop("snapshot_hash", None)
        data_to_verify.pop("immutable_hash", None)

        if not snapshot_hash:
            return False

        calculated_hash = hashlib.sha256(
            json.dumps(data_to_verify, sort_keys=True).encode()
        ).hexdigest()
        return calculated_hash == snapshot_hash
