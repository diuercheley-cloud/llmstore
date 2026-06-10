# Owner: agent-platform
import random
import uuid
from typing import Optional

from app.models.agents.prompts import PromptExperiment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PromptABTestingService:
    """
    Manages A/B experiments for prompt templates.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_experiment(
        self, tenant_id: str, template_id: uuid.UUID, version_a_id: uuid.UUID, version_b_id: uuid.UUID, name: str, split: float = 0.5
    ) -> PromptExperiment:
        exp = PromptExperiment(
            tenant_id=tenant_id,
            template_id=template_id,
            version_a_id=version_a_id,
            version_b_id=version_b_id,
            name=name,
            traffic_split=split
        )
        self.db.add(exp)
        await self.db.flush()
        return exp

    async def get_active_version(self, experiment_id: uuid.UUID) -> Optional[uuid.UUID]:
        stmt = select(PromptExperiment).where(PromptExperiment.id == experiment_id, PromptExperiment.status == "running")
        res = await self.db.execute(stmt)
        exp = res.scalar_one_or_none()
        if not exp:
            return None
        
        # Simple deterministic or random split
        if random.random() < exp.traffic_split:
            return exp.version_a_id
        return exp.version_b_id

    async def complete_experiment(self, experiment_id: uuid.UUID, winner_version_id: uuid.UUID):
        stmt = select(PromptExperiment).where(PromptExperiment.id == experiment_id)
        res = await self.db.execute(stmt)
        exp = res.scalar_one_or_none()
        if exp:
            exp.status = "completed"
            exp.winner_version_id = winner_version_id
            await self.db.flush()
            
            # Optionally update the template's active version automatically
            from app.services.prompts.prompt_registry import PromptRegistry
            registry = PromptRegistry(self.db)
            await registry.set_active_version(exp.template_id, winner_version_id)
