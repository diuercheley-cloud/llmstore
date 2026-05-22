import uuid
import logging
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import (
    AgentRegistryEntry,
    AgentPromotion,
    AgentDeprecation,
    AgentLifecycleEvent,
    AgentEvalBaseline
)
from app.services.agents.agent_registry import get_registry_entry
from app.core.config import get_settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)


async def submit_review(db: AsyncSession, entry_id: uuid.UUID, performed_by: str = "system") -> AgentRegistryEntry:
    """Transitions agent status from draft -> review."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    if entry.status != "draft":
        raise ValueError(f"Cannot submit review: agent is in '{entry.status}' status, must be 'draft'")

    old_status = entry.status
    entry.status = "review"

    event = AgentLifecycleEvent(
        agent_registry_id=entry.id,
        event_type="submit_review",
        from_status=old_status,
        to_status="review",
        performed_by=performed_by,
        notes="Agent submitted for promotion review"
    )
    db.add(event)
    await db.commit()
    await db.refresh(entry)
    return entry


async def approve_agent(
    db: AsyncSession,
    entry_id: uuid.UUID,
    approved_by: str,
    metadata: Optional[Dict[str, Any]] = None,
    performed_by: str = "system"
) -> AgentRegistryEntry:
    """Transitions agent status from review -> approved. Enforces risk-level approvals."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    if entry.status != "review":
        raise ValueError(f"Cannot approve agent: status must be 'review', currently '{entry.status}'")

    # Enforce risk level approval validation
    if entry.risk_level in ("high", "critical"):
        if not approved_by or not approved_by.strip():
            raise ValueError(f"Approval signature ('approved_by') is strictly required for high/critical risk level agents.")

    old_status = entry.status
    entry.status = "approved"

    # Save promotion record
    promotion = AgentPromotion(
        agent_registry_id=entry.id,
        from_status=old_status,
        to_status="approved",
        approved_by=approved_by,
        approved_at=utc_now(),
        promoted_by=performed_by,
        promotion_metadata=metadata
    )
    db.add(promotion)

    # Save lifecycle event
    event = AgentLifecycleEvent(
        agent_registry_id=entry.id,
        event_type="approve",
        from_status=old_status,
        to_status="approved",
        performed_by=performed_by,
        notes=f"Agent approved by {approved_by}"
    )
    db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry


async def activate_agent(db: AsyncSession, entry_id: uuid.UUID, performed_by: str = "system") -> AgentRegistryEntry:
    """Transitions agent status to active (production). Enforces governance gates."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    if entry.status not in ("approved", "paused"):
        raise ValueError(f"Cannot activate agent: status must be 'approved' or 'paused', currently '{entry.status}'")

    # 1. Enforce Owner requirement
    if not entry.owner or not entry.owner.strip():
        raise ValueError("Cannot activate agent: Owner is missing. Owner must be set before activation.")

    # 2. Enforce Evaluation Baseline requirement
    settings = get_settings()
    if settings.agent_production_requires_eval_baseline:
        # Check AgentEvalBaseline table
        res_baseline = await db.execute(
            select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == entry.id)
        )
        if not res_baseline.scalar_one_or_none():
            # Fallback to check if legacy eval_baseline field is populated as string
            if not entry.eval_baseline or not entry.eval_baseline.strip():
                raise ValueError("Cannot activate agent: Evaluation baseline is missing. Eval baseline must be defined and run.")

    # 3. Enforce Version presence
    # Check if a version exists
    result = await db.execute(
        select(AgentPromotion)
        .where(AgentPromotion.agent_registry_id == entry.id)
        .where(AgentPromotion.to_status == "approved")
    )
    approvals = result.scalars().all()

    # 4. Enforce high/critical risk approval signature verification
    if entry.risk_level in ("high", "critical"):
        has_approval = any(app.approved_by for app in approvals)
        if not has_approval:
            raise ValueError("Cannot activate agent: High/critical risk agents require prior approval signature.")

    old_status = entry.status
    entry.status = "active"

    # Create promotion entry for activation
    promotion = AgentPromotion(
        agent_registry_id=entry.id,
        from_status=old_status,
        to_status="active",
        approved_by=performed_by,
        approved_at=utc_now(),
        promoted_by=performed_by,
        promotion_metadata={"notes": "Agent promoted to active (production)"}
    )
    db.add(promotion)

    # Save lifecycle event
    event = AgentLifecycleEvent(
        agent_registry_id=entry.id,
        event_type="activate",
        from_status=old_status,
        to_status="active",
        performed_by=performed_by,
        notes="Agent activated and promoted to production"
    )
    db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry


async def pause_agent(db: AsyncSession, entry_id: uuid.UUID, performed_by: str = "system") -> AgentRegistryEntry:
    """Transitions agent status from active -> paused."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    if entry.status != "active":
        raise ValueError(f"Cannot pause agent: status must be 'active', currently '{entry.status}'")

    old_status = entry.status
    entry.status = "paused"

    # Save lifecycle event
    event = AgentLifecycleEvent(
        agent_registry_id=entry.id,
        event_type="pause",
        from_status=old_status,
        to_status="paused",
        performed_by=performed_by,
        notes="Agent operation paused"
    )
    db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry


async def deprecate_agent(
    db: AsyncSession,
    entry_id: uuid.UUID,
    reason: str,
    replacement_id: Optional[uuid.UUID] = None,
    performed_by: str = "system"
) -> AgentRegistryEntry:
    """Transitions agent status from active -> deprecated."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    if entry.status != "active":
        raise ValueError(f"Cannot deprecate agent: status must be 'active', currently '{entry.status}'")

    if not reason or not reason.strip():
        raise ValueError("A reason must be provided to deprecate an agent.")

    old_status = entry.status
    entry.status = "deprecated"

    # Save deprecation record
    deprecation = AgentDeprecation(
        agent_registry_id=entry.id,
        deprecated_by=performed_by,
        reason=reason,
        replacement_agent_id=replacement_id
    )
    db.add(deprecation)

    # Save lifecycle event
    event = AgentLifecycleEvent(
        agent_registry_id=entry.id,
        event_type="deprecate",
        from_status=old_status,
        to_status="deprecated",
        performed_by=performed_by,
        notes=f"Agent deprecated. Reason: {reason}"
    )
    db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry


async def archive_agent(db: AsyncSession, entry_id: uuid.UUID, performed_by: str = "system") -> AgentRegistryEntry:
    """Transitions agent status from deprecated -> archived."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    if entry.status != "deprecated":
        raise ValueError(f"Cannot archive agent: status must be 'deprecated', currently '{entry.status}'")

    old_status = entry.status
    entry.status = "archived"

    # Save lifecycle event
    event = AgentLifecycleEvent(
        agent_registry_id=entry.id,
        event_type="archive",
        from_status=old_status,
        to_status="archived",
        performed_by=performed_by,
        notes="Agent catalog entry archived"
    )
    db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry
