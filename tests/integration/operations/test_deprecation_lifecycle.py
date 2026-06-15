import pytest
from app.services.operations.compatibility_contracts.deprecation_lifecycle import (
    DeprecationLifecycleService,
)


def test_deprecation_requires_replacement_when_migration_required():
    service = DeprecationLifecycleService()
    with pytest.raises(ValueError):
        service.propose_deprecation(
            {"id": "c1", "migration_required": True, "replacement_contract": None}
        )


def test_deprecation_enforcement_transitions():
    service = DeprecationLifecycleService()
    result = service.enforce_deprecation(
        {"id": "c1", "migration_required": True, "replacement_contract": "c2"}
    )
    assert result["deprecation_status"] == "enforced"
