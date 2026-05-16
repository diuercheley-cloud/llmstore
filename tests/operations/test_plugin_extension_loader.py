import json
from uuid import uuid4

from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.extension_loader import DeterministicExtensionLoader


def test_deterministic_load_order_and_no_execution():
    service = PluginABIContractService()
    second = service.create_contract(
        {
            "client_id": uuid4(),
            "plugin_name": "zeta",
            "plugin_version": "1.0.0",
            "abi_version": "1.0.0",
            "schema_version": "1.0.0",
            "contract_scope": "workflow",
            "contract_status": "active",
        }
    )
    first = service.create_contract(
        {
            "client_id": second.client_id,
            "plugin_name": "alpha",
            "plugin_version": "1.0.0",
            "abi_version": "1.0.0",
            "schema_version": "1.0.0",
            "contract_scope": "workflow",
            "contract_status": "active",
        }
    )
    loader = DeterministicExtensionLoader()
    plans = loader.build_load_plan([second, first])
    assert json.loads(plans[0].load_order)[0]["plugin_name"] == "alpha"
    simulation = loader.simulate_load(plans[0])
    assert simulation["executed_plugins"] == 0
    assert simulation["dry_run"] is True
