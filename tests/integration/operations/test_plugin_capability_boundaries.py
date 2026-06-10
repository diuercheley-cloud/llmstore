from uuid import uuid4

from app.services.operations.plugin_runtime.capability_boundaries import (
    PluginCapabilityBoundaryService,
)


def test_denied_capabilities_take_precedence():
    service = PluginCapabilityBoundaryService()
    boundary = service.build_boundary(
        {
            "client_id": uuid4(),
            "abi_contract_id": "c" * 64,
            "allowed_capabilities_json": ["read_logs", "network", "shell"],
            "denied_capabilities_json": ["read_logs"],
        }
    )
    evaluation = service.evaluate_capabilities(boundary)
    assert "shell" in evaluation["denied_capabilities"]
    assert "network" in evaluation["denied_capabilities"]
    assert "read_logs" not in evaluation["allowed_capabilities"]
    assert service.validate_boundary(boundary)["valid"] is True
