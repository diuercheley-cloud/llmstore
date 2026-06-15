import logging
from typing import Any

from app.models.agents.agent_events import AgentEventSubscription, AgentEventTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def publish(
        self, db: AsyncSession, event_type: str, payload: dict[str, Any], tenant_id: str
    ):
        """
        Finds matching AgentEventSubscription and AgentEventTrigger and queues them for delivery.
        """
        from app.services.agents.events.event_triggers import fire_trigger

        logger.info(f"Publishing event {event_type} for tenant {tenant_id}")

        # 1. Find subscriptions for this event type
        stmt = select(AgentEventSubscription).where(
            AgentEventSubscription.event_type == event_type,
            AgentEventSubscription.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        subscriptions = result.scalars().all()

        for sub in subscriptions:
            # 2. Find associated triggers for this agent that are active
            trigger_stmt = select(AgentEventTrigger).where(
                AgentEventTrigger.agent_id == sub.agent_id,
                AgentEventTrigger.tenant_id == tenant_id,
                AgentEventTrigger.is_paused == False,
            )
            trigger_result = await db.execute(trigger_stmt)
            triggers = trigger_result.scalars().all()

            for trigger in triggers:
                # Fire the trigger for this event
                await fire_trigger(db, trigger.id, payload)


event_bus = EventBus()
