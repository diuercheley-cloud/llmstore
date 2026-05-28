# Owner: agent-platform
from typing import Any


class MCPAuditLog:
    events: list[dict[str, Any]] = []

    @classmethod
    def record(cls, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {"event_type": event_type, **payload}
        cls.events.append(event)
        return event
