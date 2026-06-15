import logging
import uuid
from typing import Any

from app.models.agents.agent_iam import AgentCredentialAuditEvent
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agent_iam_audit")


class IAMAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact keys containing 'token', 'secret', 'key'."""
        redacted = {}
        for k, v in data.items():
            k_lower = k.lower()
            if any(term in k_lower for term in ["token", "secret", "key", "password"]):
                if isinstance(v, str):
                    if len(v) > 8:
                        redacted[k] = f"{v[:4]}...{v[-4:]} [REDACTED]"
                    else:
                        redacted[k] = "[REDACTED]"
                else:
                    redacted[k] = "[REDACTED]"
            elif isinstance(v, dict):
                redacted[k] = self._redact_dict(v)
            elif isinstance(v, list):
                redacted[k] = [
                    self._redact_dict(item) if isinstance(item, dict) else item for item in v
                ]
            else:
                redacted[k] = v
        return redacted

    async def log_event(
        self,
        tenant_id: str,
        event_type: str,
        agent_id: uuid.UUID | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AgentCredentialAuditEvent:
        """
        Logs an IAM credential event to both the standard logger and database.
        Ensures all sensitive tokens or secrets are redacted from output.
        """
        details_dict = details or {}
        redacted_details = self._redact_dict(details_dict)

        # DB event
        event = AgentCredentialAuditEvent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            details=redacted_details,
        )
        self.db.add(event)
        await self.db.flush()

        logger.info(
            f"IAM Event: {event_type} | Tenant: {tenant_id} | Agent: {agent_id} | Actor: {actor_id} ({actor_type}) | Details: {redacted_details}"
        )
        return event
