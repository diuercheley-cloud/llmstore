import hashlib
import json
from datetime import UTC, datetime
from typing import Any


class ReleaseManifestService:
    def generate_manifest(
        self, version: str, scope: list[str], snapshot_hash: str
    ) -> dict[str, Any]:
        """
        Generates a deterministic release manifest.
        """
        manifest_data = {
            "version": version,
            "scope": sorted(scope),
            "snapshot_hash": snapshot_hash,
            "timestamp": datetime.now(UTC).isoformat(),
            "replay_safe": True,
        }

        manifest_json = json.dumps(manifest_data, sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_json.encode()).hexdigest()

        manifest_data["manifest_hash"] = manifest_hash
        return manifest_data

    def verify_manifest(self, manifest: dict[str, Any]) -> bool:
        """
        Verifies the integrity of a manifest.
        """
        data_to_verify = manifest.copy()
        manifest_hash = data_to_verify.pop("manifest_hash", None)

        if not manifest_hash:
            return False

        calculated_hash = hashlib.sha256(
            json.dumps(data_to_verify, sort_keys=True).encode()
        ).hexdigest()
        return calculated_hash == manifest_hash
