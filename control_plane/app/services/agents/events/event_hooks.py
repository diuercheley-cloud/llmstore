import logging
from typing import Any

from app.services.agents.events.event_bus import event_bus
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def notify_internal_event(
    db: AsyncSession, event_type: str, payload: dict[str, Any], tenant_id: str
):
    """
    Called by internal services (metrics, health, security) to notify the Agent Event Bus.
    """
    logger.info(f"Internal event hook triggered: {event_type} for tenant {tenant_id}")
    await event_bus.publish(db, event_type, payload, tenant_id)


# Specific hooks for convenience
async def on_readiness_degraded(db: AsyncSession, tenant_id: str, details: dict[str, Any]):
    await notify_internal_event(db, "on_readiness_degraded", details, tenant_id)


async def on_cost_threshold_exceeded(db: AsyncSession, tenant_id: str, details: dict[str, Any]):
    await notify_internal_event(db, "on_cost_threshold", details, tenant_id)


async def on_security_event(db: AsyncSession, tenant_id: str, details: dict[str, Any]):
    await notify_internal_event(db, "on_security_event", details, tenant_id)
