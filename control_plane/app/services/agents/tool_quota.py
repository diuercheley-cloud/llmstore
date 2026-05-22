"""
Owner: agent-platform
Status: beta
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.agent_tool_execution import AgentToolQuotaCounter

logger = logging.getLogger(__name__)


class QuotaExceededError(ValueError):
    """Raised when an agent tool invocation exceeds the defined quota limit."""
    pass


# Default daily limits
DEFAULT_LIMIT_TENANT = 1000
DEFAULT_LIMIT_AGENT = 500
DEFAULT_LIMIT_TOOL = 200
DEFAULT_LIMIT_SIDE_EFFECT = {
    "destructive": 5,
    "write": 50,
    "read": 500,
    "none": 1000,
    "external": 100
}


async def check_and_increment_quota(
    db: AsyncSession,
    tenant_id: str,
    agent_id: Optional[Any] = None,
    tool_id: Optional[Any] = None,
    side_effect_level: Optional[str] = None,
) -> None:
    """Enforces quota limits per tenant, agent, tool, and side effect level.
    
    If quota is exceeded, raises QuotaExceededError. Otherwise, increments the counters.
    All counters operate in a 24-hour window from midnight to midnight UTC.
    """
    now = utc_now()
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=1)

    # Define targets to check and increment
    # Format: (query_filters, default_limit, description)
    targets = []

    # 1. Tenant limit
    targets.append(({
        "tenant_id": tenant_id,
        "agent_id": None,
        "agent_tool_id": None,
        "side_effect_level": None
    }, DEFAULT_LIMIT_TENANT, f"Tenant {tenant_id} daily quota"))

    # 2. Agent limit (if agent_id provided)
    if agent_id:
        targets.append(({
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "agent_tool_id": None,
            "side_effect_level": None
        }, DEFAULT_LIMIT_AGENT, f"Agent {agent_id} daily quota"))

    # 3. Tool limit (if tool_id provided)
    if tool_id:
        targets.append(({
            "tenant_id": tenant_id,
            "agent_id": None,
            "agent_tool_id": tool_id,
            "side_effect_level": None
        }, DEFAULT_LIMIT_TOOL, f"Tool {tool_id} daily quota"))

    # 4. Side effect level limit (if level provided)
    if side_effect_level:
        limit = DEFAULT_LIMIT_SIDE_EFFECT.get(side_effect_level, 100)
        targets.append(({
            "tenant_id": tenant_id,
            "agent_id": None,
            "agent_tool_id": None,
            "side_effect_level": side_effect_level
        }, limit, f"Side-effect level '{side_effect_level}' daily quota"))

    # Check all targets before incrementing any to ensure atomicity
    counters_to_save = []
    
    for filters, default_limit, desc in targets:
        stmt = select(AgentToolQuotaCounter).where(
            AgentToolQuotaCounter.tenant_id == filters["tenant_id"],
            AgentToolQuotaCounter.agent_id == filters["agent_id"],
            AgentToolQuotaCounter.agent_tool_id == filters["agent_tool_id"],
            AgentToolQuotaCounter.side_effect_level == filters["side_effect_level"],
            AgentToolQuotaCounter.window_start == window_start
        )
        res = await db.execute(stmt)
        counter = res.scalar_one_or_none()

        if not counter:
            # Create a new counter for this window
            counter = AgentToolQuotaCounter(
                tenant_id=filters["tenant_id"],
                agent_id=filters["agent_id"],
                agent_tool_id=filters["agent_tool_id"],
                side_effect_level=filters["side_effect_level"],
                window_start=window_start,
                window_end=window_end,
                invocation_count=0,
                max_limit=default_limit
            )
            db.add(counter)
            # Need to flush to put in session
            await db.flush()

        if counter.invocation_count >= counter.max_limit:
            logger.warning(f"Quota exceeded: {desc} ({counter.invocation_count}/{counter.max_limit})")
            raise QuotaExceededError(f"Quota exceeded for: {desc} (limit: {counter.max_limit})")

        counter.invocation_count += 1
        counters_to_save.append(counter)

    # Save increments
    await db.flush()
