from app.services.operations.adapter_sandbox.contracts import (
    AdapterContract,
    AdapterExecutionRequest,
)


def test_adapter_contract_instantiation():
    contract = AdapterContract(
        adapter_name="test",
        adapter_version="1.0",
        allowed_capabilities=["a"],
        denied_capabilities=["b"]
    )
    assert contract.adapter_name == "test"
    assert "a" in contract.allowed_capabilities

def test_execution_request_defaults():
    req = AdapterExecutionRequest(client_id="c1", action_type="act", target_domain="dom")
    assert req.dry_run is True
    assert req.parameters == {}
