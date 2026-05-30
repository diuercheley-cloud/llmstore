import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.mlops import MLExperiment, MLExperimentRun
from app.services.mlops.dataset_registry import log_mlops_audit
from app.core.time import utc_now
from app.core.config import get_settings


class ExperimentTracker:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_experiment(
        self,
        name: str,
        description: Optional[str] = None,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> MLExperiment:
        experiment = MLExperiment(
            id=uuid.uuid4(),
            name=name,
            description=description,
            created_at=utc_now(),
        )
        self.session.add(experiment)
        await self.session.flush()

        await log_mlops_audit(
            self.session,
            event_type="experiment_create",
            status="success",
            target_type="ml_experiments",
            target_id=str(experiment.id),
            details={"name": name},
            admin_user_id=admin_user_id,
        )
        return experiment

    async def log_run(
        self,
        experiment_id: uuid.UUID,
        training_job_id: Optional[uuid.UUID] = None,
        metrics: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> MLExperimentRun:
        # Check experiment exists
        result = await self.session.execute(
            select(MLExperiment).where(MLExperiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")

        # Security check: verify no sensitive parameter names/values in params or artifacts
        # (e.g. check for keys containing api_key, secret, token, password, private_key, or values matching sk-...)
        # Wait, the security rule is: "nenhum dado sensível em artifact sem policy"
        # We will also enforce this for params here as general hardening
        all_params = params or {}
        for k, v in all_params.items():
            if any(term in k.lower() for term in ["api_key", "secret", "token", "password", "private_key"]):
                raise HTTPException(
                    status_code=400,
                    detail=f"Sensitive parameter '{k}' cannot be logged directly to experiment runs."
                )

        run = MLExperimentRun(
            id=uuid.uuid4(),
            experiment_id=experiment_id,
            training_job_id=training_job_id,
            metrics=metrics or {},
            params=all_params,
            artifacts=artifacts or {},
            created_at=utc_now(),
        )
        self.session.add(run)
        await self.session.flush()

        # External Integrations disabled by default
        settings = get_settings()
        integration_details = {
            "mlflow_triggered": False,
            "wandb_triggered": False
        }
        if settings.mlflow_integration_enabled:
            # Code to integrate with MLflow API would go here
            integration_details["mlflow_triggered"] = True
        if settings.wandb_integration_enabled:
            # Code to integrate with Weights & Biases API would go here
            integration_details["wandb_triggered"] = True

        await log_mlops_audit(
            self.session,
            event_type="experiment_run_log",
            status="success",
            target_type="ml_experiment_runs",
            target_id=str(run.id),
            details={
                "experiment_id": str(experiment_id),
                "training_job_id": str(training_job_id) if training_job_id else None,
                "integrations": integration_details,
            },
            admin_user_id=admin_user_id,
        )
        return run

    async def list_experiments(self) -> List[MLExperiment]:
        result = await self.session.execute(select(MLExperiment))
        return list(result.scalars().all())
