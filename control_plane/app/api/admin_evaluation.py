import uuid
from typing import Any, Dict, List, Optional

from app.api.deps import get_db_session
from app.services.evaluation.service import EvaluationService
from app.models.agents.evaluation import EvalRun, EvalResult, RedTeamFinding, EloRating
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin/evaluation", tags=["admin-evaluation"])


@router.get("/rankings")
async def get_elo_rankings(
    session: AsyncSession = Depends(get_db_session)
):
    service = EvaluationService(session)
    return await service.get_elo_ranking()


@router.post("/runs")
async def create_evaluation_run(
    dataset_id: uuid.UUID,
    model_name: str,
    tenant_id: str = "default",
    session: AsyncSession = Depends(get_db_session)
):
    service = EvaluationService(session)
    run = await service.run_evaluation(dataset_id, model_name, tenant_id)
    return {"run_id": str(run.id), "status": run.status}


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session)
):
    stmt = (
        select(EvalResult)
        .where(EvalResult.run_id == run_id)
        .order_by(EvalResult.total_score.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/red-team/findings")
async def list_red_team_findings(
    severity: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(RedTeamFinding)
    if severity:
        stmt = stmt.where(RedTeamFinding.severity == severity)
    stmt = stmt.order_by(RedTeamFinding.created_at.desc())
    
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/arena/match")
async def record_arena_match(
    dataset_id: uuid.UUID,
    model_a: str,
    model_b: str,
    score_a: float,
    score_b: float,
    session: AsyncSession = Depends(get_db_session)
):
    service = EvaluationService(session)
    await service.record_match(dataset_id, model_a, model_b, score_a, score_b)
    return {"status": "success"}
