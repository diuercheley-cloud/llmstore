# Owner: agent-platform
import uuid
from typing import Any, Dict, Optional

from app.models.agent_cognitive_loopback import AgentFeedbackEvent
from sqlalchemy.ext.asyncio import AsyncSession


class FeedbackCollector:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        agent_id: uuid.UUID,
        run_id: Optional[uuid.UUID],
        tenant_id: str,
        data: Dict[str, Any]
    ) -> AgentFeedbackEvent:
        event = AgentFeedbackEvent(
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
            user_id=data.get("user_id"),
            feedback_type=data.get("feedback_type"),
            score=data.get("score"),
            correction_text=data.get("correction_text"),
            operator_note=data.get("operator_note")
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
