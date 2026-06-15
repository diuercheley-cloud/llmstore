from app.models.operations.adapter_registry import AdapterRegistryPolicy
from app.models.operations.adapter_sandbox import AdapterManifest
from app.services.operations.adapter_registry.policy_engine import AdapterRegistryPolicyEngine


class TestAdapterRegistryPolicyEngine:
    def test_evaluate_manifest_valid(self):
        engine = AdapterRegistryPolicyEngine()
        manifest = AdapterManifest(
            adapter_type="remediation",
            sandbox_required=True,
            dry_run_default=True,
            network_access_allowed=False,
            subprocess_allowed=False,
            external_system_access_allowed=False,
            capabilities_json={"requested": ["read"]},
        )
        policy = AdapterRegistryPolicy(
            allowed_adapter_types_json={"allowed_types": ["remediation"]},
            denied_capabilities_json={"denied": ["network_admin"]},
            require_approval=True,
        )

        allowed, reason = engine.evaluate_manifest(manifest, policy)
        assert allowed is True
        assert "complies" in reason

    def test_evaluate_manifest_invalid_sandbox(self):
        engine = AdapterRegistryPolicyEngine()
        manifest = AdapterManifest(
            adapter_type="remediation",
            sandbox_required=False,
            dry_run_default=True,
            network_access_allowed=False,
            subprocess_allowed=False,
            external_system_access_allowed=False,
        )
        policy = AdapterRegistryPolicy(
            allowed_adapter_types_json={"allowed_types": ["remediation"]},
            denied_capabilities_json={"denied": []},
        )

        allowed, reason = engine.evaluate_manifest(manifest, policy)
        assert allowed is False
        assert "sandbox_required=False is blocked" in reason

    def test_evaluate_manifest_denied_capability(self):
        engine = AdapterRegistryPolicyEngine()
        manifest = AdapterManifest(
            adapter_type="remediation",
            sandbox_required=True,
            dry_run_default=True,
            network_access_allowed=False,
            subprocess_allowed=False,
            external_system_access_allowed=False,
            capabilities_json={"requested": ["root_access"]},
        )
        policy = AdapterRegistryPolicy(
            allowed_adapter_types_json={"allowed_types": ["remediation"]},
            denied_capabilities_json={"denied": ["root_access"]},
        )

        allowed, reason = engine.evaluate_manifest(manifest, policy)
        assert allowed is False
        assert "explicitly denied" in reason
