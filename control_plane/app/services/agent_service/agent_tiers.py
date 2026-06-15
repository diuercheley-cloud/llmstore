# Owner: agent-platform
import logging

from app.models.agents.agent_service import AgentServiceTier
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentTierService:
    """
    Manages service tiers for agent consumers.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tier(self, tier_name: str) -> AgentServiceTier | None:
        stmt = select(AgentServiceTier).where(AgentServiceTier.name == tier_name)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_default_tiers(self):
        """Seed default tiers if they don't exist."""
        tiers = [
            {"name": "free", "rate_limit": 5, "monthly": 100},
            {"name": "pro", "rate_limit": 50, "monthly": 10000},
            {"name": "enterprise", "rate_limit": 500, "monthly": 1000000},
        ]
        for t in tiers:
            existing = await self.get_tier(t["name"])
            if not existing:
                tier = AgentServiceTier(
                    name=t["name"],
                    rate_limit_per_minute=t["rate_limit"],
                    monthly_run_limit=t["monthly"],
                )
                self.db.add(tier)
        await self.db.flush()
