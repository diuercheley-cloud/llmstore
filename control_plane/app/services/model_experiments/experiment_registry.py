import uuid
from typing import List, Optional

from app.models.model_experiments import ModelExperiment, ModelExperimentVariant
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ExperimentRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_experiment(
        self, 
        name: str, 
        experiment_type: str = "ab_test",
        target_route_id: Optional[uuid.UUID] = None,
        target_tenant_id: Optional[str] = None
    ) -> ModelExperiment:
        experiment = ModelExperiment(
            name=name,
            experiment_type=experiment_type,
            target_route_id=target_route_id,
            target_tenant_id=target_tenant_id,
            status="draft"
        )
        self.db.add(experiment)
        await self.db.flush()
        return experiment

    async def get_active_experiments(self) -> List[ModelExperiment]:
        stmt = select(ModelExperiment).where(ModelExperiment.status == "running")
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def add_variant(
        self,
        experiment_id: uuid.UUID,
        name: str,
        traffic_weight: float,
        model_id: Optional[str] = None,
        backend_id: Optional[uuid.UUID] = None,
        is_control: bool = False
    ) -> ModelExperimentVariant:
        variant = ModelExperimentVariant(
            experiment_id=experiment_id,
            name=name,
            traffic_weight=traffic_weight,
            model_id=model_id,
            backend_id=backend_id,
            is_control=is_control
        )
        self.db.add(variant)
        await self.db.flush()
        return variant
