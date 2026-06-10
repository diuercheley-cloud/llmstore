from app.services.operations.reproducible_builds.audit_events import (
    build_reproducible_build_audit_event,
)


def test_audit_event_sanitizes_payload():
    event = build_reproducible_build_audit_event(
        "artifact_verified",
        "tenant-a",
        {"artifact_verification_id": "a" * 64, "payload": {"secret": "value"}},
    )
    assert event["payload"]["payload"] == "redacted"
    assert event["offline_compatible"] is True
