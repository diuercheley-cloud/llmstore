# Owner: Platform Operations
import uuid
from typing import List

from app.api.deps import get_admin_token, get_db
from app.core.config import get_settings
from app.models.agent_optimization_tournament import (
    AgentOptimizationPairwiseResult,
    AgentOptimizationTournament,
    AgentOptimizationTournamentCandidate,
    AgentOptimizationTournamentResult,
)
from app.services.agents.optimization.tournament_runner import TournamentRunner
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def verify_tournaments_enabled():
    settings = get_settings()
    if not settings.agent_optimizer_tournaments_enabled:
        raise HTTPException(
            status_code=403,
            detail="Tournament evaluation is disabled by feature flag.",
        )


router = APIRouter(
    prefix="/admin/agents",
    tags=["agent-optimization-tournaments-admin"],
    dependencies=[Depends(verify_tournaments_enabled)],
)


class TournamentCreateRequest(BaseModel):
    candidate_ids: List[uuid.UUID]
    parallel_limit: int = 2


class TournamentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    agent_id: uuid.UUID
    experiment_id: uuid.UUID | None
    status: str
    candidate_ids: list
    parallel_limit: int
    winner_id: uuid.UUID | None
    confidence_score: float | None
    ranking: list | None
    rollback_point: dict | None
    approval_status: str
    approved_at: str | None
    applied_at: str | None
    created_at: str
    updated_at: str


class TournamentDetailResponse(TournamentResponse):
    candidates: list = []
    results: list = []
    pairwise_results: list = []


class WinnerApproveResponse(BaseModel):
    id: uuid.UUID
    approval_status: str
    winner_id: uuid.UUID | None
    confidence_score: float | None


@router.post("/{id}/optimization/tournaments", response_model=TournamentResponse)
async def create_tournament(
    id: uuid.UUID,
    req: TournamentCreateRequest,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    runner = TournamentRunner(db)
    try:
        tournament = await runner.create_tournament(
            tenant_id, id, req.candidate_ids, req.parallel_limit
        )
        await db.commit()
        return _tournament_to_response(tournament)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/optimization/tournaments", response_model=List[TournamentResponse])
async def list_tournaments(
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    stmt = select(AgentOptimizationTournament).where(
        AgentOptimizationTournament.tenant_id == tenant_id
    ).order_by(AgentOptimizationTournament.created_at.desc())
    res = await db.execute(stmt)
    tournaments = res.scalars().all()
    return [_tournament_to_response(t) for t in tournaments]


@router.get(
    "/optimization/tournaments/{tournament_id}",
    response_model=TournamentDetailResponse,
)
async def get_tournament(
    tournament_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    stmt = select(AgentOptimizationTournament).where(
        AgentOptimizationTournament.id == tournament_id
    )
    res = await db.execute(stmt)
    tournament = res.scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found.")

    stmt_c = select(AgentOptimizationTournamentCandidate).where(
        AgentOptimizationTournamentCandidate.tournament_id == tournament_id
    )
    res_c = await db.execute(stmt_c)
    candidates = list(res_c.scalars().all())

    stmt_r = (
        select(AgentOptimizationTournamentResult)
        .where(
            AgentOptimizationTournamentResult.tournament_id == tournament_id
        )
        .order_by(AgentOptimizationTournamentResult.rank)
    )
    res_r = await db.execute(stmt_r)
    results = list(res_r.scalars().all())

    stmt_p = select(AgentOptimizationPairwiseResult).where(
        AgentOptimizationPairwiseResult.tournament_id == tournament_id
    )
    res_p = await db.execute(stmt_p)
    pairwise = list(res_p.scalars().all())

    detail = _tournament_to_response(tournament)
    detail["candidates"] = [
        {
            "id": str(c.id),
            "candidate_id": str(c.candidate_id),
            "label": c.label,
            "status": c.status,
        }
        for c in candidates
    ]
    detail["results"] = [
        {
            "id": str(r.id),
            "tournament_candidate_id": str(r.tournament_candidate_id),
            "score": r.score,
            "rank": r.rank,
            "safety_regression": r.safety_regression,
            "metrics": r.metrics,
        }
        for r in results
    ]
    detail["pairwise_results"] = [
        {
            "id": str(p.id),
            "candidate_a_id": str(p.candidate_a_id),
            "candidate_b_id": str(p.candidate_b_id),
            "winner_id": str(p.winner_id) if p.winner_id else None,
            "score_a": p.score_a,
            "score_b": p.score_b,
        }
        for p in pairwise
    ]
    return detail


@router.post(
    "/optimization/tournaments/{tournament_id}/run",
    response_model=TournamentResponse,
)
async def run_tournament(
    tournament_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    runner = TournamentRunner(db)
    try:
        tournament = await runner.run_tournament(tournament_id)
        await db.commit()
        return _tournament_to_response(tournament)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/optimization/tournaments/{tournament_id}/approve-winner",
    response_model=WinnerApproveResponse,
)
async def approve_winner(
    tournament_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    runner = TournamentRunner(db)
    try:
        tournament = await runner.approve_winner(tournament_id)
        await db.commit()
        return WinnerApproveResponse(
            id=tournament.id,
            approval_status=tournament.approval_status,
            winner_id=tournament.winner_id,
            confidence_score=tournament.confidence_score,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/optimization/tournaments/{tournament_id}/apply-winner",
    response_model=TournamentResponse,
)
async def apply_winner(
    tournament_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_token),
):
    runner = TournamentRunner(db)
    try:
        tournament = await runner.apply_winner(tournament_id)
        await db.commit()
        return _tournament_to_response(tournament)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _tournament_to_response(t: AgentOptimizationTournament) -> dict:
    return {
        "id": t.id,
        "tenant_id": t.tenant_id,
        "agent_id": t.agent_id,
        "experiment_id": t.experiment_id,
        "status": t.status,
        "candidate_ids": t.candidate_ids,
        "parallel_limit": t.parallel_limit,
        "winner_id": t.winner_id,
        "confidence_score": t.confidence_score,
        "ranking": t.ranking,
        "rollback_point": t.rollback_point,
        "approval_status": t.approval_status,
        "approved_at": t.approved_at.isoformat() if t.approved_at else None,
        "applied_at": t.applied_at.isoformat() if t.applied_at else None,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }
