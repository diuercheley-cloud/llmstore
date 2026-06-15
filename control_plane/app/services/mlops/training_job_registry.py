import re
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.core.mlops import MLDatasetVersion, MLTrainingJob
from app.services.mlops.dataset_registry import log_mlops_audit
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def sanitize_logs(log_text: str) -> str:
    if not log_text:
        return ""
    # Pattern to match keys indicating secrets/passwords/api keys and their values
    # Also sk-... patterns for openai key
    patterns = [
        r'(?i)(api[-_ ]?key|secret|password|token|private[-_ ]?key|auth_token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.\+\/]{10,}["\']?',
        r"sk-[a-zA-Z0-9]{32,}",
        r"Bearer\s+[a-zA-Z0-9_\-\.]+",
    ]
    sanitized = log_text
    for p in patterns:
        sanitized = re.sub(p, r"[REDACTED_SENSITIVE_DATA]", sanitized)
    return sanitized


class TrainingJobRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(
        self,
        model_name: str,
        dataset_version_id: uuid.UUID,
        provider: str = "mock",
        hyperparameters: dict[str, Any] | None = None,
        admin_user_id: uuid.UUID | None = None,
    ) -> MLTrainingJob:
        # Check dataset version exists
        result = await self.session.execute(
            select(MLDatasetVersion).where(MLDatasetVersion.id == dataset_version_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=404, detail="Dataset version not found")

        job = MLTrainingJob(
            id=uuid.uuid4(),
            model_name=model_name,
            dataset_version_id=dataset_version_id,
            provider=provider,
            status="queued",
            hyperparameters=hyperparameters or {},
            logs="",
            output_model_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(job)
        await self.session.flush()

        await log_mlops_audit(
            self.session,
            event_type="training_job_create",
            status="success",
            target_type="ml_training_jobs",
            target_id=str(job.id),
            details={"model_name": model_name, "provider": provider},
            admin_user_id=admin_user_id,
        )
        return job

    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: str,
        logs: str | None = None,
        output_model_id: str | None = None,
        admin_user_id: uuid.UUID | None = None,
    ) -> MLTrainingJob:
        result = await self.session.execute(select(MLTrainingJob).where(MLTrainingJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Training job not found")

        job.status = status
        if logs is not None:
            job.logs = sanitize_logs(logs)
        if output_model_id is not None:
            job.output_model_id = output_model_id
        job.updated_at = utc_now()

        await log_mlops_audit(
            self.session,
            event_type="training_job_update",
            status="success",
            target_type="ml_training_jobs",
            target_id=str(job.id),
            details={"status": status, "output_model_id": output_model_id},
            admin_user_id=admin_user_id,
        )
        return job

    async def get_job(self, job_id: uuid.UUID) -> MLTrainingJob | None:
        result = await self.session.execute(select(MLTrainingJob).where(MLTrainingJob.id == job_id))
        return result.scalar_one_or_none()
