from uuid import uuid4

from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.capability_boundaries import (
    PluginCapabilityBoundaryService,
)
from app.services.operations.plugin_runtime.isolation_policy import PluginIsolationPolicyService


def test_default_isolation_policy_is_strict():
    policy = PluginIsolationPolicyService().create_default_policy(uuid4())
    assert policy.deny_network is True
    assert policy.deny_subprocess is True
    assert policy.deny_dynamic_import is True


def test_enforce_policy_blocks_sensitive_paths():
    contract = PluginABIContractService().create_contract(
        {
            "client_id": uuid4(),
            "plugin_name": "plugin",
            "plugin_version": "1.0.0",
            "abi_version": "1.0.0",
            "schema_version": "1.0.0",
            "contract_scope": "workflow",
            "contract_status": "active",
        }
    )
    boundary = PluginCapabilityBoundaryService().build_boundary(
        {"client_id": contract.client_id, "abi_contract_id": contract.id}
    )
    enforcement = PluginIsolationPolicyService().enforce_policy(contract, boundary)
    assert enforcement["policy_enforced"] is True
    assert enforcement["no_dynamic_import_external"] is True
