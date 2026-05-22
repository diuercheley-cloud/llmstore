import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import require_admin, get_db_session
from app.models.agents import AgentEvalSuite, AgentEvalRun, AgentEvalBaseline
from app.services.agents.agent_evals import AgentEvalService

router = APIRouter(prefix="/admin/agent-evals", tags=["agent-evals"])

@router.post("/suites")
async def create_eval_suite(
    agent_id: uuid.UUID = Body(...),
    name: str = Body(...),
    description: Optional[str] = Body(None),
    cases: List[dict] = Body([]),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentEvalService(db)
    suite = await service.create_suite(agent_id, name, description)
    
    created_cases = []
    for case_data in cases:
        case = await service.create_case(suite.id, case_data)
        created_cases.append(str(case.id))
        
    return {
        "id": str(suite.id),
        "name": suite.name,
        "agent_id": str(suite.agent_id),
        "case_count": len(created_cases),
        "cases": created_cases
    }

@router.post("/runs")
async def run_eval_suite(
    suite_id: uuid.UUID = Body(...),
    metadata: Optional[dict] = Body(None),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentEvalService(db)
    eval_run = await service.run_eval_suite(suite_id, metadata)
    
    return {
        "id": str(eval_run.id),
        "suite_id": str(eval_run.suite_id),
        "status": eval_run.status,
        "passed_count": eval_run.passed_count,
        "failed_count": eval_run.failed_count,
        "total_count": eval_run.total_count,
        "started_at": eval_run.started_at.isoformat(),
        "completed_at": eval_run.completed_at.isoformat() if eval_run.completed_at else None,
    }

@router.get("/runs/{run_id}")
async def get_eval_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    res = await db.execute(select(AgentEvalRun).where(AgentEvalRun.id == run_id))
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
        
    # Also fetch results
    from app.models.agents import AgentEvalResult
    res_results = await db.execute(select(AgentEvalResult).where(AgentEvalResult.run_id == run_id))
    results = res_results.scalars().all()
    
    return {
        "id": str(run.id),
        "suite_id": str(run.suite_id),
        "status": run.status,
        "passed_count": run.passed_count,
        "failed_count": run.failed_count,
        "total_count": run.total_count,
        "results": [
            {
                "case_id": str(r.case_id),
                "passed": r.passed,
                "score": r.score,
                "assertion_results": r.assertion_results,
                "latency_ms": r.latency_ms,
                "failure_details": r.failure_details,
            }
            for r in results
        ]
    }

@router.post("/baselines")
async def set_eval_baseline(
    agent_id: uuid.UUID = Body(...),
    run_id: uuid.UUID = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentEvalService(db)
    baseline = await service.set_baseline(agent_id, run_id, set_by=admin.email if hasattr(admin, "email") else "admin")
    
    return {
        "id": str(baseline.id),
        "agent_id": str(baseline.agent_id),
        "run_id": str(baseline.run_id),
        "score": baseline.score,
        "pass_rate": baseline.pass_rate,
        "version": baseline.version,
        "created_at": baseline.created_at.isoformat(),
    }

@router.get("/baselines/{agent_id}")
async def get_eval_baseline(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentEvalService(db)
    baseline = await service.get_baseline(agent_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found for this agent")
        
    return {
        "id": str(baseline.id),
        "agent_id": str(baseline.agent_id),
        "run_id": str(baseline.run_id),
        "score": baseline.score,
        "pass_rate": baseline.pass_rate,
        "version": baseline.version,
        "created_at": baseline.created_at.isoformat(),
    }
