import logging
import uuid
from typing import Optional

from app.models.billing.cost_event import CostEvent
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CostAttributionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        agent_id: Optional[uuid.UUID] = None,
        workflow_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        model: Optional[str] = None,
        backend: Optional[str] = None,
        route_decision_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: Optional[int] = None,
        estimated_cost: float = 0.0,
        currency: str = "USD",
        cost_policy_version: Optional[str] = None,
    ) -> CostEvent:
        """
        Records a CostEvent for unified cost attribution.
        """
        event = CostEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            workflow_id=workflow_id,
            tool_name=tool_name,
            model=model,
            backend=backend,
            route_decision_id=route_decision_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
            currency=currency,
            cost_policy_version=cost_policy_version,
        )
        self.db.add(event)
        # Flush to ensure the event has an ID, but don't commit to allow transaction control
        await self.db.flush()
        return event
