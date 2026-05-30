import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.mlops import MLModelLineage
from app.services.mlops.dataset_registry import log_mlops_audit
from app.core.time import utc_now


class ModelLineage:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_lineage(
        self,
        model_id: str,
        dataset_version_id: uuid.UUID,
        training_job_id: uuid.UUID,
        experiment_run_id: Optional[uuid.UUID] = None,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> MLModelLineage:
        lineage = MLModelLineage(
            id=uuid.uuid4(),
            model_id=model_id,
            dataset_version_id=dataset_version_id,
            training_job_id=training_job_id,
            experiment_run_id=experiment_run_id,
            created_at=utc_now(),
        )
        self.session.add(lineage)
        await self.session.flush()

        await log_mlops_audit(
            self.session,
            event_type="model_lineage_create",
            status="success",
            target_type="ml_model_lineage",
            target_id=str(lineage.id),
            details={
                "model_id": model_id,
                "dataset_version_id": str(dataset_version_id),
                "training_job_id": str(training_job_id),
                "experiment_run_id": str(experiment_run_id) if experiment_run_id else None,
            },
            admin_user_id=admin_user_id,
        )
        return lineage

    async def get_lineage(self, model_id: str) -> Optional[MLModelLineage]:
        result = await self.session.execute(
            select(MLModelLineage)
            .options(
                selectinload(MLModelLineage.dataset_version),
                selectinload(MLModelLineage.training_job),
                selectinload(MLModelLineage.experiment_run)
            )
            .where(MLModelLineage.model_id == model_id)
        )
        return result.scalar_one_or_none()
