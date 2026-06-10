import logging
import uuid
from typing import Any, Dict, Optional

from app.models.agents.agent_iam import AgentCredentialAuditEvent
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agent_iam_audit")

class IAMAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
                redacted[k] = [self._redact_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                redacted[k] = v
        return redacted

    async def log_event(
        self,
        tenant_id: str,
        event_type: str,
        agent_id: Optional[uuid.UUID] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
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
