import csv
import io
import json
from datetime import datetime, timedelta
from typing import List, Optional

from app.services.runtime_dependencies import get_db_session
from app.models.billing.cost_event import CostEvent
from app.schemas.costs import CostByAgent, CostByTenant, CostByTool, CostEventRead, CostSummary
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/costs", tags=["admin-costs"])


@router.get("/summary", response_model=CostSummary)
async def get_costs_summary(
    tenant_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(
        func.sum(CostEvent.estimated_cost),
        func.count(CostEvent.id)
    )
    
    if tenant_id:
        stmt = stmt.where(CostEvent.tenant_id == tenant_id)
    if start_date:
        stmt = stmt.where(CostEvent.created_at >= start_date)
    if end_date:
        stmt = stmt.where(CostEvent.created_at <= end_date)
        
    res = await db.execute(stmt)
    row = res.one()
    
    return CostSummary(
        total_cost=float(row[0] or 0.0),
        currency="BRL",
        event_count=row[1] or 0
    )


@router.get("/by-agent", response_model=List[CostByAgent])
async def get_costs_by_agent(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(
        CostEvent.agent_id,
        func.sum(CostEvent.estimated_cost).label("total_cost"),
        func.count(CostEvent.id).label("event_count"),
        func.sum(CostEvent.input_tokens).label("input_tokens"),
        func.sum(CostEvent.output_tokens).label("output_tokens")
    ).group_by(CostEvent.agent_id)
    
    if tenant_id:
        stmt = stmt.where(CostEvent.tenant_id == tenant_id)
        
    res = await db.execute(stmt)
    return [
        CostByAgent(
            agent_id=row[0],
            total_cost=float(row[1] or 0.0),
            event_count=row[2] or 0,
            input_tokens=int(row[3] or 0),
            output_tokens=int(row[4] or 0)
        )
        for row in res.all()
    ]


@router.get("/by-tool", response_model=List[CostByTool])
async def get_costs_by_tool(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(
        CostEvent.tool_name,
        func.sum(CostEvent.estimated_cost).label("total_cost"),
        func.count(CostEvent.id).label("event_count")
    ).where(CostEvent.tool_name.isnot(None)).group_by(CostEvent.tool_name)
    
    if tenant_id:
        stmt = stmt.where(CostEvent.tenant_id == tenant_id)
        
    res = await db.execute(stmt)
    return [
        CostByTool(
            tool_name=row[0],
            total_cost=float(row[1] or 0.0),
            event_count=row[2] or 0
        )
        for row in res.all()
    ]


@router.get("/by-tenant", response_model=List[CostByTenant])
async def get_costs_by_tenant(
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(
        CostEvent.tenant_id,
        func.sum(CostEvent.estimated_cost).label("total_cost"),
        func.count(CostEvent.id).label("event_count")
    ).group_by(CostEvent.tenant_id)
    
    res = await db.execute(stmt)
    return [
        CostByTenant(
            tenant_id=row[0],
            total_cost=float(row[1] or 0.0),
            event_count=row[2] or 0
        )
        for row in res.all()
    ]


@router.get("/export")
async def export_costs(
    tenant_id: Optional[str] = None,
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CostEvent).order_by(CostEvent.created_at.desc())
    if tenant_id:
        stmt = stmt.where(CostEvent.tenant_id == tenant_id)
    
    res = await db.execute(stmt)
    events = res.scalars().all()
    
    if format == "json":
        data = [
            {
                "id": str(e.id),
                "tenant_id": e.tenant_id,
                "user_id": e.user_id,
                "agent_id": str(e.agent_id) if e.agent_id else None,
                "workflow_id": e.workflow_id,
                "tool_name": e.tool_name,
                "model": e.model,
                "backend": e.backend,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "latency_ms": e.latency_ms,
                "estimated_cost": e.estimated_cost,
                "currency": e.currency,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]
        return Response(content=json.dumps(data), media_type="application/json")
    
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "tenant_id", "user_id", "agent_id", "workflow_id", "tool_name",
            "model", "backend", "input_tokens", "output_tokens", "latency_ms",
            "estimated_cost", "currency", "created_at"
        ])
        for e in events:
            writer.writerow([
                e.id, e.tenant_id, e.user_id, e.agent_id, e.workflow_id, e.tool_name,
                e.model, e.backend, e.input_tokens, e.output_tokens, e.latency_ms,
                e.estimated_cost, e.currency, e.created_at
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=costs_export.csv"}
        )
