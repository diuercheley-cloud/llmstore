# Owner: agent-platform
import hashlib
import uuid
from typing import Any

from app.models.agents.agent_tool_synthesis import AgentSandboxPolicyEvent
from sqlalchemy.ext.asyncio import AsyncSession


class SandboxAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        event_type: str,
        details: dict[str, Any],
        session_id: uuid.UUID | None = None,
    ) -> AgentSandboxPolicyEvent:
        event = AgentSandboxPolicyEvent(
            session_id=session_id,
            event_type=event_type,
            details=details,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def record_start(
        self,
        agent_id: uuid.UUID | None,
        run_id: uuid.UUID | None,
        tenant_id: str | None,
        code: str,
        session_id: uuid.UUID | None,
        provider: str,
        limits: dict[str, Any],
    ) -> AgentSandboxPolicyEvent:
        return await self.record_event(
            "execution_started",
            {
                "agent_id": str(agent_id) if agent_id else None,
                "run_id": str(run_id) if run_id else None,
                "tenant_id": tenant_id,
                "provider": provider,
                "limits": limits,
                "code_hash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
            },
            session_id=session_id,
        )
