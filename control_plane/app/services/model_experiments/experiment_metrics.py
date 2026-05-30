import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_experiments import ModelExperimentMetric

class ExperimentMetrics:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_metric(
        self, 
        experiment_id: uuid.UUID, 
        variant_id: uuid.UUID, 
        name: str, 
        value: float
    ):
        metric = ModelExperimentMetric(
            experiment_id=experiment_id,
            variant_id=variant_id,
            metric_name=name,
            metric_value=value
        )
        self.db.add(metric)
        await self.db.flush()

    async def get_summary(self, experiment_id: uuid.UUID) -> Dict[str, Any]:
        # Implementation to aggregate metrics per variant
        return {}
