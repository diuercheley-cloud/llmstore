# Owner: agent-platform
import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.services.agents.streaming.websocket_manager import ws_manager

logger = logging.getLogger("run_event_stream")

SECRET_REGEXES = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"token-[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"password=[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
]


def sanitize_string(val: str) -> str:
    for pattern in SECRET_REGEXES:
        val = pattern.sub("[REDACTED]", val)
    return val


def sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if any(
                term in k.lower()
                for term in ["token", "secret", "key", "password", "auth", "db_url", "database"]
            ):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        return sanitize_string(payload)
    return payload


class RunEventStreamService:
    @staticmethod
    async def publish_run_event(
        run_id: str, event_type: str, data: dict[str, Any], session_id: str | None = None
    ):
        from app.services.security.pii_gateway import pii_gateway

        sanitized_data = pii_gateway.redact_payload(data)
        event = {
            "event": event_type,
            "run_id": run_id,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": sanitized_data,
        }
        logger.debug(f"Streaming event {event_type} for run {run_id} (session_id: {session_id})")
        await ws_manager.broadcast(run_id, event)
        if session_id:
            await ws_manager.broadcast(f"session:{session_id}", event)
