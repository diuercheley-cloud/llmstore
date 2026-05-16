from uuid import uuid4

from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.extension_loader import DeterministicExtensionLoader
from app.services.operations.plugin_runtime.replay_verifier import PluginReplayVerifier


def test_replay_verification_for_contract_and_load_plan():
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
    verifier = PluginReplayVerifier()
    assert verifier.replay_contract(contract)["match"] is True
    load_plan = DeterministicExtensionLoader().build_load_plan([contract])[0]
    assert verifier.replay_load_plan(load_plan)["match"] is True
