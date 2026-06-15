"""
Owner: agent-platform
Status: beta
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_tool_execution import AgentToolRollbackAction, AgentToolSideEffect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def register_side_effect(
    db: AsyncSession,
    tenant_id: str,
    invocation_id: Any,
    side_effect_level: str,
    description: str,
    resource_id: str | None = None,
    change_payload: dict[str, Any] | None = None,
) -> AgentToolSideEffect:
    """Registers a side effect produced by a tool invocation."""
    side_effect = AgentToolSideEffect(
        invocation_id=invocation_id,
        tenant_id=tenant_id,
        side_effect_level=side_effect_level,
        description=description,
        resource_id=resource_id,
        change_payload=change_payload,
    )
    db.add(side_effect)
    await db.flush()
    return side_effect


async def register_rollback_action(
    db: AsyncSession,
    tenant_id: str,
    side_effect_id: Any,
    compensation_action: str,
    compensation_payload: dict[str, Any],
) -> AgentToolRollbackAction:
    """Registers a compensation action to roll back/revert a side effect."""
    action = AgentToolRollbackAction(
        side_effect_id=side_effect_id,
        tenant_id=tenant_id,
        compensation_action=compensation_action,
        compensation_payload=compensation_payload,
        status="pending",
    )
    db.add(action)
    await db.flush()
    return action


async def execute_rollback_action(
    db: AsyncSession,
    tenant_id: str,
    action_id: Any,
    rollback_callable: Callable[..., Any] | None = None,
) -> bool:
    """Executes a registered rollback action to run its compensation logic."""
    stmt = select(AgentToolRollbackAction).where(
        AgentToolRollbackAction.id == action_id, AgentToolRollbackAction.tenant_id == tenant_id
    )
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        logger.error(f"Rollback action {action_id} not found for tenant {tenant_id}")
        return False

    if action.status in ("success", "in_progress"):
        logger.info(f"Rollback action {action_id} is already in state: {action.status}")
        return True

    action.status = "in_progress"
    await db.flush()

    try:
        if rollback_callable:
            if asyncio.iscoroutinefunction(rollback_callable):
                await rollback_callable(**action.compensation_payload)
            else:
                await asyncio.to_thread(rollback_callable, **action.compensation_payload)
        else:
            # Simulated compensation if no programmatic hook provided
            logger.info(
                f"Simulating compensation action '{action.compensation_action}' with payload: {action.compensation_payload}"
            )

        action.status = "success"
        action.executed_at = utc_now()
        action.error_message = None
    except Exception as e:
        logger.exception(f"Rollback action {action_id} execution failed: {e}")
        action.status = "failed"
        action.error_message = str(e)
        await db.flush()
        return False

    await db.flush()
    return True


async def rollback_invocation_side_effects(
    db: AsyncSession,
    tenant_id: str,
    invocation_id: Any,
    rollback_callable: Callable[..., Any] | None = None,
) -> bool:
    """Automatically rolls back all side effects of an invocation in reverse chronological order."""
    settings = get_settings()
    if not settings.agent_tool_rollback_enabled:
        logger.info("Automatic tool rollback is disabled by feature flag.")
        return False

    # Get side effects for the invocation
    stmt = (
        select(AgentToolSideEffect)
        .where(
            AgentToolSideEffect.invocation_id == invocation_id,
            AgentToolSideEffect.tenant_id == tenant_id,
        )
        .order_by(AgentToolSideEffect.created_at.desc())
    )  # reverse order!

    res = await db.execute(stmt)
    side_effects = res.scalars().all()

    all_success = True
    for effect in side_effects:
        # Fetch pending rollback actions for each side effect
        action_stmt = select(AgentToolRollbackAction).where(
            AgentToolRollbackAction.side_effect_id == effect.id,
            AgentToolRollbackAction.status == "pending",
        )
        action_res = await db.execute(action_stmt)
        actions = action_res.scalars().all()

        for action in actions:
            success = await execute_rollback_action(db, tenant_id, action.id, rollback_callable)
            if not success:
                all_success = False

    return all_success
