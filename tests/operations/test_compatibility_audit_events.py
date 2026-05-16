import pytest

from app.services.operations.compatibility_contracts.audit_events import build_compatibility_audit_event


def test_compatibility_audit_event_sanitizes_payload():
    event = build_compatibility_audit_event(
        "compatibility_contract_created",
        "tenant",
        {"contract_id": "c1", "secret_token": "abc"},
    )
    assert event["payload"]["secret_token"] == "redacted"
    assert event["offline_compatible"] is True


def test_compatibility_audit_event_rejects_unknown_event():
    with pytest.raises(ValueError):
        build_compatibility_audit_event("unknown", "tenant", {})
