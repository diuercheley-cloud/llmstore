# Owner: agent-platform
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.agents.analytics.analytics_aggregator import AnalyticsAggregator

router = APIRouter()

@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    """
    Returns aggregated metrics for the agent analytics dashboard.
    """
    aggregator = AnalyticsAggregator(db)
    data = await aggregator.get_dashboard_data(current_user.tenant_id, days=days)
    
    if data["run_metrics"]["total_runs"] == 0:
        return await aggregator.get_no_data_response()
        
    return data
