from app.services.operations.compatibility_contracts.compatibility_matrix import (
    CompatibilityMatrixService,
)


def test_matrix_upgrade_and_downgrade_rules():
    service = CompatibilityMatrixService()
    upgrade = service.build_matrix("1.2.0", "1.3.0")
    downgrade = service.build_matrix("1.3.0", "1.2.0")
    blocked = service.build_matrix("1.2.0", "2.0.0")
    assert upgrade["compatibility_type"] == "backward"
    assert upgrade["upgrade_supported"] is True
    assert downgrade["compatibility_status"] == "warning"
    assert downgrade["downgrade_supported"] is False
    assert blocked["compatibility_status"] == "incompatible"
    assert blocked["replay_safe"] is False
