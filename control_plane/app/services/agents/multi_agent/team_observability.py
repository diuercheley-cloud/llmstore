# Owner: Platform Operations
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.multi_agent import AgentTeamRun, AgentTeamTrace, AgentTeamMessage
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class TeamObservability:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_trace(self, run_id: uuid.UUID, event_type: str, details: Dict[str, Any], agent_id: Optional[uuid.UUID] = None):
        trace = AgentTeamTrace(
            run_id=run_id,
            event_type=event_type,
            agent_id=agent_id,
            details=details
        )
        self.db.add(trace)
        await self.db.flush()

    async def record_message(
        self, 
        run_id: uuid.UUID, 
        sender_id: Optional[uuid.UUID], 
        recipient_id: Optional[uuid.UUID], 
        content: str, 
        message_type: str
    ):
        msg = AgentTeamMessage(
            run_id=run_id,
            sender_agent_id=sender_id,
            recipient_agent_id=recipient_id,
            content=content,
            message_type=message_type
        )
        self.db.add(msg)
        await self.db.flush()
        
        await self.record_trace(run_id, "message_sent", {
            "message_type": message_type,
            "sender_id": str(sender_id) if sender_id else None,
            "recipient_id": str(recipient_id) if recipient_id else None
        }, agent_id=sender_id)
