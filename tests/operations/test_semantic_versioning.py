import pytest
from app.services.operations.compatibility_contracts.semantic_versioning import (
    SemanticVersioningService,
)


def test_semver_parsing_and_comparison():
    service = SemanticVersioningService()
    parsed = service.parse_version("1.2.3")
    assert parsed["major"] == 1
    assert service.compare_versions("1.2.3", "1.3.0")["order"] == -1
    assert service.is_backward_compatible("1.2.3", "1.3.0") is True
    assert service.is_forward_compatible("1.2.3", "1.3.0") is False
    assert service.is_bidirectional_compatible("1.2.3", "1.2.9") is True


def test_semver_rejects_invalid_version():
    service = SemanticVersioningService()
    with pytest.raises(ValueError):
        service.parse_version("1.2")
