import uuid

from app.services.operations.federation_sync.environment_registry import SovereignFederationEnvironmentRegistry
from app.services.operations.federation_sync.synchronization_protocol import SovereignFederationSynchronizationProtocol


def test_synchronization_protocol_export_import_verify_finalize():
    registry = SovereignFederationEnvironmentRegistry()
    protocol = SovereignFederationSynchronizationProtocol()
    client_id = uuid.uuid4()
    source = registry.register_environment(
        {"client_id": client_id, "environment_name": "source", "environment_type": "airgap_node", "federation_scope": "ops", "trust_level": "trusted"}
    )
    target = registry.register_environment(
        {"client_id": client_id, "environment_name": "target", "environment_type": "offline_staging", "federation_scope": "ops", "trust_level": "verified"}
    )
    session = protocol.create_sync_session(source, target)
    bundle = protocol.export_bundle(session, {"bundle_name": "bundle", "bundle_type": "mixed", "payload": {"x": 1}})
    verified = protocol.verify_bundle(bundle)
    assert verified["verified"] is True
    protocol.import_bundle(session, bundle)
    session.lineage_verified = True
    finalized = protocol.finalize_session(session, [])
    assert finalized.sync_status == "verified"
