import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.agents import AgentDefinition
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class AssistantRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_assistant(
        self,
        tenant_id: str,
        name: str,
        model_id: str,
        instructions: str,
        description: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentDefinition:
        assistant = AgentDefinition(
            id=uuid.uuid4(),
            name=name,
            model_id=model_id,
            instructions=instructions,
            description=description,
            tenant_id=tenant_id,
            allowed_tools=tools,
            owner="assistants_api",
            version="1.0.0",
            status="active"
        )
        self.db.add(assistant)
        await self.db.flush()
        return assistant

    async def get_assistant(self, tenant_id: str, assistant_id: uuid.UUID) -> Optional[AgentDefinition]:
        stmt = select(AgentDefinition).where(
            AgentDefinition.id == assistant_id,
            AgentDefinition.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_assistants(self, tenant_id: str, limit: int = 20) -> List[AgentDefinition]:
        stmt = select(AgentDefinition).where(
            AgentDefinition.tenant_id == tenant_id
        ).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
