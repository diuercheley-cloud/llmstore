import json
from typing import Any


def normalize_chat_completion(payload: dict[str, Any], *, include_reasoning: bool) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "id": payload.get("id"),
        "object": payload.get("object", "chat.completion"),
        "created": payload.get("created"),
        "model": payload.get("model"),
        "choices": [_normalize_choice(item, include_reasoning=include_reasoning) for item in payload.get("choices", [])],
    }
    if "usage" in payload:
        normalized["usage"] = payload["usage"]
    if "system_fingerprint" in payload:
        normalized["system_fingerprint"] = payload["system_fingerprint"]
    return normalized


def normalize_chat_stream_line(line: str, *, include_reasoning: bool) -> str | None:
    if not line.startswith("data: "):
        return line
    if line == "data: [DONE]":
        return line

    payload = json.loads(line.removeprefix("data: "))
    normalized = normalize_chat_completion(payload, include_reasoning=include_reasoning)

    choices = normalized.get("choices", [])
    if choices:
        choice = choices[0]
        delta = choice.get("delta")
        if delta == {} and choice.get("finish_reason") is None:
            return None
    return f"data: {json.dumps(normalized, ensure_ascii=False)}"


def _normalize_choice(choice: dict[str, Any], *, include_reasoning: bool) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "index": choice.get("index", 0),
        "finish_reason": choice.get("finish_reason"),
    }
    if "message" in choice:
        normalized["message"] = _normalize_message(choice.get("message") or {}, include_reasoning=include_reasoning)
    if "delta" in choice:
        normalized["delta"] = _normalize_message(choice.get("delta") or {}, include_reasoning=include_reasoning)
    if "text" in choice:
        normalized["text"] = choice.get("text")
    if "logprobs" in choice:
        normalized["logprobs"] = choice.get("logprobs")
    return normalized


def _normalize_message(message: dict[str, Any], *, include_reasoning: bool) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if "role" in message:
        normalized["role"] = message.get("role")
    if "content" in message:
        normalized["content"] = message.get("content")
    elif "text" in message:
        normalized["content"] = message.get("text")
    if include_reasoning and "reasoning_content" in message:
        normalized["reasoning_content"] = message.get("reasoning_content")
    if "tool_calls" in message:
        normalized["tool_calls"] = message.get("tool_calls")
    return normalized
