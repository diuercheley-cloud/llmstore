SENSITIVE_KEYS = {"prompt", "response", "secret", "token", "password"}


def check_payload_for_sensitive_keys(payload: dict) -> list[str]:
    return sorted(key for key in payload if key.lower() in SENSITIVE_KEYS)
