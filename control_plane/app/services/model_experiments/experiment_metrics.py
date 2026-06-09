import uuid
from typing import Any, Dict

from app.models.model_experiments import ModelExperimentMetric
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


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
        result = await self.db.execute(
            select(
                ModelExperimentMetric.variant_id,
                ModelExperimentMetric.metric_name,
                func.count(ModelExperimentMetric.id).label("count"),
                func.avg(ModelExperimentMetric.metric_value).label("average"),
                func.min(ModelExperimentMetric.metric_value).label("minimum"),
                func.max(ModelExperimentMetric.metric_value).label("maximum"),
            )
            .where(ModelExperimentMetric.experiment_id == experiment_id)
            .group_by(ModelExperimentMetric.variant_id, ModelExperimentMetric.metric_name)
        )
        variants: Dict[str, Dict[str, Any]] = {}
        for row in result.mappings():
            variant = variants.setdefault(str(row["variant_id"]), {})
            variant[row["metric_name"]] = {
                "count": int(row["count"]),
                "average": float(row["average"]),
                "minimum": float(row["minimum"]),
                "maximum": float(row["maximum"]),
            }
        return {"experiment_id": str(experiment_id), "variants": variants}
