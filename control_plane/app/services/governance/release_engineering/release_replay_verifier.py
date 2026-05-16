from typing import Dict, Any
from .release_manifest_service import ReleaseManifestService
from .validation_snapshot_service import ValidationSnapshotService

class ReleaseReplayVerifier:
    def __init__(self):
        self.manifest_service = ReleaseManifestService()
        self.snapshot_service = ValidationSnapshotService()

    def verify_release_replay(self, manifest: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies if a release can be replayed deterministically.
        """
        manifest_valid = self.manifest_service.verify_manifest(manifest)
        snapshot_valid = self.snapshot_service.verify_snapshot(snapshot)
        
        replay_safe = manifest.get("replay_safe", False)
        hashes_match = manifest.get("snapshot_hash") == snapshot.get("snapshot_hash")
        
        return {
            "manifest_integrity": manifest_valid,
            "snapshot_integrity": snapshot_valid,
            "hashes_consistency": hashes_match,
            "replay_safe_marker": replay_safe,
            "overall_status": manifest_valid and snapshot_valid and hashes_match and replay_safe
        }
