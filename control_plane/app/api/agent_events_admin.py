# Owner: agent-platform
import uuid
from typing import Optional

from app.api.deps import get_admin_token, get_db
from app.core.config import get_settings
from app.models.agent_events import (
    AgentEventDelivery,
    AgentEventSource,
    AgentEventSubscription,
    AgentEventTrigger,
    AgentScheduledTrigger,
    AgentWebhookTrigger,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def verify_event_driven_enabled():
    settings = get_settings()
    if not settings.agent_event_driven_enabled:
        raise HTTPException(status_code=403, detail="Event-driven agent execution is disabled by feature flag.")

router = APIRouter(
    prefix="/admin/agents",
    tags=["agent-events-admin"],
    dependencies=[Depends(verify_event_driven_enabled)]
)

class EventSourceCreate(BaseModel):
    type: str
    config: dict = Field(default_factory=dict)
    tenant_id: str

class EventTriggerCreate(BaseModel):
    agent_id: uuid.UUID
    source_id: Optional[uuid.UUID] = None
    trigger_type: str
    config: dict = Field(default_factory=dict)
    rate_limit: Optional[int] = None
    budget: Optional[float] = None
    tenant_id: str

class EventSubscriptionCreate(BaseModel):
    event_type: str
    agent_id: uuid.UUID
    tenant_id: str

@router.post("/event-sources")
async def create_event_source(source_in: EventSourceCreate, db: AsyncSession = Depends(get_db), _admin = Depends(get_admin_token)):
    source = AgentEventSource(
        type=source_in.type,
        config=source_in.config,
        tenant_id=source_in.tenant_id
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source

@router.post("/event-triggers")
async def create_event_trigger(trigger_in: EventTriggerCreate, db: AsyncSession = Depends(get_db), _admin = Depends(get_admin_token)):
    trigger = AgentEventTrigger(
        agent_id=trigger_in.agent_id,
        source_id=trigger_in.source_id,
        trigger_type=trigger_in.trigger_type,
        config=trigger_in.config,
        rate_limit=trigger_in.rate_limit,
        budget=trigger_in.budget,
        tenant_id=trigger_in.tenant_id
    )
    db.add(trigger)
    await db.flush()

    # Automatically create the concrete trigger details (cron schedules / webhook secrets) if applicable
    if trigger.trigger_type == "on_schedule":
        cron_expr = trigger.config.get("cron_expression", "* * * * *")
        tz_str = trigger.config.get("timezone", "UTC")
        
        from app.core.time import utc_now
        from app.services.agents.events.cron_triggers import calculate_next_run
        next_run = calculate_next_run(cron_expr, utc_now(), tz_str)
        
        scheduled = AgentScheduledTrigger(
            trigger_id=trigger.id,
            cron_expression=cron_expr,
            timezone=tz_str,
            next_run_at=next_run
        )
        db.add(scheduled)
        
        # Subscribe agent to its own schedule event
        sub = AgentEventSubscription(
            event_type="on_schedule",
            agent_id=trigger.agent_id,
            tenant_id=trigger.tenant_id
        )
        db.add(sub)
        
    elif trigger.trigger_type == "on_webhook":
        secret = trigger.config.get("secret", "default_secret")
        sig_header = trigger.config.get("signature_header", "X-Agent-Signature")
        
        webhook = AgentWebhookTrigger(
            trigger_id=trigger.id,
            secret_hash=secret,
            signature_header=sig_header
        )
        db.add(webhook)
        
        # Subscribe agent to its own webhook event
        sub = AgentEventSubscription(
            event_type="on_webhook",
            agent_id=trigger.agent_id,
            tenant_id=trigger.tenant_id
        )
        db.add(sub)
        
    else:
        # For internal/custom triggers, automatically create subscription
        sub = AgentEventSubscription(
            event_type=trigger.trigger_type,
            agent_id=trigger.agent_id,
            tenant_id=trigger.tenant_id
        )
        db.add(sub)

    await db.commit()
    await db.refresh(trigger)
    return trigger

@router.get("/event-triggers")
async def list_event_triggers(tenant_id: Optional[str] = None, db: AsyncSession = Depends(get_db), _admin = Depends(get_admin_token)):
    stmt = select(AgentEventTrigger)
    if tenant_id:
        stmt = stmt.where(AgentEventTrigger.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/event-triggers/{trigger_id}/pause")
async def pause_trigger(trigger_id: uuid.UUID, db: AsyncSession = Depends(get_db), _admin = Depends(get_admin_token)):
    stmt = select(AgentEventTrigger).where(AgentEventTrigger.id == trigger_id)
    result = await db.execute(stmt)
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    trigger.is_paused = True
    await db.commit()
    return {"status": "paused"}

@router.post("/event-triggers/{trigger_id}/resume")
async def resume_trigger(trigger_id: uuid.UUID, db: AsyncSession = Depends(get_db), _admin = Depends(get_admin_token)):
    stmt = select(AgentEventTrigger).where(AgentEventTrigger.id == trigger_id)
    result = await db.execute(stmt)
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    trigger.is_paused = False
    await db.commit()
    return {"status": "resumed"}

@router.get("/event-deliveries")
async def list_event_deliveries(trigger_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db), _admin = Depends(get_admin_token)):
    stmt = select(AgentEventDelivery)
    if trigger_id:
        stmt = stmt.where(AgentEventDelivery.trigger_id == trigger_id)
    stmt = stmt.order_by(AgentEventDelivery.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/event-subscriptions")
async def create_event_subscription(sub_in: EventSubscriptionCreate, db: AsyncSession = Depends(get_db), _admin = Depends(get_admin_token)):
    sub = AgentEventSubscription(
        event_type=sub_in.event_type,
        agent_id=sub_in.agent_id,
        tenant_id=sub_in.tenant_id
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub
