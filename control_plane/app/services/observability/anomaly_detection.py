# Owner: agent-platform
import logging
import uuid
from datetime import timedelta
from typing import List

from app.core.time import utc_now
from app.models.agents.agents import (
    AgentRunCosts,
    AgentRunMetrics,
    AgentRunStep,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """
    Detects anomalies in agent metrics:
    - Cost spikes (current hour vs 24h average)
    - Failure spikes (tool failures, approval denials)
    - Latency degradation
    - Token usage anomalies
    - Step count anomalies
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_cost_spike(self, agent_id: uuid.UUID, threshold_multiplier: float = 2.0) -> bool:
        now = utc_now()
        last_hour = now - timedelta(hours=1)
        prev_24h = now - timedelta(hours=24)

        stmt_avg = select(func.avg(AgentRunCosts.estimated_cost_brl)).where(
            AgentRunCosts.agent_id == agent_id,
            AgentRunCosts.created_at >= prev_24h,
            AgentRunCosts.created_at < last_hour
        )
        res_avg = await self.db.execute(stmt_avg)
        avg_cost = res_avg.scalar_one_or_none() or 0.0

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

    async def detect_failure_spike(self, agent_id: uuid.UUID, threshold: float = 1.5) -> bool:
        now = utc_now()
        last_hour = now - timedelta(hours=1)
        prev_24h = now - timedelta(hours=24)

        stmt_avg = select(func.count(AgentRunStep.id)).where(
            AgentRunStep.agent_id == agent_id,
            AgentRunStep.step_type.in_(["tool_error", "policy_denied"]),
            AgentRunStep.created_at >= prev_24h,
            AgentRunStep.created_at < last_hour,
        )
        res_avg = await self.db.execute(stmt_avg)
        avg_failures = res_avg.scalar_one_or_none() or 0

        stmt_curr = select(func.count(AgentRunStep.id)).where(
            AgentRunStep.agent_id == agent_id,
            AgentRunStep.step_type.in_(["tool_error", "policy_denied"]),
            AgentRunStep.created_at >= last_hour,
        )
        res_curr = await self.db.execute(stmt_curr)
        curr_failures = res_curr.scalar_one_or_none() or 0

        if avg_failures > 0 and curr_failures > (avg_failures * threshold):
            logger.warning(f"Failure spike detected for agent {agent_id}: {curr_failures} vs avg {avg_failures}")
            return True

        return False

    async def detect_latency_degradation(self, agent_id: uuid.UUID, threshold_ms: float = 5000) -> bool:
        now = utc_now()
        last_hour = now - timedelta(hours=1)

        stmt = select(func.avg(AgentRunMetrics.latency_ms)).where(
            AgentRunMetrics.agent_id == agent_id,
            AgentRunMetrics.created_at >= last_hour,
        )
        res = await self.db.execute(stmt)
        avg_latency = res.scalar_one_or_none() or 0.0

        if avg_latency > threshold_ms:
            logger.warning(f"Latency degradation for agent {agent_id}: avg {avg_latency}ms > {threshold_ms}ms")
            return True

        return False

    async def detect_token_usage_anomaly(self, agent_id: uuid.UUID, threshold_multiplier: float = 3.0) -> bool:
        now = utc_now()
        last_hour = now - timedelta(hours=1)
        prev_24h = now - timedelta(hours=24)

        stmt_avg = select(func.avg(AgentRunCosts.total_tokens)).where(
            AgentRunCosts.agent_id == agent_id,
            AgentRunCosts.created_at >= prev_24h,
            AgentRunCosts.created_at < last_hour,
        )
        res_avg = await self.db.execute(stmt_avg)
        avg_tokens = res_avg.scalar_one_or_none() or 0.0

        stmt_curr = select(func.avg(AgentRunCosts.total_tokens)).where(
            AgentRunCosts.agent_id == agent_id,
            AgentRunCosts.created_at >= last_hour,
        )
        res_curr = await self.db.execute(stmt_curr)
        curr_tokens = res_curr.scalar_one_or_none() or 0.0

        if avg_tokens > 0 and curr_tokens > (avg_tokens * threshold_multiplier):
            logger.warning(f"Token usage anomaly for agent {agent_id}: {curr_tokens} vs avg {avg_tokens}")
            return True

        return False

    async def run_all_checks(self, agent_id: uuid.UUID) -> List[str]:
        anomalies = []
        if await self.detect_cost_spike(agent_id):
            anomalies.append("cost_spike")
        if await self.detect_failure_spike(agent_id):
            anomalies.append("failure_spike")
        if await self.detect_latency_degradation(agent_id):
            anomalies.append("latency_degradation")
        if await self.detect_token_usage_anomaly(agent_id):
            anomalies.append("token_usage_anomaly")
        return anomalies
