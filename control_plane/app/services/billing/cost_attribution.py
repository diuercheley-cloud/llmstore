import logging
import uuid

from app.models.billing.cost_event import CostEvent
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CostAttributionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        tenant_id: str,
        user_id: str | None = None,
        agent_id: uuid.UUID | None = None,
        workflow_id: str | None = None,
        tool_name: str | None = None,
        model: str | None = None,
        backend: str | None = None,
        route_decision_id: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int | None = None,
        estimated_cost: float = 0.0,
        currency: str = "USD",
        cost_policy_version: str | None = None,
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
