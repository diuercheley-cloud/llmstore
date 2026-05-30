import uuid
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.mlops.training_job_registry import TrainingJobRegistry
from app.services.mlops.model_lineage import ModelLineage


class FineTuningService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.job_registry = TrainingJobRegistry(session)
        self.lineage_service = ModelLineage(session)

    async def start_fine_tuning(
        self,
        model_name: str,
        dataset_version_id: uuid.UUID,
        provider: str = "mock",
        hyperparameters: Optional[Dict[str, Any]] = None,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        # Create job entry
        job = await self.job_registry.create_job(
            model_name=model_name,
            dataset_version_id=dataset_version_id,
            provider=provider,
            hyperparameters=hyperparameters,
            admin_user_id=admin_user_id,
        )

        # Execution logic based on provider
        if provider == "mock":
            # Running state transition
            await self.job_registry.update_job_status(
                job_id=job.id,
                status="running",
                logs="Starting mock training execution... Setting up environments.",
                admin_user_id=admin_user_id,
            )

            # Success transition
            output_model_id = f"{model_name}-ft-{str(job.id)[:8]}"
            raw_logs = (
                "Training finished successfully.\n"
                "Saved weights. Epoch 3/3 loss=0.045\n"
                "Config API key was config_api_key='<redacted>'\n"
                "Done."
            )

            await self.job_registry.update_job_status(
                job_id=job.id,
                status="completed",
                logs=raw_logs,
                output_model_id=output_model_id,
                admin_user_id=admin_user_id,
            )

            # Record model lineage
            await self.lineage_service.record_lineage(
                model_id=output_model_id,
                dataset_version_id=dataset_version_id,
                training_job_id=job.id,
                admin_user_id=admin_user_id,
            )
        elif provider == "local":
            await self.job_registry.update_job_status(
                job_id=job.id,
                status="failed",
                logs="Local training execution not configured.",
                admin_user_id=admin_user_id,
            )
        else:
            await self.job_registry.update_job_status(
                job_id=job.id,
                status="failed",
                logs=f"Provider {provider} not configured.",
                admin_user_id=admin_user_id,
            )

        return job.id
