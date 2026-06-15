# Owner: agent-platform
import uuid
from typing import Any

from app.api.deps import get_db_session, require_admin
from app.services.agents.agent_evals import AgentEvalService
from app.services.agents.eval_dataset_registry import EvalDatasetRegistryService
from app.services.agents.eval_gate import EvalGateService
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agent-evals", tags=["agent-evals"])


# ---------------------------------------------------------------------------
# Datasets (Versioned)
# ---------------------------------------------------------------------------


@router.post("/datasets")
async def create_eval_dataset(
    agent_id: uuid.UUID = Body(...),
    name: str = Body(...),
    description: str | None = Body(None),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = EvalDatasetRegistryService(db)
    dataset = await service.create_dataset(agent_id, name, description)
    return {
        "id": str(dataset.id),
        "agent_id": str(dataset.agent_id),
        "name": dataset.name,
        "description": dataset.description,
        "created_at": dataset.created_at.isoformat(),
    }


@router.post("/datasets/{id}/versions")
async def create_dataset_version(
    id: uuid.UUID,
    version: str = Body(...),
    cases_json: list[dict] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = EvalDatasetRegistryService(db)
    try:
        dv = await service.create_dataset_version(id, version, cases_json)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {
        "id": str(dv.id),
        "dataset_id": str(dv.dataset_id),
        "version": dv.version,
        "cases_count": dv.cases_count,
        "created_at": dv.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Evaluation Runs
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_evaluation(
    agent_id: uuid.UUID = Body(...),
    suite_id: uuid.UUID | None = Body(None),
    dataset_id: uuid.UUID | None = Body(None),
    version: str | None = Body(None),
    metadata: dict | None = Body(None),
    allow_paid_provider: bool = Body(False),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = AgentEvalService(db)

    if suite_id:
        eval_run = await service.run_eval_suite(suite_id, metadata)
    elif dataset_id and version:
        eval_run = await service.run_dataset_version_eval(
            agent_id=agent_id,
            dataset_id=dataset_id,
            version=version,
            metadata=metadata,
            allow_paid_provider=allow_paid_provider,
        )
    else:
        raise HTTPException(
            status_code=400, detail="Either suite_id or dataset_id + version must be provided"
        )

    return {
        "id": str(eval_run.id),
        "status": eval_run.status,
        "passed_count": eval_run.passed_count,
        "failed_count": eval_run.failed_count,
        "total_count": eval_run.total_count,
        "started_at": eval_run.started_at.isoformat(),
        "completed_at": eval_run.completed_at.isoformat() if eval_run.completed_at else None,
    }


# ---------------------------------------------------------------------------
# Reports & Promotion Gates
# ---------------------------------------------------------------------------


@router.get("/reports/{agent_id}")
async def get_agent_eval_report(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = EvalGateService(db)
    return await service.get_report(agent_id)


@router.post("/promotion-check/{agent_id}")
async def check_promotion_gate(
    agent_id: uuid.UUID,
    eval_run_id: uuid.UUID = Body(...),
    audit_override: bool = Body(False),
    override_reason: str | None = Body(None),
    override_by: str | None = Body(None),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    service = EvalGateService(db)
    try:
        promo_result = await service.evaluate_promotion(
            agent_id=agent_id,
            eval_run_id=eval_run_id,
            audit_override=audit_override,
            override_reason=override_reason,
            override_by=override_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": str(promo_result.id),
        "agent_id": str(promo_result.agent_id),
        "passed": promo_result.passed,
        "audit_override": promo_result.audit_override,
        "details": promo_result.details,
        "created_at": promo_result.created_at.isoformat(),
    }
