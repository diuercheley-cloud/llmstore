import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.api.deps import require_admin, get_db_session
from app.models.agents import AgentRun, AgentRunStep, AgentRunEvent, AgentDefinition
from app.services.agents.agent_observability import AgentObservabilityService

router = APIRouter(prefix="/admin/agents/observability", tags=["agent-observability"])

@router.get("/overview")
async def get_observability_overview(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Returns an overview of agent runs across the platform.
    """
    # Summary of runs by status
    stmt_status = select(AgentRun.status, func.count(AgentRun.id)).group_by(AgentRun.status)
    res_status = await db.execute(stmt_status)
    status_counts = {status: count for status, count in res_status.all()}

    # Recent runs
    stmt_recent = select(AgentRun).order_by(desc(AgentRun.started_at)).limit(10)
    res_recent = await db.execute(stmt_recent)
    recent_runs = [
        {
            "id": str(run.id),
            "agent_id": str(run.agent_id),
            "status": run.status,
            "total_steps": run.total_steps,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
        for run in res_recent.scalars().all()
    ]

    return {
        "status_distribution": status_counts,
        "recent_runs": recent_runs,
        "total_runs": sum(status_counts.values())
    }

@router.get("/runs/{run_id}/timeline")
async def get_run_timeline(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """
    Returns a chronological list of steps and events for a specific agent run.
    """
    # Fetch steps
    stmt_steps = select(AgentRunStep).where(AgentRunStep.run_id == run_id).order_by(AgentRunStep.step_number.asc())
    res_steps = await db.execute(stmt_steps)
    steps = res_steps.scalars().all()

    # Fetch events
    stmt_events = select(AgentRunEvent).where(AgentRunEvent.run_id == run_id).order_by(AgentRunEvent.created_at.asc())
    res_events = await db.execute(stmt_events)
    events = res_events.scalars().all()

    # Combine and sort
    timeline = []
    for step in steps:
        timeline.append({
            "timestamp": step.created_at.isoformat(),
            "type": "step",
            "step_number": step.step_number,
            "step_type": step.step_type,
            "status": step.status,
            "latency_ms": step.latency_ms,
            "error": step.error,
        })
    
    for event in events:
        timeline.append({
            "timestamp": event.created_at.isoformat(),
            "type": "event",
            "event_type": event.event_type,
            "payload": event.payload,
        })
    
    timeline.sort(key=lambda x: x["timestamp"])
    return timeline

@router.get("/runs/{run_id}/trace")
async def get_run_trace(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Returns an OpenTelemetry-compatible trace representation of the agent run.
    """
    # Fetch run with agent definition
    stmt_run = select(AgentRun).where(AgentRun.id == run_id)
    res_run = await db.execute(stmt_run)
    run = res_run.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    obs = AgentObservabilityService()
    
    # Root span
    root_trace = {
        "trace_id": uuid.uuid4().hex, # Placeholder trace ID
        "span_id": uuid.uuid4().hex[:16],
        "name": f"Agent Run: {run.agent_id}",
        "kind": "SERVER",
        "start_time": run.started_at.isoformat(),
        "end_time": run.completed_at.isoformat() if run.completed_at else None,
        "attributes": obs.get_trace_attributes(run),
        "status": {"code": "OK" if run.status == "completed" else "ERROR" if run.status == "failed" else "UNSET"},
        "spans": []
    }

    # Child spans for steps
    stmt_steps = select(AgentRunStep).where(AgentRunStep.run_id == run_id).order_by(AgentRunStep.step_number.asc())
    res_steps = await db.execute(stmt_steps)
    steps = res_steps.scalars().all()

    for step in steps:
        step_span = {
            "span_id": uuid.uuid4().hex[:16],
            "parent_id": root_trace["span_id"],
            "name": f"Step {step.step_number}: {step.step_type}",
            "kind": "INTERNAL",
            "start_time": step.created_at.isoformat(),
            "attributes": obs.get_trace_attributes(run, step),
            "status": {"code": "OK" if step.status == "success" else "ERROR"},
        }
        root_trace["spans"].append(step_span)

    return root_trace

@router.get("/metrics/summary")
async def get_metrics_summary(
    agent_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Returns a summary of metrics for agents.
    """
    # Average latency
    stmt_latency = select(func.avg(AgentRunStep.latency_ms))
    if agent_id:
        stmt_latency = stmt_latency.join(AgentRun).where(AgentRun.agent_id == agent_id)
    
    res_latency = await db.execute(stmt_latency)
    avg_latency = res_latency.scalar() or 0

    # Token usage
    stmt_tokens = select(func.sum(AgentRun.total_tokens), func.sum(AgentRun.estimated_cost_brl))
    if agent_id:
        stmt_tokens = stmt_tokens.where(AgentRun.agent_id == agent_id)
    
    res_tokens = await db.execute(stmt_tokens)
    tokens_row = res_tokens.one()
    total_tokens = tokens_row[0] or 0
    total_cost = tokens_row[1] or 0.0

    return {
        "avg_step_latency_ms": float(avg_latency),
        "total_tokens": int(total_tokens),
        "total_cost_brl": float(total_cost),
    }
