import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_experiments import ModelExperiment
from app.core.time import utc_now

class PromotionGate:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def promote_variant(self, experiment_id: uuid.UUID, variant_id: uuid.UUID):
        experiment = await self.db.get(ModelExperiment, experiment_id)
        if experiment:
            # Mark as promoted
            experiment.status = "promoted"
            experiment.ended_at = utc_now()
            
            # Implementation would then update the Route/Model settings 
            # to permanently use the promoted variant's configuration.
            await self.db.flush()

    async def rollback(self, experiment_id: uuid.UUID, reason: str):
        experiment = await self.db.get(ModelExperiment, experiment_id)
        if experiment:
            experiment.status = "rolled_back"
            experiment.ended_at = utc_now()
            experiment.description = (experiment.description or "") + f"\nRollback reason: {reason}"
            await self.db.flush()
