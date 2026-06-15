import hashlib
import random
import uuid

from app.models.core.model_experiments import (
    ModelExperiment,
    ModelExperimentAssignment,
    ModelExperimentVariant,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TrafficSplitter:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_assigned_variant(
        self, tenant_id: str, route_id: uuid.UUID | None = None, user_id: str | None = None
    ) -> ModelExperimentVariant | None:
        # 1. Find applicable active experiments
        stmt = select(ModelExperiment).where(ModelExperiment.status == "running")
        if route_id:
            stmt = stmt.where(
                (ModelExperiment.target_route_id == route_id)
                | (ModelExperiment.target_route_id.is_(None))
            )
        if tenant_id:
            stmt = stmt.where(
                (ModelExperiment.target_tenant_id == tenant_id)
                | (ModelExperiment.target_tenant_id.is_(None))
            )

        res = await self.db.execute(stmt)
        experiments = res.scalars().all()

        if not experiments:
            return None

        # For simplicity, pick the first applicable experiment
        experiment = experiments[0]

        # 2. Check for sticky assignment
        if user_id:
            stmt = select(ModelExperimentAssignment).where(
                ModelExperimentAssignment.experiment_id == experiment.id,
                ModelExperimentAssignment.user_id == user_id,
            )
            res = await self.db.execute(stmt)
            assignment = res.scalar_one_or_none()
            if assignment:
                return await self.db.get(ModelExperimentVariant, assignment.variant_id)

        # 3. Perform traffic split
        # Use deterministic hash for sticky assignment if user_id is provided, else random
        if user_id:
            hash_val = int(hashlib.md5(f"{experiment.id}:{user_id}".encode()).hexdigest(), 16) % 100
        else:
            hash_val = random.uniform(0, 100)

        stmt = select(ModelExperimentVariant).where(
            ModelExperimentVariant.experiment_id == experiment.id
        )
        res = await self.db.execute(stmt)
        variants = res.scalars().all()

        cumulative_weight = 0
        selected_variant = None
        for variant in variants:
            cumulative_weight += variant.traffic_weight
            if hash_val < cumulative_weight:
                selected_variant = variant
                break

        if selected_variant and user_id:
            # Save sticky assignment
            assignment = ModelExperimentAssignment(
                experiment_id=experiment.id,
                variant_id=selected_variant.id,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            self.db.add(assignment)
            await self.db.flush()

        return selected_variant
