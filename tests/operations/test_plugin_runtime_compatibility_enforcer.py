from uuid import uuid4

from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.compatibility_enforcer import (
    PluginRuntimeCompatibilityEnforcer,
)


def test_incompatible_runtime_blocks_load_plan():
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
    enforcer = PluginRuntimeCompatibilityEnforcer()
    result = enforcer.enforce_compatibility(contract, "2.0.0")
    assert result.compatibility_status == "incompatible"
    assert enforcer.explain_compatibility(result)["load_plan_blocked"] is True
