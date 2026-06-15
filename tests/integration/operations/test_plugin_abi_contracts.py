from uuid import uuid4

import pytest
from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService


def test_plugin_abi_contract_service_create_and_validate():
    service = PluginABIContractService()
    contract = service.create_contract(
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
    validation = service.validate_contract(contract)
    assert validation["valid"] is True
    assert (
        service.explain_contract(contract)["notes"][1]
        == "placeholder_certified is not real certification"
    )


def test_plugin_abi_contract_block_and_deprecate_require_reason():
    service = PluginABIContractService()
    contract = service.create_contract(
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
    with pytest.raises(ValueError):
        service.block_contract(contract, "")
    service.deprecate_contract(contract, "sunset")
    assert contract.contract_status == "deprecated"
