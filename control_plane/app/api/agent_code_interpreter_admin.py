# Owner: agent-platform
import uuid
from typing import Optional

from app.api.deps import get_db as get_async_db
from app.api.deps import require_admin
from app.core.config import Settings, get_settings
from app.models.agents.agent_tool_synthesis import (
    AgentCodeInterpreterRun,
    AgentSandboxArtifact,
)
from app.services.agents.code_interpreter import CodeInterpreter
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/code-interpreter", tags=["agent-code-interpreter"])

class CodeRunRequest(BaseModel):
    code: str
    agent_id: Optional[uuid.UUID] = None
    run_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None
    tenant_id: Optional[str] = "default"

@router.post("/run")
async def run_code(
    req: CodeRunRequest, 
    db: AsyncSession = Depends(get_async_db), 
    settings: Settings = Depends(get_settings), 
    _: dict = Depends(require_admin)
):
    if not settings.agent_code_interpreter_enabled:
        raise HTTPException(status_code=400, detail="Code interpreter is not enabled")
    
    interpreter = CodeInterpreter(db)
    try:
        result = await interpreter.run_code(
            code=req.code,
            agent_id=req.agent_id,
            run_id=req.run_id,
            tenant_id=req.tenant_id,
            session_id=req.session_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}")
async def get_run(
    run_id: uuid.UUID, 
    db: AsyncSession = Depends(get_async_db), 
    _: dict = Depends(require_admin)
):
    stmt = select(AgentCodeInterpreterRun).where(AgentCodeInterpreterRun.id == run_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": str(run.id),
        "session_id": str(run.session_id) if run.session_id else None,
        "agent_id": str(run.agent_id) if run.agent_id else None,
        "stdout": run.stdout,
        "stderr": run.stderr,
        "exit_code": run.exit_code,
        "execution_time_ms": run.execution_time_ms,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }

@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: uuid.UUID, 
    db: AsyncSession = Depends(get_async_db), 
    _: dict = Depends(require_admin)
):
    stmt = select(AgentSandboxArtifact).where(AgentSandboxArtifact.id == artifact_id)
    res = await db.execute(stmt)
    artifact = res.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "id": str(artifact.id),
        "session_id": str(artifact.session_id),
        "filename": artifact.filename,
        "content_type": artifact.content_type,
        "size_bytes": artifact.size_bytes,
        "storage_path": artifact.storage_path,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
    }

@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: uuid.UUID, 
    db: AsyncSession = Depends(get_async_db), 
    _: dict = Depends(require_admin)
):
    # Logic to cancel a running sandbox execution
    return {"status": "cancelled", "run_id": str(run_id)}
