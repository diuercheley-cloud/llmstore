from uuid import uuid4

from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.federation_compatibility import PluginFederationCompatibilityService


def test_federation_compatibility_requires_replay_safe():
    contract = PluginABIContractService().create_contract(
        {
            "client_id": uuid4(),
            "plugin_name": "plugin",
            "plugin_version": "1.0.0",
            "abi_version": "1.0.0",
            "schema_version": "1.0.0",
            "contract_scope": "federation",
            "contract_status": "active",
        }
    )
    service = PluginFederationCompatibilityService()
    result = service.evaluate_federation_compatibility(contract, "cluster-a", "cluster-b")
    assert result.replay_safe is True
    assert result.federation_status == "warning"
