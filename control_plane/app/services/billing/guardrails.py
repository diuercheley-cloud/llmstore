import logging
from datetime import date
from uuid import UUID

from app.core.config import get_settings
from app.models.billing.request_financial import RequestFinancial
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_global_provider_cost_today(session: AsyncSession) -> float:
    today = date.today()
    try:
        stmt = select(func.sum(RequestFinancial.provider_cost_brl)).where(
            func.date(RequestFinancial.created_at) == today
        )
        result = await session.execute(stmt)
        return float(result.scalar() or 0.0)
    except Exception as e:
        logger.error(f"Error fetching global provider cost: {e}")
        return 0.0


async def get_client_provider_cost_today(session: AsyncSession, client_id: UUID) -> float:
    today = date.today()
    try:
        stmt = select(func.sum(RequestFinancial.provider_cost_brl)).where(
            RequestFinancial.client_id == str(client_id),
            func.date(RequestFinancial.created_at) == today,
        )
        result = await session.execute(stmt)
        return float(result.scalar() or 0.0)
    except Exception as e:
        logger.error(f"Error fetching client provider cost: {e}")
        return 0.0


async def is_cloud_blocked_by_guardrails(
    session: AsyncSession, client_id: UUID
) -> tuple[bool, str | None]:
    if settings.deployment_mode != "saas":
        return False, None

    # 1. Check global limit
    global_cost = await get_global_provider_cost_today(session)
    if (
        settings.max_global_provider_cost_per_day_brl > 0
        and global_cost >= settings.max_global_provider_cost_per_day_brl
    ):
        return (
            True,
            f"Global SaaS provider cost limit reached (R$ {global_cost:.2f} >= R$ {settings.max_global_provider_cost_per_day_brl:.2f})",
        )

    # 2. Check client limit
    client_cost = await get_client_provider_cost_today(session, client_id)
    if (
        settings.max_client_provider_cost_per_day_brl > 0
        and client_cost >= settings.max_client_provider_cost_per_day_brl
    ):
        return (
            True,
            f"Client daily provider cost limit reached (R$ {client_cost:.2f} >= R$ {settings.max_client_provider_cost_per_day_brl:.2f})",
        )

    return False, None
