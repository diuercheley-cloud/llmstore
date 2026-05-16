import uuid

from app.services.operations.federation_sync.environment_registry import SovereignFederationEnvironmentRegistry
from app.services.operations.federation_sync.replay_verifier import FederationReplayVerifier
from app.services.operations.federation_sync.synchronization_protocol import SovereignFederationSynchronizationProtocol


def test_replay_verifier_bundle_and_session():
    registry = SovereignFederationEnvironmentRegistry()
    protocol = SovereignFederationSynchronizationProtocol()
    verifier = FederationReplayVerifier()
    client_id = uuid.uuid4()
    source = registry.register_environment({"client_id": client_id, "environment_name": "source", "environment_type": "airgap_node", "federation_scope": "ops"})
    target = registry.register_environment({"client_id": client_id, "environment_name": "target", "environment_type": "offline_staging", "federation_scope": "ops"})
    session = protocol.create_sync_session(source, target)
    bundle = protocol.export_bundle(session, {"bundle_name": "bundle", "bundle_type": "mixed", "payload": {"ok": True}})
    assert verifier.replay_session(session)["match"] is True
    assert verifier.replay_bundle(bundle)["match"] is True
