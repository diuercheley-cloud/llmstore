from app.services.operations.observability.metric_recorder import (
    build_metric_hash,
    validate_metric_payload,
)
from app.services.operations.observability.observability_sanitizer import (
    sanitize_observability_payload,
)


def test_observability_sanitizes_sensitive_payload():
    sanitized = sanitize_observability_payload({"token": "secret", "metric": "cpu"})
    assert sanitized["token"] == "[redacted]"


def test_observability_metric_hash_is_deterministic():
    assert build_metric_hash("tenant", "cpu", "node", "0.4") == build_metric_hash("tenant", "cpu", "node", "0.4")
    assert validate_metric_payload({"password": "x"}) == ["password"]

