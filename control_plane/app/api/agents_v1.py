# Surface: client
import uuid
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.auth import require_client
from app.models.client import Client
from app.models.agents import AgentDefinition, AgentRun, AgentRunStep, AgentRunEvent
from app.services.agents import agent_state, agent_api_facade
from app.services.agents.agent_executor import AgentExecutor
from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyDecision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["client", "agents-api"])

@router.post("")
async def create_agent(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    """
    Creates a new agent definition for the tenant.
    """
    agent_data = {
        **data,
        "tenant_id": str(client.id),
        "owner": client.name
    }
    agent = await agent_state.create_agent_definition(db, agent_data)
    return {
        "id": str(agent.id),
        "name": agent.name,
        "version": agent.version,
        "status": agent.status
    }

@router.get("")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> List[Dict[str, Any]]:
    """
    Lists all agents belonging to the tenant.
    """
    stmt = select(AgentDefinition).where(AgentDefinition.tenant_id == str(client.id))
    res = await db.execute(stmt)
    agents = res.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "version": a.version,
            "status": a.status
        }
        for a in agents
    ]

@router.get("/{agent_id}")
async def get_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    """
    Gets details of a specific agent.
    """
    agent = await agent_state.get_agent_definition(db, agent_id)
    if not agent or agent.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "version": agent.version,
        "instructions": agent.instructions,
        "model_id": agent.model_id,
        "allowed_tools": agent.allowed_tools,
        "status": agent.status
    }

@router.post("/{agent_id}/runs")
async def start_run(
    agent_id: uuid.UUID,
    input_text: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    """
    Starts a new execution run for the specified agent.
    """
    try:
        run = await agent_api_facade.validate_and_start_run(
            db=db,
            agent_id=agent_id,
            tenant_id=str(client.id),
            input_text=input_text,
            is_admin=False
        )
    except agent_api_facade.PolicyDenialError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    
    return {
        "id": str(run.id),
        "status": run.status,
        "started_at": run.started_at.isoformat()
    }

@router.get("/runs/{run_id}")
async def get_run_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    """
    Gets the current status and summary of an agent run.
    """
    run = await agent_state.get_agent_run(db, run_id)
    if not run or run.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "id": str(run.id),
        "agent_id": str(run.agent_id),
        "status": run.status,
        "total_steps": run.total_steps,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "failure_reason": run.failure_reason
    }

@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> Dict[str, Any]:
    """
    Cancels a running agent execution.
    """
    run = await agent_state.get_agent_run(db, run_id)
    if not run or run.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status in ["completed", "failed", "cancelled"]:
        return {"status": run.status, "message": "Run already finished"}
        
    try:
        await agent_api_facade.validate_and_cancel_run(
            db=db,
            run_id=run_id,
            tenant_id=str(client.id),
            is_admin=False
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Run not found")
        
    return {"status": "cancelled"}

@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
):
    """
    Streams agent execution events using Server-Sent Events (SSE).
    """
    run = await agent_state.get_agent_run(db, run_id)
    if not run or run.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="Run not found")

    settings = get_settings()

    async def event_generator() -> AsyncGenerator[str, None]:
        runtime_active = (
            settings.agent_runtime_enabled
            and settings.agent_execution_enabled
            and settings.agent_async_execution_enabled
        )
        if not runtime_active:
            yield f"event: run.status\ndata: {json.dumps({'status': run.status, 'mode': 'advisory_only'})}\n\n"
            yield f"event: run.idle\ndata: {json.dumps({'status': run.status, 'reason': 'agent_execution_disabled_by_default'})}\n\n"
            return
        
        last_event_count = 0
        while True:
            # Poll for new events from AgentRunEvent
            stmt = select(AgentRunEvent).where(AgentRunEvent.run_id == run_id).order_by(AgentRunEvent.created_at.asc())
            res = await db.execute(stmt)
            events = res.scalars().all()
            
            for event in events[last_event_count:]:
                sanitized = agent_api_facade.sanitize_payload(event.payload or {})
                yield f"event: {event.event_type}\ndata: {json.dumps(sanitized)}\n\n"
                last_event_count += 1

            # Check if run finished
            current_run = await agent_state.get_agent_run(db, run_id)
            if not current_run:
                yield "event: run_failed\ndata: {\"status\":\"failed\",\"failure_reason\":\"Run not found\"}\n\n"
                break
            if current_run.status in ["completed", "failed", "cancelled"]:
                # Fetch any remaining events logged right at the end
                stmt = select(AgentRunEvent).where(AgentRunEvent.run_id == run_id).order_by(AgentRunEvent.created_at.asc())
                res = await db.execute(stmt)
                events = res.scalars().all()
                for event in events[last_event_count:]:
                    sanitized = agent_api_facade.sanitize_payload(event.payload or {})
                    yield f"event: {event.event_type}\ndata: {json.dumps(sanitized)}\n\n"
                    last_event_count += 1
                break
                
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
