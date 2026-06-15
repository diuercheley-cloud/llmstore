import hashlib
import json
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.core.admin_action_log import AdminActionLog
from sqlalchemy.ext.asyncio import AsyncSession


async def log_operational_audit_event(
    session: AsyncSession,
    action: str,
    client_id: uuid.UUID,
    payload: dict[str, Any],
    status: str = "success",
):
    """
    Logs an operational audit event to the AdminActionLog.
    Follows offline-compatible and advisory-only rules.
    """
    # Sanitize payload: remove sensitive data, ensure it's serializable
    sanitized_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    sanitized_payload["client_id"] = str(client_id)
    sanitized_payload["advisory_only"] = True
    signature_material = json.dumps(
        {"action": action, "client_id": str(client_id), "payload": sanitized_payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    sanitized_payload["signature"] = hashlib.sha256(signature_material.encode("utf-8")).hexdigest()[
        :16
    ]

    audit_entry = AdminActionLog(
        action=f"ops_correlation:{action}",
        admin_role="system",
        request_path="/internal/operations/correlation",
        request_method="SYSTEM",
        payload_json=sanitized_payload,
        status=status,
        created_at=utc_now(),
    )

    session.add(audit_entry)
    return audit_entry


async def log_correlation_created(
    session: AsyncSession, client_id: uuid.UUID, correlation_id: uuid.UUID, correlation_type: str
):
    return await log_operational_audit_event(
        session,
        "operational_correlation_created",
        client_id,
        {"correlation_id": str(correlation_id), "correlation_type": correlation_type},
    )


async def log_trust_link_created(
    session: AsyncSession, client_id: uuid.UUID, source: str, target: str
):
    return await log_operational_audit_event(
        session,
        "operational_trust_link_created",
        client_id,
        {"source_node": source, "target_node": target},
    )


async def log_graph_generated(session: AsyncSession, client_id: uuid.UUID, summary: dict[str, Any]):
    return await log_operational_audit_event(
        session,
        "trust_graph_generated",
        client_id,
        {
            "node_count": summary.get("node_count"),
            "edge_count": summary.get("edge_count"),
            "aggregate_confidence": summary.get("aggregate_confidence"),
        },
    )
