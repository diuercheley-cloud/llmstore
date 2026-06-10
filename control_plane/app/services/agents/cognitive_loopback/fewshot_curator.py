# Owner: agent-platform
import uuid
from typing import List

from app.models.agents.agent_cognitive_loopback import AgentFewShotExample
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class FewShotCurator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_examples(self, agent_id: uuid.UUID, tenant_id: str) -> List[AgentFewShotExample]:
        stmt = select(AgentFewShotExample).where(
            AgentFewShotExample.agent_id == agent_id,
            AgentFewShotExample.tenant_id == tenant_id,
            AgentFewShotExample.is_active == True
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def activate_example(self, example_id: uuid.UUID, tenant_id: str) -> bool:
        example = await self.db.get(AgentFewShotExample, example_id)
        if not example or example.tenant_id != tenant_id:
            return False
        example.is_active = True
        await self.db.commit()
        return True

    async def deactivate_example(self, example_id: uuid.UUID, tenant_id: str) -> bool:
        example = await self.db.get(AgentFewShotExample, example_id)
        if not example or example.tenant_id != tenant_id:
            return False
        example.is_active = False
        await self.db.commit()
        return True
