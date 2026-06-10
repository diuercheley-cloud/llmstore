from app.services.operations.compatibility_contracts.version_negotiation import (
    VersionNegotiationService,
)


def test_version_negotiation_blocks_incompatible_versions():
    service = VersionNegotiationService()
    accepted = service.negotiate("1.2.0", "1.3.0")
    conflicted = service.negotiate("1.2.0", "2.0.0")
    assert accepted["negotiation_status"] == "accepted"
    assert accepted["negotiated_version"] == "1.2.0"
    assert service.validate_negotiated_version(accepted) is True
    assert conflicted["negotiation_status"] == "conflicted"
    assert service.resolve_conflict(conflicted)["resolution_status"] == "rejected"
