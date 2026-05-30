# Owner: agent-platform
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.analytics.analytics_queries import AnalyticsQueries
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class AnalyticsAggregator:
    """
    Aggregates all agent metrics for the dashboard.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.queries = AnalyticsQueries(db)

    async def get_dashboard_data(self, tenant_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Gathers all metrics for the specified time range.
        """
        end_time = utc_now()
        start_time = end_time - timedelta(days=days)
        
        success_data = await self.queries.get_run_success_rate(tenant_id, start_time, end_time)
        cost_tokens = await self.queries.get_cost_and_tokens(tenant_id, start_time, end_time)
        tool_metrics = await self.queries.get_tool_metrics(tenant_id, start_time, end_time)
        policy_denials = await self.queries.get_policy_denials(tenant_id, start_time, end_time)
        eval_pass_rate = await self.queries.get_eval_pass_rate(tenant_id, start_time, end_time)

        return {
            "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "run_metrics": {
                "total_runs": success_data["total"],
                "success_rate": success_data["success_rate"],
                "status_distribution": success_data["distribution"]
            },
            "financial_metrics": cost_tokens,
            "operational_metrics": {
                "tool_failure_rate": tool_metrics["tool_failure_rate"],
                "total_tool_calls": tool_metrics["total_tool_calls"],
                "policy_denials_count": policy_denials,
                "eval_pass_rate": eval_pass_rate
            }
        }
        
    async def get_no_data_response(self) -> Dict[str, Any]:
        return {
            "status": "no_data",
            "message": "No agent metrics found for this tenant and time range."
        }
        
