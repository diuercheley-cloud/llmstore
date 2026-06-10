# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agents import (
    AgentDeprecation,
    AgentEvalBaseline,
    AgentEvalRun,
    AgentEvalSuite,
    AgentLifecycleEvent,
    AgentPromotion,
    AgentPromotionGateResult,
    AgentRegistryEntry,
)
from app.services.agents.agent_registry import get_registry_entry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def submit_review(db: AsyncSession, entry_id: uuid.UUID, performed_by: str = "system") -> AgentRegistryEntry:
    """Transitions agent status from draft -> review."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    if entry.status != "draft":
        raise ValueError(f"Cannot submit review: agent is in '{entry.status}' status, must be 'draft'")

    # Enforce evaluation dry-run requirement (at least one completed eval run)
    settings = get_settings()
    if settings.agent_evals_enabled:
        # Fetch suites for the agent entry
        res_suites = await db.execute(select(AgentEvalSuite.id).where(AgentEvalSuite.agent_id == entry.id))
        suite_ids = res_suites.scalars().all()
        if not suite_ids:
            raise ValueError("Cannot submit review: At least one completed evaluation dry-run is required.")
        
        res_runs = await db.execute(
            select(AgentEvalRun.id)
            .where(AgentEvalRun.suite_id.in_(suite_ids))
            .where(AgentEvalRun.status == "completed")
        )
        if not res_runs.scalars().first():
            raise ValueError("Cannot submit review: At least one completed evaluation dry-run is required.")

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
            raise ValueError("Approval signature ('approved_by') is strictly required for high/critical risk level agents.")

    # Enforce Evaluation Baseline requirement
    settings = get_settings()
    if settings.agent_production_requires_eval_baseline:
        res_baseline = await db.execute(
            select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == entry.id)
        )
        baseline = res_baseline.scalar_one_or_none()
        if not baseline:
            raise ValueError("Cannot approve agent: Evaluation baseline is missing. Baseline must be set before approval.")
        if getattr(baseline, "is_stale", False):
            raise ValueError("Cannot approve agent: Evaluation baseline is stale. A new baseline must be set before approval.")

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
        promotion_step_metadata=metadata
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

    # 2. Enforce Evaluation Baseline and Gate requirement
    settings = get_settings()
    if settings.agent_production_requires_eval_baseline or settings.agent_promotion_requires_evals:

        # Check AgentEvalBaseline table
        res_baseline = await db.execute(
            select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == entry.id)
        )
        baseline = res_baseline.scalar_one_or_none()
        if not baseline:
            # Fallback to check if legacy eval_baseline field is populated as string
            if not entry.eval_baseline or not entry.eval_baseline.strip():
                raise ValueError("Cannot activate agent: Evaluation baseline is missing. Eval baseline must be defined and run.")
        else:
            if getattr(baseline, "is_stale", False):
                raise ValueError("Cannot activate agent: Evaluation baseline is stale. A new evaluation is required before activation.")

            # Check AgentPromotionGateResult
            res_gate = await db.execute(
                select(AgentPromotionGateResult)
                .where(AgentPromotionGateResult.agent_id == entry.id)
                .order_by(AgentPromotionGateResult.created_at.desc())
            )
            gate_res = res_gate.scalars().first()
            if not gate_res:
                raise ValueError("Cannot activate agent: Promotion gate verification has not been run.")
            if not gate_res.passed and not gate_res.audit_override:
                raise ValueError("Cannot activate agent: Promotion gate verification failed. Override required to proceed.")

            # Rule: production_ready exige gateway ou real provider
            run_id_to_check = gate_res.baseline_run_id or (baseline.run_id if baseline else None)
            if run_id_to_check:
                res_run = await db.execute(
                    select(AgentEvalRun).where(AgentEvalRun.id == run_id_to_check)
                )
                eval_run = res_run.scalar_one_or_none()
                if eval_run and eval_run.metadata_json:
                    eval_provider = eval_run.metadata_json.get("provider", "unknown")
                    if eval_provider == "mock" and not settings.agent_eval_allow_mock_for_promotion:
                        raise ValueError("Cannot activate agent: Production-ready agents require evaluation via gateway or real provider.")

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
        promotion_step_metadata={"notes": "Agent promoted to active (production)"}
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
