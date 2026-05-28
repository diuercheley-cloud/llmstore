import logging
from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_events import AgentEventTrigger, AgentEventDelivery
from app.core.time import utc_now

logger = logging.getLogger(__name__)

async def check_policy(db: AsyncSession, trigger: AgentEventTrigger) -> bool:
    """
    Validates rate limits and budgets using AgentEventDelivery history and trigger config.
    """
    if trigger.is_paused:
        logger.info(f"Trigger {trigger.id} is paused.")
        return False

    # Check rate limit (max events per hour)
    if trigger.rate_limit:
        one_hour_ago = utc_now() - timedelta(hours=1)
        stmt = select(func.count(AgentEventDelivery.id)).where(
            AgentEventDelivery.trigger_id == trigger.id,
            AgentEventDelivery.created_at >= one_hour_ago
        )
        result = await db.execute(stmt)
        count = result.scalar_one()
        if count >= trigger.rate_limit:
            logger.warning(f"Trigger {trigger.id} exceeded rate limit: {count} >= {trigger.rate_limit}")
            return False

    # Check budget: aggregate cost of runs initiated by this trigger
    if trigger.budget:
        from app.models.agents import AgentRun
        stmt = (
            select(func.sum(AgentRun.estimated_cost_brl))
            .join(AgentEventDelivery, AgentEventDelivery.agent_run_id == AgentRun.id)
            .where(AgentEventDelivery.trigger_id == trigger.id)
        )
        result = await db.execute(stmt)
        total_cost = result.scalar() or 0.0
        if total_cost >= trigger.budget:
            logger.warning(f"Trigger {trigger.id} exceeded budget: {total_cost} >= {trigger.budget}")
            return False

    return True
