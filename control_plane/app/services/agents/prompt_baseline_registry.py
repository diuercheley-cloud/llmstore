# Owner: agent-platform
import hashlib
import logging
import uuid
from typing import Any, Dict, Optional

from app.core.time import utc_now
from app.models.agents.agents import AgentPromptBaseline
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class PromptBaselineRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    def compute_prompt_hash(self, instructions: str) -> str:
        return hashlib.sha256(instructions.encode("utf-8")).hexdigest()

    async def get_latest_baseline(self, agent_id: uuid.UUID) -> Optional[AgentPromptBaseline]:
        stmt = select(AgentPromptBaseline).where(
            AgentPromptBaseline.agent_id == agent_id,
            AgentPromptBaseline.status == "active"
        ).order_by(desc(AgentPromptBaseline.created_at))
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_baseline(
        self, 
        agent_id: uuid.UUID, 
        instructions: str, 
        eval_run_id: Optional[uuid.UUID] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> AgentPromptBaseline:
        # Supersede old baselines
        stmt = select(AgentPromptBaseline).where(
            AgentPromptBaseline.agent_id == agent_id,
            AgentPromptBaseline.status == "active"
        )
        res = await self.db.execute(stmt)
        for old in res.scalars().all():
            old.status = "superseded"
        
        prompt_hash = self.compute_prompt_hash(instructions)
        
        baseline = AgentPromptBaseline(
            agent_id=agent_id,
            prompt_hash=prompt_hash,
            eval_run_id=eval_run_id,
            status="active",
            metrics=metrics or {},
            created_at=utc_now()
        )
        self.db.add(baseline)
        await self.db.commit()
        return baseline

    async def validate_prompt_against_baseline(self, agent_id: uuid.UUID, current_instructions: str) -> bool:
        baseline = await self.get_latest_baseline(agent_id)
        if not baseline:
            return False
        
        current_hash = self.compute_prompt_hash(current_instructions)
        return current_hash == baseline.prompt_hash
