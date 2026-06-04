from app.services.governance.data_governance.data_minimization_checker import (
    check_payload_for_sensitive_keys,
)


def sanitize_observability_payload(payload: dict) -> dict:
    redacted = dict(payload)
    for key in check_payload_for_sensitive_keys(payload):
        redacted[key] = "[redacted]"
    return redacted

