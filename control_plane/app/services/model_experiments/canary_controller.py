import logging
import uuid

from app.core.time import utc_now
from app.models.core.model_experiments import ModelExperiment, ModelExperimentVariant
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CanaryController:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_canary(self, experiment_id: uuid.UUID):
        experiment = await self.db.get(ModelExperiment, experiment_id)
        if experiment:
            experiment.status = "running"
            experiment.started_at = utc_now()
            await self.db.flush()

    async def increment_traffic(self, experiment_id: uuid.UUID, increment: float = 10.0):
        # Gradual increase of canary traffic
        experiment = await self.db.get(ModelExperiment, experiment_id)
        if not experiment or experiment.status != "running":
            return

        variants = (
            (
                await self.db.execute(
                    select(ModelExperimentVariant).where(
                        ModelExperimentVariant.experiment_id == experiment_id
                    )
                )
            )
            .scalars()
            .all()
        )

        canary_variant = next((v for v in variants if not v.is_control), None)
        control_variant = next((v for v in variants if v.is_control), None)

        if canary_variant and control_variant:
            new_canary_weight = min(canary_variant.traffic_weight + increment, 100.0)
            canary_variant.traffic_weight = new_canary_weight
            control_variant.traffic_weight = 100.0 - new_canary_weight
            await self.db.flush()

    async def check_slos_and_auto_rollback(self, experiment_id: uuid.UUID):
        experiment = await self.db.get(ModelExperiment, experiment_id)
        if not experiment or not experiment.auto_rollback_enabled:
            return

        # Fetch recent metrics and check against thresholds
        # This would be called by a background task
        pass
