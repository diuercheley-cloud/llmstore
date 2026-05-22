"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentTimelineEvent
from app.core.config import get_settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class AgentRunTimelineService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def record_event(
        self,
        run_id: uuid.UUID,
        event_type: str,
        step_id: Optional[uuid.UUID] = None,
        tool_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        is_error: bool = False
    ) -> Optional[AgentTimelineEvent]:
        if not self.settings.agent_observability_enabled:
            return None

        # Redact secrets
        details_json = details or {}
        if "secret" in str(details_json).lower() or "key" in str(details_json).lower():
             details_json = {"sanitized": "Details potentially contained secrets and were redacted."}

        event = AgentTimelineEvent(
            run_id=run_id,
            event_type=event_type,
            step_id=step_id,
            tool_name=tool_name,
            details_json=details_json,
            is_error=is_error,
            event_time=utc_now()
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_timeline(self, run_id: uuid.UUID) -> List[AgentTimelineEvent]:
        res = await self.db.execute(
            select(AgentTimelineEvent)
            .where(AgentTimelineEvent.run_id == run_id)
            .order_by(AgentTimelineEvent.event_time.asc())
        )
        return list(res.scalars().all())
