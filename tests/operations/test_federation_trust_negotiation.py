import uuid

from app.services.operations.federation_sync.environment_registry import SovereignFederationEnvironmentRegistry
from app.services.operations.federation_sync.trust_negotiation import FederationTrustNegotiationService


def test_isolated_trust_blocking_and_verified_requirement():
    registry = SovereignFederationEnvironmentRegistry()
    service = FederationTrustNegotiationService()
    client_id = uuid.uuid4()
    isolated = registry.register_environment(
        {"client_id": client_id, "environment_name": "isolated", "environment_type": "airgap_node", "federation_scope": "ops", "trust_level": "isolated"}
    )
    target = registry.register_environment(
        {"client_id": client_id, "environment_name": "target", "environment_type": "offline_staging", "federation_scope": "ops", "trust_level": "verified"}
    )
    denied = service.negotiate(isolated, target)
    assert denied.negotiation_status == "denied"
    assert service.validate_negotiation(denied)["valid"] is False

    restricted = registry.register_environment(
        {"client_id": client_id, "environment_name": "restricted", "environment_type": "sovereign_cluster", "federation_scope": "ops", "trust_level": "restricted"}
    )
    accepted = service.negotiate(restricted, target)
    assert accepted.replay_verification_required is True
    assert "restricted requires manual review" in " ".join(service.explain_negotiation(accepted)["rules"])
