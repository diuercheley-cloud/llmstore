# Owner: agent-platform
"""
MCP Audit Log

Records every MCP lifecycle event with timestamps, tenant context,
and enough detail for security reviews.

Events stored in memory (for tests and short-lived processes).
In production, this should be shipped to a persistent audit sink.
"""

from __future__ import annotations

import time
from typing import Any


class MCPAuditLog:
    events: list[dict[str, Any]] = []

    @classmethod
    def record(
        cls,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str | None = None,
        server_id: str | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "event_type": event_type,
            "timestamp": time.time(),
        }
        if tenant_id:
            event["tenant_id"] = tenant_id
        if server_id:
            event["server_id"] = server_id
        event.update(payload)
        cls.events.append(event)
        return event

    @classmethod
    def list_events(
        cls,
        event_type: str | None = None,
        tenant_id: str | None = None,
        server_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        out = cls.events
        if event_type:
            out = [e for e in out if e.get("event_type") == event_type]
        if tenant_id:
            out = [e for e in out if e.get("tenant_id") == tenant_id]
        if server_id:
            out = [e for e in out if e.get("server_id") == server_id]
        return out[-limit:]

    @classmethod
    def clear(cls) -> None:
        cls.events.clear()
