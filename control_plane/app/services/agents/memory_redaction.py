"""
Owner: agent-platform
Status: beta
"""

import uuid

from app.models.agents.agents import AgentMemoryRedactionEvent
from sqlalchemy.ext.asyncio import AsyncSession


class MemoryRedactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def redact_content(self, content: str) -> tuple[str, list[str]]:
        # Dummy implementation of redaction
        # In a real scenario, this would use a PII/secret scanner
        redacted_types = []
        final_content = content

        if "email@" in final_content:
            final_content = final_content.replace("email@", "[REDACTED]@")
            redacted_types.append("email")

        if "pii-" in final_content:
            final_content = final_content.replace("pii-", "[REDACTED]-")
            redacted_types.append("pii")

        return final_content, redacted_types

    async def log_redaction(
        self, tenant_id: str, agent_id: uuid.UUID, item_id: uuid.UUID, redacted_types: list[str]
    ):
        if not redacted_types:
            return

        event = AgentMemoryRedactionEvent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            memory_item_id=item_id,
            redacted_types=",".join(redacted_types),
        )
        self.db.add(event)
        # Flush or let caller commit
