import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.agents import AgentRun, AgentDefinition
from app.models.assistants import AssistantThread, AssistantMessage
from app.services.agents.agent_runtime import start_run

logger = logging.getLogger(__name__)

class AssistantRunAdapter:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_run(
        self,
        tenant_id: str,
        thread_id: uuid.UUID,
        assistant_id: uuid.UUID,
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentRun:
        # 1. Fetch thread history
        from .message_store import MessageStore
        msg_store = MessageStore(self.db)
        messages = await msg_store.list_messages(thread_id)
        
        # 2. Format input for AgentRun
        history_text = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        # 3. Create and start AgentRun using the real runtime
        run = await start_run(
            db=self.db,
            agent_id=assistant_id,
            tenant_id=tenant_id,
            input_text=history_text,
            correlation_id=str(thread_id)
        )
        
        return run

    async def get_run(self, tenant_id: str, run_id: uuid.UUID) -> Optional[AgentRun]:
        stmt = select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
