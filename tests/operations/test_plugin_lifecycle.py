from uuid import uuid4

import pytest

from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.lifecycle import PluginLifecycleService


def test_lifecycle_requires_reason_for_revoke_and_block():
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
    service = PluginLifecycleService()
    with pytest.raises(ValueError):
        service.revoke_plugin(contract, "")
    event = service.block_plugin(contract, "unsafe")
    assert event.lifecycle_event_type == "blocked"
    assert contract.contract_status == "blocked"
