# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, Optional

from app.models.agents.agent_deployments import AgentApiDeployment, AgentApiSlaEvent
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DeploymentSlaService:
    """Monitors and enforces SLA configuration for deployments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_sla_config(self, deployment: AgentApiDeployment) -> Dict[str, Any]:
        return {
            "timeout_seconds": deployment.timeout_seconds,
            "max_concurrency": deployment.max_concurrency,
            "retry_max_attempts": deployment.retry_max_attempts,
            "retry_backoff_ms": deployment.retry_backoff_ms,
            "rate_limit_per_minute": deployment.rate_limit_per_minute,
            "rate_limit_per_day": deployment.rate_limit_per_day,
        }

    async def update_sla(
        self,
        deployment: AgentApiDeployment,
        timeout_seconds: Optional[int] = None,
        max_concurrency: Optional[int] = None,
        retry_max_attempts: Optional[int] = None,
        retry_backoff_ms: Optional[int] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_day: Optional[int] = None,
    ) -> AgentApiDeployment:
        if timeout_seconds is not None:
            deployment.timeout_seconds = max(1, min(300, timeout_seconds))
        if max_concurrency is not None:
            deployment.max_concurrency = max(1, min(1000, max_concurrency))
        if retry_max_attempts is not None:
            deployment.retry_max_attempts = max(0, min(10, retry_max_attempts))
        if retry_backoff_ms is not None:
            deployment.retry_backoff_ms = max(0, min(30000, retry_backoff_ms))
        if rate_limit_per_minute is not None:
            deployment.rate_limit_per_minute = max(1, min(100000, rate_limit_per_minute))
        if rate_limit_per_day is not None:
            deployment.rate_limit_per_day = max(1, min(10000000, rate_limit_per_day))

        await self.db.flush()
        return deployment

    async def get_sla_events(
        self,
        deployment_id: uuid.UUID,
        limit: int = 50,
    ) -> list[AgentApiSlaEvent]:
        from sqlalchemy import select
        stmt = (
            select(AgentApiSlaEvent)
            .where(AgentApiSlaEvent.deployment_id == deployment_id)
            .order_by(AgentApiSlaEvent.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_sla_summary(self, deployment_id: uuid.UUID) -> Dict[str, Any]:
        """Get SLA health summary for a deployment."""
        from app.models.agents.agent_deployments import AgentApiUsageEvent
        from sqlalchemy import func, select

        # Total invocations
        total_stmt = select(func.count()).where(
            AgentApiUsageEvent.deployment_id == deployment_id
        )
        total = (await self.db.execute(total_stmt)).scalar() or 0

        # Failed invocations
        failed_stmt = select(func.count()).where(
            AgentApiUsageEvent.deployment_id == deployment_id,
            AgentApiUsageEvent.status.in_(["failed", "timeout"]),
        )
        failed = (await self.db.execute(failed_stmt)).scalar() or 0

        # Average latency
        avg_stmt = select(func.avg(AgentApiUsageEvent.latency_ms)).where(
            AgentApiUsageEvent.deployment_id == deployment_id,
            AgentApiUsageEvent.latency_ms.isnot(None),
        )
        avg_latency = (await self.db.execute(avg_stmt)).scalar()

        # SLA events count
        events_stmt = select(func.count()).where(
            AgentApiSlaEvent.deployment_id == deployment_id
        )
        events_count = (await self.db.execute(events_stmt)).scalar() or 0

        return {
            "total_invocations": total,
            "failed_invocations": failed,
            "success_rate": round((total - failed) / max(total, 1) * 100, 2),
            "avg_latency_ms": round(avg_latency, 1) if avg_latency else None,
            "sla_events_count": events_count,
        }
