import uuid
from datetime import datetime, timezone

from app.models.core.security_event import SecurityEvent
from app.services.security_monitor import prompt_fingerprint, serialize_security_event


def test_prompt_fingerprint_is_stable():
    first = prompt_fingerprint("prompto grande repetido")
    second = prompt_fingerprint("prompto grande repetido")

    assert first == second


def test_serialize_security_event_preserves_details():
    now = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    event = SecurityEvent(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        event_type="invalid_api_key_attempts",
        severity="high",
        correlation_id="corr-123",
        source_ip="127.0.0.1",
        api_key_prefix="sk-local-abc",
        title="Many invalid API key attempts",
        detail_json='{"attempts": 5}',
        created_at=now,
    )

    payload = serialize_security_event(event)

    assert payload["event_type"] == "invalid_api_key_attempts"
    assert payload["details"]["attempts"] == 5
    assert payload["correlation_id"] == "corr-123"
    assert payload["created_at"] == now.isoformat()
