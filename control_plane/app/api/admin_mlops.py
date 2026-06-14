import json
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.services.runtime_dependencies import get_db_session
from app.services.auth import require_admin
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin-mlops"], dependencies=[Depends(require_admin)])
settings = get_settings()


class VllmTestRequest(BaseModel):
    prompt: str = "Hello, tell me a short joke."
    model: str | None = None
    stream: bool = False


class MLDatasetCreate(BaseModel):
    name: str
    description: str | None = None
    is_production: bool = False


class MLDatasetVersionCreate(BaseModel):
    version: str
    checksum: str
    provenance: str
    redaction_status: str = "none"
    consent_metadata: dict | None = None


class MLTrainingJobCreate(BaseModel):
    model_name: str
    dataset_version_id: uuid.UUID
    provider: str = "local_vllm"
    hyperparameters: dict | None = None


@router.get("/inference/backends/vllm/health")
async def get_vllm_health():
    from app.services.inference_backends import check_vllm_health
    return await check_vllm_health()


@router.get("/inference/backends/vllm/models")
async def get_vllm_models():
    from app.services.inference_backends import list_vllm_models
    return await list_vllm_models()


@router.post("/inference/backends/vllm/test")
async def test_vllm(req: VllmTestRequest):
    from app.services.inference_backends import VllmBackendService
    service = VllmBackendService()
    payload = {
        "model": req.model or service.settings.vllm_default_model,
        "messages": [{"role": "user", "content": req.prompt}],
        "max_tokens": 50,
    }
    return await service.chat_completions(payload, stream=req.stream)


@router.post("/mlops/datasets", status_code=201)
async def create_dataset(req: MLDatasetCreate, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.mlops_enabled:
        raise HTTPException(status_code=403, detail="MLOps features are disabled.")

    from app.services.mlops.dataset_registry import DatasetRegistry
    registry = DatasetRegistry(session)
    dataset = await registry.create_dataset(
        name=req.name,
        description=req.description,
        is_production=req.is_production,
    )
    await session.commit()
    return dataset


@router.get("/mlops/datasets")
async def list_datasets(session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.mlops_enabled:
        raise HTTPException(status_code=403, detail="MLOps features are disabled.")

    from app.services.mlops.dataset_registry import DatasetRegistry
    registry = DatasetRegistry(session)
    return await registry.list_datasets()


@router.post("/mlops/datasets/{id}/approve")
async def approve_dataset(id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.mlops_enabled:
        raise HTTPException(status_code=403, detail="MLOps features are disabled.")

    from app.services.mlops.dataset_registry import DatasetRegistry
    registry = DatasetRegistry(session)
    dataset = await registry.approve_dataset(id)
    await session.commit()
    return dataset


@router.post("/mlops/datasets/{id}/versions", status_code=201)
async def create_dataset_version(
    id: uuid.UUID,
    req: MLDatasetVersionCreate,
    session: AsyncSession = Depends(get_db_session)
):
    settings = get_settings()
    if not settings.mlops_enabled:
        raise HTTPException(status_code=403, detail="MLOps features are disabled.")

    from app.services.mlops.dataset_registry import DatasetRegistry
    registry = DatasetRegistry(session)
    version = await registry.create_version(
        dataset_id=id,
        version=req.version,
        checksum=req.checksum,
        provenance=req.provenance,
        redaction_status=req.redaction_status,
        consent_metadata=req.consent_metadata,
    )
    await session.commit()
    return version


@router.post("/mlops/fine-tuning/jobs", status_code=201)
async def create_fine_tuning_job(
    req: MLTrainingJobCreate,
    session: AsyncSession = Depends(get_db_session)
):
    settings = get_settings()
    if not settings.mlops_enabled or not settings.fine_tuning_enabled:
        raise HTTPException(status_code=403, detail="Fine-tuning features are disabled.")

    from app.services.mlops.finetuning_service import FineTuningService
    service = FineTuningService(session)
    job_id = await service.start_fine_tuning(
        model_name=req.model_name,
        dataset_version_id=req.dataset_version_id,
        provider=req.provider,
        hyperparameters=req.hyperparameters,
    )
    await session.commit()
    return {"job_id": job_id, "status": "queued"}


@router.get("/mlops/fine-tuning/jobs/{id}")
async def get_fine_tuning_job(id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.mlops_enabled or not settings.fine_tuning_enabled:
        raise HTTPException(status_code=403, detail="Fine-tuning features are disabled.")

    from app.services.mlops.training_job_registry import TrainingJobRegistry
    registry = TrainingJobRegistry(session)
    job = await registry.get_job(id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job


@router.get("/mlops/experiments")
async def list_experiments(session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.mlops_enabled or not settings.experiment_tracking_enabled:
        raise HTTPException(status_code=403, detail="Experiment tracking features are disabled.")

    from app.services.mlops.experiment_tracker import ExperimentTracker
    tracker = ExperimentTracker(session)
    return await tracker.list_experiments()


@router.get("/mlops/model-lineage/{model_id}")
async def get_model_lineage(model_id: str, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.mlops_enabled:
        raise HTTPException(status_code=403, detail="MLOps features are disabled.")

    from app.services.mlops.model_lineage import ModelLineage
    service = ModelLineage(session)
    lineage = await service.get_lineage(model_id)
    if not lineage:
        raise HTTPException(status_code=404, detail="Model lineage not found")
    return lineage
