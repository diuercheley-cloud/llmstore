import uuid

from app.services.operations.federation_sync.environment_registry import SovereignFederationEnvironmentRegistry


def test_environment_registry_defaults_and_explanation():
    registry = SovereignFederationEnvironmentRegistry()
    env = registry.register_environment(
        {
            "client_id": uuid.uuid4(),
            "environment_name": "airgap-a",
            "environment_type": "airgap_node",
            "federation_scope": "ops",
        }
    )
    assert env.offline_only is True
    assert registry.verify_environment(env)["placeholder_trust_only"] is True
    assert "placeholder trust only" in " ".join(registry.explain_environment(env)["notes"])
