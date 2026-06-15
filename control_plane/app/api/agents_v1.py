# Owner: agent-platform
# Surface: client
import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.agents.agents import AgentDefinition, AgentRunEvent
from app.models.core.client import Client
from app.services.agents import agent_api_facade, agent_state
from app.services.agents.sessions.agent_session_service import AgentSessionService
from app.services.agents.sessions.conversation_thread_service import ConversationThreadService
from app.services.auth import require_client
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["client", "agents-api"])


@router.post("")
async def create_agent(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> dict[str, Any]:
    """
    Creates a new agent definition for the tenant.
    """
    agent_data = {**data, "tenant_id": str(client.id), "owner": client.name}
    agent = await agent_state.create_agent_definition(db, agent_data)
    return {
        "id": str(agent.id),
        "name": agent.name,
        "version": agent.version,
        "status": agent.status,
    }


@router.get("")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> list[dict[str, Any]]:
    """
    Lists all agents belonging to the tenant.
    """
    stmt = select(AgentDefinition).where(AgentDefinition.tenant_id == str(client.id))
    res = await db.execute(stmt)
    agents = res.scalars().all()
    return [
        {"id": str(a.id), "name": a.name, "version": a.version, "status": a.status} for a in agents
    ]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> dict[str, Any]:
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
        "status": agent.status,
    }


@router.post("/{agent_id}/runs")
async def start_run(
    agent_id: uuid.UUID,
    input_text: str = Body(..., embed=True),
    session_id: uuid.UUID | None = Body(None, embed=True),
    is_simulation: bool = Body(False, embed=True),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> dict[str, Any]:
    """
    Starts a new execution run for the specified agent.
    """
    try:
        run = await agent_api_facade.validate_and_start_run(
            db=db,
            agent_id=agent_id,
            tenant_id=str(client.id),
            input_text=input_text,
            session_id=session_id,
            is_simulation=is_simulation,
            is_admin=False,
        )
    except agent_api_facade.PolicyDenialError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))

    if run.session_id:
        thread_svc = ConversationThreadService(db)
        await thread_svc.add_message(
            session_id=run.session_id,
            role="user",
            content=input_text,
            run_id=run.id,
        )
        session_svc = AgentSessionService(db)
        await session_svc.link_run_to_session(run.session_id, run.id)
        await session_svc.touch_session(run.session_id)
        await db.commit()

    return {
        "id": str(run.id),
        "session_id": str(run.session_id) if run.session_id else None,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "is_simulation": getattr(run, "is_simulation", False),
        "simulation_report": getattr(run, "simulation_report", None),
    }


@router.get("/runs/{run_id}")
async def get_run_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> dict[str, Any]:
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
        "failure_reason": run.failure_reason,
        "is_simulation": getattr(run, "is_simulation", False),
        "simulation_report": getattr(run, "simulation_report", None),
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(require_client),
) -> dict[str, Any]:
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
            db=db, run_id=run_id, tenant_id=str(client.id), is_admin=False
        )
    except ValueError:
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
            stmt = (
                select(AgentRunEvent)
                .where(AgentRunEvent.run_id == run_id)
                .order_by(AgentRunEvent.created_at.asc())
            )
            res = await db.execute(stmt)
            events = res.scalars().all()

            for event in events[last_event_count:]:
                sanitized = agent_api_facade.sanitize_payload(event.payload or {})
                yield f"event: {event.event_type}\ndata: {json.dumps(sanitized)}\n\n"
                last_event_count += 1

            # Check if run finished
            current_run = await agent_state.get_agent_run(db, run_id)
            if not current_run:
                yield 'event: run_failed\ndata: {"status":"failed","failure_reason":"Run not found"}\n\n'
                break
            if current_run.status in ["completed", "failed", "cancelled"]:
                # Fetch any remaining events logged right at the end
                stmt = (
                    select(AgentRunEvent)
                    .where(AgentRunEvent.run_id == run_id)
                    .order_by(AgentRunEvent.created_at.asc())
                )
                res = await db.execute(stmt)
                events = res.scalars().all()
                for event in events[last_event_count:]:
                    sanitized = agent_api_facade.sanitize_payload(event.payload or {})
                    yield f"event: {event.event_type}\ndata: {json.dumps(sanitized)}\n\n"
                    last_event_count += 1
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
