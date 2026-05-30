# Owner: agent-platform
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent_cicd import AgentDeployment, AgentDeploymentEvent
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class BlueGreenDeploymentService:
    """
    Manages Blue/Green deployment strategy for agents.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_deployment(self, agent_id: uuid.UUID, environment: str, strategy: str = "blue-green") -> AgentDeployment:
        deployment = AgentDeployment(
            agent_id=agent_id,
            environment=environment,
            strategy=strategy,
            version_tag=f"v-{utc_now().strftime('%Y%m%d%H%M%S')}",
            status="in_progress",
            traffic_weight=0.0 # Green version starts with 0 traffic
        )
        self.db.add(deployment)
        await self.db.flush()
        
        await self._record_event(deployment.id, "deployment_started", {"strategy": strategy})
        return deployment

    async def switch_traffic(self, deployment_id: uuid.UUID, weight: float):
        """
        Adjusts traffic weight for the 'green' (new) deployment.
        """
        stmt = select(AgentDeployment).where(AgentDeployment.id == deployment_id)
        res = await self.db.execute(stmt)
        deployment = res.scalar_one_or_none()
        if not deployment: return

        deployment.traffic_weight = weight
        await self._record_event(deployment_id, "traffic_switch", {"weight": weight})
        
        if weight >= 1.0:
            deployment.status = "completed"
            deployment.completed_at = utc_now()
            
        await self.db.flush()

    async def _record_event(self, deployment_id: uuid.UUID, event_type: str, details: dict):
        event = AgentDeploymentEvent(
            deployment_id=deployment_id,
            event_type=event_type,
            details=details
        )
        self.db.add(event)
