# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, Optional

from app.core.time import utc_now
from app.models.agent_deployments import AgentApiDeployment, AgentApiUsageEvent
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DeploymentUsageService:
    """Tracks and reports usage/billing for deployment invocations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_invocation(
        self,
        deployment: AgentApiDeployment,
        run_id: Optional[uuid.UUID],
        endpoint_key_id: Optional[uuid.UUID],
        mode: str,
        status: str,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        latency_ms: Optional[int] = None,
        tokens_used: int = 0,
        cost_brl: float = 0.0,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> AgentApiUsageEvent:
        event = AgentApiUsageEvent(
            deployment_id=deployment.id,
            tenant_id=deployment.tenant_id,
            run_id=run_id,
            endpoint_key_id=endpoint_key_id,
            mode=mode,
            status=status,
            input_text=input_text[:1000] if input_text else None,  # truncate
            output_text=output_text[:1000] if output_text else None,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_brl=cost_brl,
            error_message=error_message,
            client_ip=client_ip,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def complete_invocation(
        self,
        event: AgentApiUsageEvent,
        status: str,
        output_text: Optional[str] = None,
        latency_ms: Optional[int] = None,
        tokens_used: int = 0,
        cost_brl: float = 0.0,
        error_message: Optional[str] = None,
    ):
        event.status = status
        event.output_text = output_text[:1000] if output_text else None
        event.latency_ms = latency_ms
        event.tokens_used = tokens_used
        event.cost_brl = cost_brl
        event.error_message = error_message
        event.completed_at = utc_now()
        await self.db.flush()

    async def get_usage_stats(
        self,
        deployment_id: uuid.UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get usage statistics for a deployment."""
        from datetime import timedelta
        since = utc_now() - timedelta(days=days)

        base = select(AgentApiUsageEvent).where(
            AgentApiUsageEvent.deployment_id == deployment_id,
            AgentApiUsageEvent.created_at >= since,
        )

        # Total invocations
        total = (await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )).scalar() or 0

        # Successful invocations
        success = (await self.db.execute(
            select(func.count()).select_from(
                select(AgentApiUsageEvent).where(
                    AgentApiUsageEvent.deployment_id == deployment_id,
                    AgentApiUsageEvent.created_at >= since,
                    AgentApiUsageEvent.status == "completed",
                ).subquery()
            )
        )).scalar() or 0

        # Total cost
        total_cost = (await self.db.execute(
            select(func.sum(AgentApiUsageEvent.cost_brl)).where(
                AgentApiUsageEvent.deployment_id == deployment_id,
                AgentApiUsageEvent.created_at >= since,
            )
        )).scalar() or 0.0

        # Total tokens
        total_tokens = (await self.db.execute(
            select(func.sum(AgentApiUsageEvent.tokens_used)).where(
                AgentApiUsageEvent.deployment_id == deployment_id,
                AgentApiUsageEvent.created_at >= since,
            )
        )).scalar() or 0

        # Average latency
        avg_latency = (await self.db.execute(
            select(func.avg(AgentApiUsageEvent.latency_ms)).where(
                AgentApiUsageEvent.deployment_id == deployment_id,
                AgentApiUsageEvent.created_at >= since,
                AgentApiUsageEvent.latency_ms.isnot(None),
            )
        )).scalar()

        # Sync vs async breakdown
        sync_count = (await self.db.execute(
            select(func.count()).where(
                AgentApiUsageEvent.deployment_id == deployment_id,
                AgentApiUsageEvent.created_at >= since,
                AgentApiUsageEvent.mode == "sync",
            )
        )).scalar() or 0

        return {
            "period_days": days,
            "total_invocations": total,
            "successful_invocations": success,
            "success_rate": round(success / max(total, 1) * 100, 2),
            "total_cost_brl": round(float(total_cost), 4),
            "total_tokens": total_tokens,
            "avg_latency_ms": round(float(avg_latency), 1) if avg_latency else None,
            "sync_invocations": sync_count,
            "async_invocations": total - sync_count,
        }

    async def get_usage_events(
        self,
        deployment_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentApiUsageEvent]:
        stmt = (
            select(AgentApiUsageEvent)
            .where(AgentApiUsageEvent.deployment_id == deployment_id)
            .order_by(AgentApiUsageEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
