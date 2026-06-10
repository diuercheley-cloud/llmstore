from app.services.operations.compatibility_contracts.capability_negotiation import (
    CapabilityNegotiationService,
)


def test_capability_denial_precedence():
    service = CapabilityNegotiationService()
    result = service.negotiate_capabilities(
        ["read_logs", "shell", "network"],
        ["read_logs", "shell", "network", "metrics"],
    )
    assert result["approved_capabilities"] == ["read_logs"]
    assert "shell" in result["denied_capabilities"]
    assert "network" in result["denied_capabilities"]
    assert service.validate_capabilities(result) is True
