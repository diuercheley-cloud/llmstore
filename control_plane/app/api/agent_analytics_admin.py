# Owner: agent-platform
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.api import deps
from app.services.agents.analytics.agent_analytics import AgentAnalyticsService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/admin/agents/analytics", tags=["agent-analytics"])


def _get_time_range(
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    days: int
) -> tuple[datetime, datetime]:
    """Helper to parse or fallback time range parameters."""
    if not end_time:
        end_time = datetime.now(timezone.utc)
    else:
        # Ensure tz-aware
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
            
    if not start_time:
        start_time = end_time - timedelta(days=days)
    else:
        # Ensure tz-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
    return start_time, end_time


@router.get("/overview")
async def get_overview(
    days: int = Query(7, ge=1, le=365),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Returns aggregated high-level metrics overview for all agents of the tenant."""
    start_dt, end_dt = _get_time_range(start_time, end_time, days)
    tenant_id = current_user.tenant_id
    
    data = await AgentAnalyticsService.get_overview(
        db=db,
        tenant_id=tenant_id,
        start_time=start_dt,
        end_time=end_dt
    )
    return data


@router.get("/{agent_id}")
async def get_agent_metrics(
    agent_id: str,
    days: int = Query(7, ge=1, le=365),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Returns detailed overview metrics for a single agent."""
    start_dt, end_dt = _get_time_range(start_time, end_time, days)
    tenant_id = current_user.tenant_id

    data = await AgentAnalyticsService.get_agent_metrics(
        db=db,
        tenant_id=tenant_id,
        agent_id=agent_id,
        start_time=start_dt,
        end_time=end_dt
    )
    return data


@router.get("/{agent_id}/costs")
async def get_agent_costs(
    agent_id: str,
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(7, ge=1, le=365),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Returns cost trend points for a single agent."""
    start_dt, end_dt = _get_time_range(start_time, end_time, days)
    tenant_id = current_user.tenant_id

    data = await AgentAnalyticsService.get_cost_trend(
        db=db,
        tenant_id=tenant_id,
        agent_id=agent_id,
        start_time=start_dt,
        end_time=end_dt,
        granularity=granularity
    )
    return data


@router.get("/{agent_id}/latency")
async def get_agent_latency(
    agent_id: str,
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(7, ge=1, le=365),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Returns latency trend points for a single agent."""
    start_dt, end_dt = _get_time_range(start_time, end_time, days)
    tenant_id = current_user.tenant_id

    data = await AgentAnalyticsService.get_latency_trend(
        db=db,
        tenant_id=tenant_id,
        agent_id=agent_id,
        start_time=start_dt,
        end_time=end_dt,
        granularity=granularity
    )
    return data


@router.get("/{agent_id}/tools")
async def get_agent_tools(
    agent_id: str,
    days: int = Query(7, ge=1, le=365),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """Returns tool invocation metrics breakdown for a single agent."""
    start_dt, end_dt = _get_time_range(start_time, end_time, days)
    tenant_id = current_user.tenant_id

    data = await AgentAnalyticsService.get_tools_usage(
        db=db,
        tenant_id=tenant_id,
        agent_id=agent_id,
        start_time=start_dt,
        end_time=end_dt
    )
    return data


@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """
    Returns aggregated metrics for the agent analytics dashboard.
    """
    from app.services.agents.analytics.analytics_aggregator import AnalyticsAggregator
    aggregator = AnalyticsAggregator(db)
    data = await aggregator.get_dashboard_data(current_user.tenant_id, days=days)
    
    if data["run_metrics"]["total_runs"] == 0:
        return await aggregator.get_no_data_response()
        
    return data

