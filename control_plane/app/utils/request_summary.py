import hashlib


def summarize_chat_request(messages: list[dict], *, include_reasoning: bool) -> str:
    roles = ",".join(message.get("role", "unknown") for message in messages[:8])
    total_chars = sum(len(message.get("content", "")) for message in messages)
    prompt_fingerprint = _fingerprint(" ".join(message.get("content", "") for message in messages))
    return (
        f"chat messages={len(messages)} roles={roles} chars={total_chars} "
        f"include_reasoning={str(include_reasoning).lower()} prompt_sha256={prompt_fingerprint}"
    )


def summarize_completion_request(prompt: str) -> str:
    return f"completion chars={len(prompt)} prompt_sha256={_fingerprint(prompt)}"


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
