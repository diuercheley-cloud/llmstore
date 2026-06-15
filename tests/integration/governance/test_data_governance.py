from app.services.governance.data_governance.data_minimization_checker import (
    check_payload_for_sensitive_keys,
)
from app.services.governance.data_governance.export_governance_service import build_export_hash


def test_data_governance_flags_sensitive_keys():
    assert check_payload_for_sensitive_keys({"token": "x", "safe": "y"}) == ["token"]


def test_data_governance_export_hash_is_deterministic():
    first = build_export_hash("tenant-1", "reports", True, "advisory")
    second = build_export_hash("tenant-1", "reports", True, "advisory")
    assert first == second
