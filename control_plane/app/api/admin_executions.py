import uuid
from typing import Any, Dict, List, Optional

from app.api.deps import get_db_session
from app.services.deterministic_execution.service import DeterministicExecutionService
from app.models.deterministic_execution import ExecutionRun, ExecutionStep
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin/executions", tags=["admin-executions"])


@router.get("/{run_id}/manifest")
async def get_execution_manifest(
    run_id: uuid.UUID, 
    session: AsyncSession = Depends(get_db_session)
):
    service = DeterministicExecutionService(session)
    manifest = await service.generate_manifest(run_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Execution run not found")
    return manifest


@router.post("/{run_id}/replay/dry-run")
async def replay_dry_run(
    run_id: uuid.UUID, 
    session: AsyncSession = Depends(get_db_session)
):
    service = DeterministicExecutionService(session)
    return await service.replay_dry_run(run_id)


@router.get("/{run_id}/steps")
async def get_execution_steps(
    run_id: uuid.UUID, 
    session: AsyncSession = Depends(get_db_session)
):
    stmt = (
        select(ExecutionStep)
        .where(ExecutionStep.run_id == run_id)
        .options(selectinload(ExecutionStep.tool_calls))
        .order_by(ExecutionStep.step_number.asc())
    )
    result = await session.execute(stmt)
    steps = result.scalars().all()
    
    return [
        {
            "step_number": s.step_number,
            "model": s.model_name,
            "provider": s.provider,
            "prompt_hash": s.prompt_hash,
            "response_hash": s.response_hash,
            "timestamp": s.timestamp.isoformat(),
            "tool_calls": [
                {
                    "tool": tc.tool_name,
                    "input": tc.tool_input,
                    "output": tc.tool_output if not tc.is_redacted else "[REDACTED]",
                    "is_redacted": tc.is_redacted
                }
                for tc in s.tool_calls
            ]
        }
        for s in steps
    ]
