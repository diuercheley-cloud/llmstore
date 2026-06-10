import asyncio
import logging
import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_events import AgentEventDelivery, AgentEventTrigger
from app.services.agents.agent_runtime import start_run
from app.services.agents.events.event_deduplication import sanitize_payload
from app.services.agents.events.event_policy import check_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def evaluate_trigger(db: AsyncSession, trigger_id: uuid.UUID, payload: Dict[str, Any]) -> bool:
    """
    Checks if a trigger should fire.
    """
    settings = get_settings()
    if not settings.agent_event_driven_enabled:
        return False

    stmt = select(AgentEventTrigger).where(AgentEventTrigger.id == trigger_id)
    result = await db.execute(stmt)
    trigger = result.scalar_one_or_none()
    
    if not trigger:
        return False
        
    return await check_policy(db, trigger)

async def fire_trigger(db: AsyncSession, trigger_id: uuid.UUID, payload: Dict[str, Any]) -> bool:
    """
    Creates an AgentEventDelivery record and triggers an async AgentRun.
    """
    settings = get_settings()
    if not settings.agent_event_driven_enabled:
        logger.warning("Event-driven agent execution is disabled by feature flag.")
        return False

    stmt = select(AgentEventTrigger).where(AgentEventTrigger.id == trigger_id)
    result = await db.execute(stmt)
    trigger = result.scalar_one_or_none()
    
    if not trigger:
        logger.error(f"Trigger {trigger_id} not found")
        return False

    # Check policy before firing
    if not await check_policy(db, trigger):
        logger.info(f"Trigger {trigger_id} policy check failed (rate limit, budget or paused).")
        return False

    # Sanitize payload recursively so secrets are not exposed in DB logs or tasks
    sanitized_payload = sanitize_payload(payload)

    # Create delivery record
    delivery = AgentEventDelivery(
        trigger_id=trigger.id,
        event_payload=sanitized_payload,
        status="pending",
        created_at=utc_now()
    )
    db.add(delivery)
    await db.flush()

    delivery_id = delivery.id
    agent_id = trigger.agent_id
    tenant_id = trigger.tenant_id
    input_text = sanitized_payload.get("input_text") or trigger.config.get("default_input", "Event triggered execution")

    # Spawn async run execution background task using a separate session
    asyncio.create_task(_run_agent_in_background(agent_id, tenant_id, input_text, delivery_id))
    await db.commit()
    return True

async def _run_agent_in_background(agent_id: uuid.UUID, tenant_id: str, input_text: str, delivery_id: uuid.UUID):
    from app.db.session import SessionLocal
    from app.models.agents.agent_events import AgentEventDelivery
    
    logger.info(f"Starting background AgentRun for agent={agent_id} delivery={delivery_id}")
    
    async with SessionLocal() as db:
        try:
            run = await start_run(
                db=db,
                agent_id=agent_id,
                tenant_id=tenant_id,
                input_text=input_text,
                correlation_id=str(delivery_id)
            )
            
            stmt = select(AgentEventDelivery).where(AgentEventDelivery.id == delivery_id)
            result = await db.execute(stmt)
            delivery = result.scalar_one_or_none()
            if delivery:
                delivery.agent_run_id = run.id
                delivery.status = "delivered"
                delivery.delivered_at = utc_now()
            await db.commit()
            logger.info(f"Background AgentRun started successfully: run={run.id} delivery={delivery_id}")
        except Exception as e:
            logger.exception(f"Failed background AgentRun starting for delivery={delivery_id}: {e}")
            try:
                stmt = select(AgentEventDelivery).where(AgentEventDelivery.id == delivery_id)
                result = await db.execute(stmt)
                delivery = result.scalar_one_or_none()
                if delivery:
                    delivery.status = "failed"
                await db.commit()
            except Exception:
                logger.exception("Failed to update event delivery status to failed")
