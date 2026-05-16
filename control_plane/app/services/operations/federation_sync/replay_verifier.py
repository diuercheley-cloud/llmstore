from typing import Any

from app.models.operations.federation_sync import FederationLineageLink, FederationSynchronizationBundle, FederationSynchronizationSession
from app.services.operations.federation_sync.hash_utils import compute_bundle_hash, compute_session_hash


class FederationReplayVerifier:
    def replay_bundle(self, bundle: FederationSynchronizationBundle) -> dict[str, Any]:
        logical_payload = getattr(bundle, "_logical_payload", None) or {
            "client_id": str(bundle.client_id),
            "session_id": bundle.session_id,
            "bundle_name": bundle.bundle_name,
            "bundle_type": bundle.bundle_type,
            "parent_bundle_hash": bundle.parent_bundle_hash,
            "payload": {},
            "deterministic_version": "v1",
        }
        replayed = compute_bundle_hash(logical_payload)
        return self.compare_replay_hashes(bundle.replay_hash, replayed)

    def replay_session(self, session: FederationSynchronizationSession) -> dict[str, Any]:
        replayed = compute_session_hash(
            {
                "client_id": str(session.client_id),
                "source_environment_id": session.source_environment_id,
                "target_environment_id": session.target_environment_id,
                "sync_scope": session.sync_scope,
                "replay_verifiable": session.replay_verifiable,
                "offline_verifiable": session.offline_verifiable,
                "lineage_verified": session.lineage_verified,
                "deterministic_version": session.deterministic_version,
            }
        )
        return self.compare_replay_hashes(session.session_hash, replayed)

    def compare_replay_hashes(self, original: str, replayed: str) -> dict[str, Any]:
        return {"match": original == replayed, "original": original, "replayed": replayed}

    def validate_lineage(self, lineage: list[FederationLineageLink]) -> dict[str, Any]:
        ordered = sorted(lineage, key=lambda item: item.created_at)
        previous = None
        valid = True
        for link in ordered:
            if link.parent_bundle_hash != previous:
                valid = False
                break
            previous = link.lineage_hash
        return {"valid": valid, "chain_length": len(ordered), "replay_verifiable": all(item.replay_verifiable for item in ordered)}
