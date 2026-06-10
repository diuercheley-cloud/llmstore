from app.services.operations.attestation_framework.audit_events import build_attestation_audit_event


def test_attestation_audit_events_redact_sensitive_payload():
    event = build_attestation_audit_event(
        "attestation_issued",
        "client-1",
        {"attestation_id": "att-1", "secret_token": "abc", "payload_hash": "123"},
    )
    assert event["event_type"] == "attestation_issued"
    assert event["offline_compatible"] is True
    assert event["payload"]["secret_token"] == "redacted"
    assert event["payload"]["payload_hash"] == "redacted"
