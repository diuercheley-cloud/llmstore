import logging
import uuid

from app.models.agents.agent_service import AgentServiceTier, AgentServiceUsage
from app.services.agents.wallets.agent_wallet import AgentWalletService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentUsageMeter:
    """
    Unified metering service that tracks agent usage,
    applies pricing, debits wallets, and records billing data.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_svc = AgentWalletService(db)

    async def get_or_create_tier(self, name: str) -> AgentServiceTier:
        stmt = select(AgentServiceTier).where(AgentServiceTier.name == name)
        res = await self.db.execute(stmt)
        tier = res.scalar_one_or_none()
        if tier:
            return tier
        defaults = {
            "free": {
                "rate_limit_per_minute": 10,
                "monthly_run_limit": 100,
                "price_per_run_brl": 0.0,
                "price_per_1k_tokens_brl": 0.0,
                "monthly_fee_brl": 0.0,
            },
            "pro": {
                "rate_limit_per_minute": 60,
                "monthly_run_limit": 10000,
                "price_per_run_brl": 0.01,
                "price_per_1k_tokens_brl": 0.02,
                "monthly_fee_brl": 29.0,
            },
            "enterprise": {
                "rate_limit_per_minute": 300,
                "monthly_run_limit": 100000,
                "price_per_run_brl": 0.005,
                "price_per_1k_tokens_brl": 0.01,
                "monthly_fee_brl": 99.0,
            },
        }
        cfg = defaults.get(name, defaults["free"])
        tier = AgentServiceTier(name=name, **cfg)
        self.db.add(tier)
        await self.db.flush()
        await self.db.refresh(tier)
        return tier

    async def record_run_usage(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        tokens_consumed: int,
        cost_estimated_brl: float,
        tier_name: str = "free",
        invocation_mode: str = "async",
    ) -> AgentServiceUsage:
        existing_stmt = select(AgentServiceUsage).where(AgentServiceUsage.run_id == run_id)
        existing_res = await self.db.execute(existing_stmt)
        existing = existing_res.scalar_one_or_none()
        if existing is not None:
            return existing

        tier = await self.get_or_create_tier(tier_name)

        usage = AgentServiceUsage(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            tier_id=tier.id,
            tokens_consumed=tokens_consumed,
            cost_estimated_brl=cost_estimated_brl,
            invocation_mode=invocation_mode,
        )
        self.db.add(usage)

        # Calculate charge
        run_charge = tier.price_per_run_brl
        token_charge = (tokens_consumed / 1000.0) * tier.price_per_1k_tokens_brl
        total_charge = round(run_charge + token_charge, 4)

        if total_charge > 0:
            try:
                await self.wallet_svc.spend(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    amount_brl=total_charge,
                    description=f"Run {run_id}: {tokens_consumed} tokens @ {tier.name} tier",
                )
            except Exception as e:
                logger.warning(f"Wallet spend failed for run {run_id}: {e}")

        await self.db.flush()
        return usage

    async def get_monthly_usage(
        self,
        tenant_id: str,
        agent_id: uuid.UUID | None = None,
    ) -> dict:
        stmt = select(
            func.count(AgentServiceUsage.id),
            func.sum(AgentServiceUsage.tokens_consumed),
            func.sum(AgentServiceUsage.cost_estimated_brl),
        ).where(AgentServiceUsage.tenant_id == tenant_id)

        if agent_id:
            stmt = stmt.where(AgentServiceUsage.agent_id == agent_id)

        res = await self.db.execute(stmt)
        row = res.one()
        return {
            "total_runs": row[0] or 0,
            "total_tokens": row[1] or 0,
            "total_cost_brl": round(float(row[2] or 0.0), 2),
        }

    async def check_run_allowed(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        tier_name: str = "free",
    ) -> bool:
        tier = await self.get_or_create_tier(tier_name)
        stmt = select(func.count(AgentServiceUsage.id)).where(
            AgentServiceUsage.tenant_id == tenant_id,
            AgentServiceUsage.agent_id == agent_id,
        )
        res = await self.db.execute(stmt)
        monthly_runs = res.scalar_one() or 0
        return monthly_runs < tier.monthly_run_limit
