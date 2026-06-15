import json
import uuid

from app.api.deps import get_db_session
from app.models.agents.evaluation import EvalResult, RedTeamFinding
from app.services.agents.agent_evaluation_framework import AgentEvaluationService
from app.services.evaluation.service import EvaluationService
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/evaluation", tags=["admin-evaluation"])


@router.get("/agent-evaluation/benchmarks")
async def list_agent_benchmarks(session: AsyncSession = Depends(get_db_session)):
    service = AgentEvaluationService(session)
    return service.list_benchmarks()


@router.post("/agent-evaluation/runs")
async def run_agent_evaluation(
    agent_id: uuid.UUID,
    model_name: str,
    benchmark: str = Query(..., pattern=r"^(AgentBench|GAIA|BFCL)$"),
    session: AsyncSession = Depends(get_db_session),
):
    service = AgentEvaluationService(session)
    try:
        report = await service.run_benchmark(
            agent_id=agent_id, model_name=model_name, benchmark=benchmark
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return report.to_dict()


@router.get("/agent-evaluation/runs")
async def list_agent_evaluation_reports(session: AsyncSession = Depends(get_db_session)):
    service = AgentEvaluationService(session)
    runs = []
    for benchmark_dir in service.artifacts_dir.glob("*"):
        if not benchmark_dir.is_dir():
            continue
        for run_dir in benchmark_dir.glob("*"):
            report_file = run_dir / "report.json"
            if report_file.exists():
                try:
                    runs.append(report_file.read_text())
                except Exception:
                    continue
    return [json.loads(item) for item in runs]


@router.get("/agent-evaluation/runs/{run_id}/export")
async def export_agent_evaluation_run(
    run_id: str,
    benchmark: str = Query(..., pattern=r"^(AgentBench|GAIA|BFCL)$"),
    format: str = Query("json", pattern=r"^(json|csv|md)$"),
    session: AsyncSession = Depends(get_db_session),
):
    service = AgentEvaluationService(session)
    report_file = service.artifacts_dir / benchmark / run_id / f"report.{format}"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    media_type = (
        "application/json"
        if format == "json"
        else "text/csv"
        if format == "csv"
        else "text/markdown"
    )
    return Response(content=report_file.read_text(), media_type=media_type)


@router.get("/rankings")
async def get_elo_rankings(session: AsyncSession = Depends(get_db_session)):
    service = EvaluationService(session)
    return await service.get_elo_ranking()


@router.post("/runs")
async def create_evaluation_run(
    dataset_id: uuid.UUID,
    model_name: str,
    tenant_id: str = "default",
    session: AsyncSession = Depends(get_db_session),
):
    service = EvaluationService(session)
    run = await service.run_evaluation(dataset_id, model_name, tenant_id)
    return {"run_id": str(run.id), "status": run.status}


@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    stmt = (
        select(EvalResult)
        .where(EvalResult.run_id == run_id)
        .order_by(EvalResult.total_score.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/red-team/findings")
async def list_red_team_findings(
    severity: str | None = None, session: AsyncSession = Depends(get_db_session)
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
    session: AsyncSession = Depends(get_db_session),
):
    service = EvaluationService(session)
    await service.record_match(dataset_id, model_a, model_b, score_a, score_b)
    return {"status": "success"}
