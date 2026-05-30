# Owner: agent-platform
import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.agents import AgentRunMetrics, AgentRunCosts, AgentTimelineEvent
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class AnomalyDetectionService:
    """
    Detects anomalies in agent metrics (cost spikes, failure spikes, etc.)
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_cost_spike(self, agent_id: uuid.UUID, threshold_multiplier: float = 2.0) -> bool:
        """
        Detects if current costs are significantly higher than historical average.
        """
        now = utc_now()
        last_hour = now - timedelta(hours=1)
        prev_24h = now - timedelta(hours=24)

        # 1. Average cost in last 24h
        stmt_avg = select(func.avg(AgentRunCosts.estimated_cost_brl)).where(
            AgentRunCosts.agent_id == agent_id,
            AgentRunCosts.created_at >= prev_24h,
            AgentRunCosts.created_at < last_hour
        )
        res_avg = await self.db.execute(stmt_avg)
        avg_cost = res_avg.scalar_one_or_none() or 0.0

        # 2. Current cost in last hour
        stmt_curr = select(func.sum(AgentRunCosts.estimated_cost_brl)).where(
            AgentRunCosts.agent_id == agent_id,
            AgentRunCosts.created_at >= last_hour
        )
        res_curr = await self.db.execute(stmt_curr)
        curr_cost = res_curr.scalar_one_or_none() or 0.0

        if avg_cost > 0 and curr_cost > (avg_cost * threshold_multiplier):
            logger.warning(f"Cost spike detected for agent {agent_id}: {curr_cost} vs avg {avg_cost}")
            return True
        
        return False

    async def detect_failure_spike(self, agent_id: uuid.UUID) -> bool:
        # Similar logic for tool failures
        return False

    async def run_all_checks(self, agent_id: uuid.UUID) -> List[str]:
        anomalies = []
        if await self.detect_cost_spike(agent_id):
            anomalies.append("cost_spike")
        # Add other checks
        return anomalies
