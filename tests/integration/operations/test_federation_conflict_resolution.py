import uuid

from app.services.operations.federation_sync.conflict_resolution import (
    FederationConflictResolutionService,
)
from app.services.operations.federation_sync.environment_registry import (
    SovereignFederationEnvironmentRegistry,
)
from app.services.operations.federation_sync.synchronization_protocol import (
    SovereignFederationSynchronizationProtocol,
)


def test_conflict_resolution_deterministic_and_blocking():
    registry = SovereignFederationEnvironmentRegistry()
    protocol = SovereignFederationSynchronizationProtocol()
    service = FederationConflictResolutionService()
    client_id = uuid.uuid4()
    source = registry.register_environment(
        {
            "client_id": client_id,
            "environment_name": "source",
            "environment_type": "airgap_node",
            "federation_scope": "ops",
        }
    )
    target = registry.register_environment(
        {
            "client_id": client_id,
            "environment_name": "target",
            "environment_type": "offline_staging",
            "federation_scope": "ops",
        }
    )
    session = protocol.create_sync_session(source, target)
    source_bundle = protocol.export_bundle(
        session, {"bundle_name": "a", "bundle_type": "mixed", "payload": {"x": 1}}
    )
    target_bundle = protocol.export_bundle(
        session, {"bundle_name": "a", "bundle_type": "mixed", "payload": {"x": 2}}
    )
    conflicts = service.detect_conflicts(source_bundle, target_bundle)
    assert any(item["conflict_type"] == "bundle_hash_conflict" for item in conflicts)
    merge = service.resolve_conflict(
        {"conflict_type": "bundle_hash_conflict", "client_id": client_id, "session_id": session.id},
        "deterministic_merge",
    )
    manual = service.resolve_conflict(
        {"conflict_type": "bundle_hash_conflict", "client_id": client_id, "session_id": session.id},
        "manual_review_required",
    )
    lineage = service.resolve_conflict(
        {"conflict_type": "lineage_conflict", "client_id": client_id, "session_id": session.id},
        "keep_source",
    )
    assert merge.replay_safe is True
    assert service.validate_resolution(manual)["finalize_blocked"] is True
    assert lineage.resolution_status == "blocked"
