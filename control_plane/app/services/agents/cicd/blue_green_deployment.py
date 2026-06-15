# Owner: agent-platform
import logging
import uuid
from collections.abc import Iterable
from typing import Any

from app.core.time import utc_now
from app.models.agents.agent_cicd import AgentDeployment, AgentDeploymentEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BlueGreenDeploymentService:
    """
    Manages Blue/Green deployment strategy for agents.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_deployment(
        self,
        agent_id: uuid.UUID,
        environment: str,
        strategy: str = "blue-green",
        pipeline_id: uuid.UUID | None = None,
        version_tag: str | None = None,
        rollout_metadata: dict[str, Any] | None = None,
    ) -> AgentDeployment:
        deployment = AgentDeployment(
            agent_id=agent_id,
            pipeline_id=pipeline_id,
            environment=environment,
            strategy=strategy,
            version_tag=version_tag or f"v-{utc_now().strftime('%Y%m%d%H%M%S')}",
            status="in_progress",
            traffic_weight=0.0,  # Green version starts with 0 traffic
        )
        self.db.add(deployment)
        await self.db.flush()

        await self._record_event(
            deployment.id,
            "deployment_started",
            {
                "strategy": strategy,
                "environment": environment,
                "version_tag": deployment.version_tag,
                "pipeline_id": str(pipeline_id) if pipeline_id else None,
                "rollout_metadata": rollout_metadata or {},
            },
        )
        return deployment

    async def switch_traffic(self, deployment_id: uuid.UUID, weight: float):
        """
        Adjusts traffic weight for the 'green' (new) deployment.
        """
        stmt = select(AgentDeployment).where(AgentDeployment.id == deployment_id)
        res = await self.db.execute(stmt)
        deployment = res.scalar_one_or_none()
        if not deployment:
            return

        deployment.traffic_weight = weight
        if not deployment.status:
            deployment.status = "in_progress"
        await self._record_event(deployment_id, "traffic_switch", {"weight": weight})

        if weight >= 1.0:
            deployment.status = "completed"
            deployment.completed_at = utc_now()

        await self.db.flush()

    async def _record_event(self, deployment_id: uuid.UUID, event_type: str, details: dict):
        event = AgentDeploymentEvent(
            deployment_id=deployment_id, event_type=event_type, details=details
        )
        self.db.add(event)

    async def progressive_rollout(
        self,
        deployment_id: uuid.UUID,
        weights: Iterable[float] | None = None,
        *,
        require_healthy: bool = True,
        healthy: bool = True,
    ) -> bool:
        rollout_weights = [float(weight) for weight in (weights or [0.1, 0.5, 1.0])]
        rollout_weights = [min(1.0, max(0.0, weight)) for weight in rollout_weights]
        if not rollout_weights or rollout_weights[-1] < 1.0:
            rollout_weights.append(1.0)

        for weight in rollout_weights:
            await self.switch_traffic(deployment_id, weight)
            await self._record_event(
                deployment_id,
                "rollout_step_completed",
                {"weight": weight, "healthy": healthy},
            )
            if require_healthy and not healthy:
                await self.mark_failed(
                    deployment_id, f"Health checks failed at traffic weight {weight}"
                )
                return False

        return True

    async def pause_deployment(self, deployment_id: uuid.UUID, reason: str | None = None) -> bool:
        deployment = await self._get_deployment(deployment_id)
        if not deployment:
            return False
        deployment.status = "paused"
        await self._record_event(
            deployment_id, "deployment_paused", {"reason": reason or "manual_pause"}
        )
        await self.db.flush()
        return True

    async def resume_deployment(self, deployment_id: uuid.UUID, reason: str | None = None) -> bool:
        deployment = await self._get_deployment(deployment_id)
        if not deployment:
            return False
        if deployment.status == "paused":
            deployment.status = "in_progress"
        await self._record_event(
            deployment_id, "deployment_resumed", {"reason": reason or "manual_resume"}
        )
        await self.db.flush()
        return True

    async def mark_failed(self, deployment_id: uuid.UUID, reason: str) -> bool:
        deployment = await self._get_deployment(deployment_id)
        if not deployment:
            return False
        deployment.status = "failed"
        await self._record_event(deployment_id, "deployment_failed", {"reason": reason})
        await self.db.flush()
        return True

    async def _get_deployment(self, deployment_id: uuid.UUID) -> AgentDeployment | None:
        stmt = select(AgentDeployment).where(AgentDeployment.id == deployment_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
