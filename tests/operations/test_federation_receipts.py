import uuid

from app.services.operations.federation_sync.environment_registry import SovereignFederationEnvironmentRegistry
from app.services.operations.federation_sync.receipts import (
    build_bundle_receipt,
    build_conflict_resolution_receipt,
    build_sync_session_receipt,
    build_trust_negotiation_receipt,
)
from app.services.operations.federation_sync.synchronization_protocol import SovereignFederationSynchronizationProtocol
from app.services.operations.federation_sync.trust_negotiation import FederationTrustNegotiationService
from app.services.operations.federation_sync.conflict_resolution import FederationConflictResolutionService
from app.utils.crypto_signer import sign_payload


def test_federation_receipts_shape():
    registry = SovereignFederationEnvironmentRegistry()
    protocol = SovereignFederationSynchronizationProtocol()
    trust = FederationTrustNegotiationService()
    conflict_service = FederationConflictResolutionService()
    client_id = uuid.uuid4()
    source = registry.register_environment({"client_id": client_id, "environment_name": "source", "environment_type": "airgap_node", "federation_scope": "ops"})
    target = registry.register_environment({"client_id": client_id, "environment_name": "target", "environment_type": "offline_staging", "federation_scope": "ops"})
    session = protocol.create_sync_session(source, target)
    bundle = protocol.export_bundle(session, {"bundle_name": "bundle", "bundle_type": "mixed", "payload": {}})
    negotiation = trust.negotiate(source, target)
    conflict = conflict_service.resolve_conflict({"conflict_type": "bundle_hash_conflict", "client_id": client_id, "session_id": session.id}, "reject")
    for receipt in (
        build_sync_session_receipt(session),
        build_bundle_receipt(bundle),
        build_trust_negotiation_receipt(negotiation),
        build_conflict_resolution_receipt(conflict),
    ):
        assert receipt["signature"].startswith("placeholder-signature:")
        assert "generated_at" in receipt
