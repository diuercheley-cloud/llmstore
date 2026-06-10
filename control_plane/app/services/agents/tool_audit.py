"""
Owner: agent-platform
Status: beta
"""
import logging
from typing import Any, Dict, Optional

from app.models.agents.agent_tool_execution import AgentToolExecutionAudit
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def sanitize_payload(data: Any) -> Any:
    """Recursively redacts sensitive keys and values from parameter payloads and details."""
    import uuid
    from datetime import date, datetime
    if isinstance(data, uuid.UUID):
        return str(data)
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = k.lower()
            if any(p in k_lower for p in ["api_key", "secret", "password", "token", "authorization", "credential", "private_key"]):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    elif isinstance(data, str):
        # Detect typical secret keys or prefixes
        if data.startswith("sk-") or ("eyj" in data.lower() and len(data) > 40):
            return "[REDACTED]"
        return data
    return data


async def log_audit_event(
    db: AsyncSession,
    tenant_id: str,
    event_type: str,
    invocation_id: Optional[Any] = None,
    agent_id: Optional[Any] = None,
    agent_tool_id: Optional[Any] = None,
    decision: Optional[str] = None,
    reason: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AgentToolExecutionAudit:
    """Creates a sanitized audit log record for security, policy, and tool decisions."""
    sanitized_details = sanitize_payload(details) if details else None

    # Redact raw secrets from reason if any leaked there
    clean_reason = reason
    if reason and any(p in reason.lower() for p in ["sk-", "secret", "password", "key"]):
        clean_reason = "[REDACTED reason containing potential secrets]"

    audit_entry = AgentToolExecutionAudit(
        invocation_id=invocation_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_tool_id=agent_tool_id,
        event_type=event_type,
        decision=decision,
        reason=clean_reason,
        details=sanitized_details,
    )
    
    db.add(audit_entry)
    await db.flush()
    
    logger.info(
        f"[AUDIT] Tenant: {tenant_id} | Event: {event_type} | Decision: {decision} | Reason: {clean_reason}"
    )
    return audit_entry
