from typing import Any

from app.core.time import utc_now
from app.models.operations.federation_sync import (
    FederationSynchronizationBundle,
    FederationSynchronizationSession,
)
from app.services.operations.federation_sync.hash_utils import (
    compute_bundle_hash,
    compute_lineage_hash,
    compute_session_hash,
    sha256_hex,
)


class SovereignFederationSynchronizationProtocol:
    def create_sync_session(self, source: Any, target: Any) -> FederationSynchronizationSession:
        logical_payload = {
            "client_id": str(source.client_id),
            "source_environment_id": source.id,
            "target_environment_id": target.id,
            "sync_scope": source.federation_scope,
            "replay_verifiable": True,
            "offline_verifiable": True,
            "lineage_verified": False,
            "deterministic_version": getattr(source, "deterministic_version", "v1"),
        }
        session_hash = compute_session_hash(logical_payload)
        return FederationSynchronizationSession(
            id=sha256_hex({"kind": "federation_session_id", **logical_payload}),
            client_id=source.client_id,
            source_environment_id=source.id,
            target_environment_id=target.id,
            sync_scope=source.federation_scope,
            sync_status="proposed",
            replay_verifiable=True,
            offline_verifiable=True,
            lineage_verified=False,
            deterministic_version=logical_payload["deterministic_version"],
            session_hash=session_hash,
            immutable_hash=sha256_hex(
                {"kind": "federation_session_immutable", "session_hash": session_hash}
            ),
            started_at=utc_now(),
        )

    def export_bundle(
        self, session: FederationSynchronizationSession, bundle: dict[str, Any]
    ) -> FederationSynchronizationBundle:
        logical_payload = {
            "client_id": str(session.client_id),
            "session_id": session.id,
            "bundle_name": bundle["bundle_name"],
            "bundle_type": bundle["bundle_type"],
            "parent_bundle_hash": bundle.get("parent_bundle_hash"),
            "payload": bundle.get("payload", {}),
            "deterministic_version": session.deterministic_version,
        }
        bundle_hash = compute_bundle_hash(logical_payload)
        lineage_hash = compute_lineage_hash(
            {
                "bundle_hash": bundle_hash,
                "parent_bundle_hash": bundle.get("parent_bundle_hash"),
                "session_hash": session.id,
            }
        )
        exported = FederationSynchronizationBundle(
            id=sha256_hex({"kind": "federation_bundle_id", "bundle_hash": bundle_hash}),
            client_id=session.client_id,
            session_id=session.id,
            bundle_name=bundle["bundle_name"],
            bundle_type=bundle["bundle_type"],
            bundle_hash=bundle_hash,
            lineage_hash=lineage_hash,
            parent_bundle_hash=bundle.get("parent_bundle_hash"),
            replay_hash=bundle_hash,
            bundle_status="exported",
            immutable_hash=sha256_hex(
                {
                    "kind": "federation_bundle_immutable",
                    "bundle_hash": bundle_hash,
                    "lineage_hash": lineage_hash,
                }
            ),
        )
        exported._logical_payload = logical_payload
        session.sync_status = "exported"
        return exported

    def import_bundle(
        self, session: FederationSynchronizationSession, bundle: FederationSynchronizationBundle
    ) -> FederationSynchronizationBundle:
        verification = self.verify_bundle(bundle)
        if not verification["verified"]:
            bundle.bundle_status = "conflicted"
            session.sync_status = "conflicted"
            return bundle
        bundle.bundle_status = "imported"
        session.sync_status = "imported"
        session.lineage_verified = verification["lineage_verified"]
        return bundle

    def verify_bundle(self, bundle: FederationSynchronizationBundle) -> dict[str, Any]:
        logical_payload = getattr(bundle, "_logical_payload", None) or {
            "client_id": str(bundle.client_id),
            "session_id": bundle.session_id,
            "bundle_name": bundle.bundle_name,
            "bundle_type": bundle.bundle_type,
            "parent_bundle_hash": bundle.parent_bundle_hash,
            "payload": {},
            "deterministic_version": "v1",
        }
        replay_hash = compute_bundle_hash(logical_payload)
        lineage_hash = compute_lineage_hash(
            {
                "bundle_hash": bundle.bundle_hash,
                "parent_bundle_hash": bundle.parent_bundle_hash,
                "session_hash": logical_payload["session_id"],
            }
        )
        replay_ok = replay_hash == bundle.replay_hash
        lineage_ok = lineage_hash == bundle.lineage_hash
        return {
            "verified": replay_ok and lineage_ok,
            "replay_verified": replay_ok,
            "offline_verified": True,
            "lineage_verified": lineage_ok,
            "expected_replay_hash": replay_hash,
            "expected_lineage_hash": lineage_hash,
        }

    def finalize_session(
        self, session: FederationSynchronizationSession, blocking_conflicts: list[Any] | None = None
    ) -> FederationSynchronizationSession:
        blockers = blocking_conflicts or []
        if any(
            conflict.resolution_strategy == "manual_review_required"
            or conflict.resolution_status == "blocked"
            for conflict in blockers
        ):
            session.sync_status = "conflicted"
            return session
        if (
            not session.replay_verifiable
            or not session.offline_verifiable
            or not session.lineage_verified
        ):
            session.sync_status = "rejected"
            return session
        session.sync_status = "verified"
        session.completed_at = utc_now()
        return session

    def explain_session(self, session: FederationSynchronizationSession) -> dict[str, Any]:
        return {
            "session_id": session.id,
            "sync_scope": session.sync_scope,
            "sync_status": session.sync_status,
            "replay_verifiable": session.replay_verifiable,
            "offline_verifiable": session.offline_verifiable,
            "lineage_verified": session.lineage_verified,
            "notes": [
                "deterministic replay required",
                "offline verification required",
                "lineage verification required",
                "no mandatory network",
            ],
        }
