"""
Owner: agent-platform
Status: beta
"""
import logging
import uuid

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agents import AgentRunCosts
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class AgentCostMeterService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def record_cost(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost_brl: float
    ) -> AgentRunCosts:
        # Check if record already exists for run
        res = await self.db.execute(select(AgentRunCosts).where(AgentRunCosts.run_id == run_id))
        record = res.scalar_one_or_none()

        if record:
            record.prompt_tokens += prompt_tokens
            record.completion_tokens += completion_tokens
            record.estimated_cost_brl += estimated_cost_brl
        else:
            record = AgentRunCosts(
                run_id=run_id,
                agent_id=agent_id,
                tenant_id=tenant_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_brl=estimated_cost_brl,
                created_at=utc_now()
            )
            self.db.add(record)
        
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_cost(self, run_id: uuid.UUID) -> AgentRunCosts:
        res = await self.db.execute(select(AgentRunCosts).where(AgentRunCosts.run_id == run_id))
        return res.scalar_one_or_none()
