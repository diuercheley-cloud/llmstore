# Surface: client
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.agents import agent_state, agent_runtime

router = APIRouter(prefix="/agents", tags=["client", "agent-runtime"])

def verify_runtime_active():
    settings = get_settings()
    if not settings.agent_runtime_enabled:
        raise HTTPException(
            status_code=400,
            detail="Agent runtime is disabled. Set AGENT_RUNTIME_ENABLED=true to enable it."
        )

# Pydantic Schemas
class AgentRunCreate(BaseModel):
    tenant_id: str = Field(..., max_length=128)
    input_text: str
    user_id: Optional[str] = Field(None, max_length=128)
    correlation_id: Optional[str] = Field(None, max_length=128)

class AgentRunResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    tenant_id: str
    user_id: Optional[str] = None
    status: str
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    total_steps: int
    total_tokens: int
    estimated_cost_brl: float
    started_at: str
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    correlation_id: Optional[str] = None

    class Config:
        from_attributes = True

class AgentRunStepResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    step_number: int
    step_type: str
    input_hash: str
    output_hash: str
    status: str
    latency_ms: Optional[int] = None
    policy_result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

def format_datetime(dt) -> str:
    return dt.isoformat() if dt else ""

def to_run_response(run) -> AgentRunResponse:
    return AgentRunResponse(
        id=run.id,
        agent_id=run.agent_id,
        tenant_id=run.tenant_id,
        user_id=run.user_id,
        status=run.status,
        input_hash=run.input_hash,
        output_hash=run.output_hash,
        total_steps=run.total_steps,
        total_tokens=run.total_tokens,
        estimated_cost_brl=run.estimated_cost_brl,
        started_at=format_datetime(run.started_at),
        completed_at=format_datetime(run.completed_at),
        failure_reason=run.failure_reason,
        correlation_id=run.correlation_id,
    )

def to_step_response(step) -> AgentRunStepResponse:
    return AgentRunStepResponse(
        id=step.id,
        run_id=step.run_id,
        step_number=step.step_number,
        step_type=step.step_type,
        input_hash=step.input_hash,
        output_hash=step.output_hash,
        status=step.status,
        latency_ms=step.latency_ms,
        policy_result=step.policy_result,
        error=step.error,
        created_at=format_datetime(step.created_at),
    )

@router.post("/{agent_id}/runs", response_model=AgentRunResponse, dependencies=[Depends(verify_runtime_active)])
async def create_run(
    agent_id: uuid.UUID,
    payload: AgentRunCreate,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent_id,
            tenant_id=payload.tenant_id,
            input_text=payload.input_text,
            user_id=payload.user_id,
            correlation_id=payload.correlation_id,
        )
        return to_run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except agent_runtime.RuntimeDisabledError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/runs/{run_id}", response_model=AgentRunResponse, dependencies=[Depends(verify_runtime_active)])
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return to_run_response(run)

@router.post("/runs/{run_id}/cancel", response_model=AgentRunResponse, dependencies=[Depends(verify_runtime_active)])
async def cancel_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        run = await agent_runtime.cancel_run(db, run_id)
        return to_run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))

@router.post("/runs/{run_id}/pause", response_model=AgentRunResponse, dependencies=[Depends(verify_runtime_active)])
async def pause_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        run = await agent_runtime.pause_run(db, run_id)
        return to_run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))

@router.post("/runs/{run_id}/resume", response_model=AgentRunResponse, dependencies=[Depends(verify_runtime_active)])
async def resume_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        run = await agent_runtime.resume_run(db, run_id)
        return to_run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))

@router.get("/runs/{run_id}/steps", response_model=List[AgentRunStepResponse], dependencies=[Depends(verify_runtime_active)])
async def get_run_steps(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
        
    steps = await agent_state.get_run_steps(db, run_id)
    return [to_step_response(s) for s in steps]

@router.post("/runs/{run_id}/replay", response_model=Dict[str, Any], dependencies=[Depends(verify_runtime_active)])
async def replay_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        result = await agent_runtime.replay_run(db, run_id)
        # Convert run_id to string and return dictionary
        result["run_id"] = str(result["run_id"])
        result["agent_id"] = str(result["agent_id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except agent_runtime.ReplayDisabledError as e:
        raise HTTPException(status_code=400, detail=str(e))
