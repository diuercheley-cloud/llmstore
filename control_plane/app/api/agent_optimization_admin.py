# Owner: Platform Operations
import uuid

from app.api.deps import get_admin_token, get_db
from app.core.config import get_settings
from app.services.agents.optimization.optimization_experiments import OptimizationExperimentService
from app.services.agents.optimization.optimizer import AgentOptimizerCoordinator
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


def verify_optimization_enabled():
    settings = get_settings()
    if not settings.agent_auto_optimization_enabled:
        raise HTTPException(
            status_code=403, detail="Agent Auto-Optimization is disabled by feature flag."
        )


router = APIRouter(
    prefix="/admin/agents",
    tags=["agent-optimization-admin"],
    dependencies=[Depends(verify_optimization_enabled)],
)


# Schemas
class ExperimentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    agent_id: uuid.UUID
    status: str
    metrics_baseline: dict
    created_at: str


class CandidateResponse(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    tenant_id: str
    agent_id: uuid.UUID
    candidate_type: str
    status: str
    is_improvement: bool
    safety_regression: bool
    created_at: str


class OptimizationResultResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    eval_run_id: uuid.UUID
    metrics_delta: dict
    created_at: str


# Endpoints
@router.post("/{id}/optimization/experiments", response_model=ExperimentResponse)
async def create_experiment(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    """Triggers an optimization experiment to analyze failures and generate candidates."""
    coordinator = AgentOptimizerCoordinator(db)
    try:
        experiment, candidates = await coordinator.run_optimization_experiment(tenant_id, id)
        await db.commit()
        return ExperimentResponse(
            id=experiment.id,
            tenant_id=experiment.tenant_id,
            agent_id=experiment.agent_id,
            status=experiment.status,
            metrics_baseline=experiment.metrics_baseline,
            created_at=experiment.created_at.isoformat(),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id}/optimization/candidates", response_model=list[CandidateResponse])
async def get_candidates(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    """Gets all generated optimization candidates for an agent."""
    service = OptimizationExperimentService(db)
    candidates = await service.get_candidates(tenant_id, id)
    return [
        CandidateResponse(
            id=c.id,
            experiment_id=c.experiment_id,
            tenant_id=c.tenant_id,
            agent_id=c.agent_id,
            candidate_type=c.candidate_type,
            status=c.status,
            is_improvement=c.is_improvement,
            safety_regression=c.safety_regression,
            created_at=c.created_at.isoformat(),
        )
        for c in candidates
    ]


@router.post(
    "/optimization/candidates/{candidate_id}/eval", response_model=OptimizationResultResponse
)
async def evaluate_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    """Runs the evaluation suite on a candidate to assess performance and safety deltas."""
    service = OptimizationExperimentService(db)
    try:
        result = await service.evaluate_candidate(candidate_id)
        await db.commit()
        return OptimizationResultResponse(
            id=result.id,
            candidate_id=result.candidate_id,
            eval_run_id=result.eval_run_id,
            metrics_delta=result.metrics_delta,
            created_at=result.created_at.isoformat(),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/optimization/candidates/{candidate_id}/approve", response_model=CandidateResponse)
async def approve_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    """Approves an optimization candidate for promotion."""
    service = OptimizationExperimentService(db)
    try:
        candidate = await service.approve_candidate(candidate_id)
        await db.commit()
        return CandidateResponse(
            id=candidate.id,
            experiment_id=candidate.experiment_id,
            tenant_id=candidate.tenant_id,
            agent_id=candidate.agent_id,
            candidate_type=candidate.candidate_type,
            status=candidate.status,
            is_improvement=candidate.is_improvement,
            safety_regression=candidate.safety_regression,
            created_at=candidate.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/optimization/candidates/{candidate_id}/apply", response_model=CandidateResponse)
async def apply_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    """Promotes/applies the candidate's changes onto the active agent definition."""
    service = OptimizationExperimentService(db)
    try:
        candidate = await service.apply_optimization(candidate_id)
        await db.commit()
        return CandidateResponse(
            id=candidate.id,
            experiment_id=candidate.experiment_id,
            tenant_id=candidate.tenant_id,
            agent_id=candidate.agent_id,
            candidate_type=candidate.candidate_type,
            status=candidate.status,
            is_improvement=candidate.is_improvement,
            safety_regression=candidate.safety_regression,
            created_at=candidate.created_at.isoformat(),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
