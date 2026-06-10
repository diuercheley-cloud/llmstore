import pytest
from app.services.operations.federation_sync.audit_events import (
    FEDERATION_SYNC_AUDIT_EVENTS,
    build_federation_sync_audit_event,
)


def test_federation_audit_events_sanitize():
    event = build_federation_sync_audit_event(
        "federation_bundle_exported",
        "client-1",
        {"bundle_id": "b1", "secret_token": "hidden", "payload": {"x": 1}},
    )
    assert event["payload"]["secret_token"] == "redacted"
    assert event["payload"]["payload"] == "redacted"
    assert event["offline_compatible"] is True
    assert "federation_receipt_created" in FEDERATION_SYNC_AUDIT_EVENTS


def test_federation_audit_event_rejects_unknown_type():
    with pytest.raises(ValueError):
        build_federation_sync_audit_event("unknown", "client-1", {})
