# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.models.agent_service import AgentServiceUsage
from app.services.agent_service.agent_rate_limits import AgentRateLimitService
from app.services.agent_service.agent_tiers import AgentTierService
from app.services.agent_service.sync_mode import SyncInvocationService
from app.services.agents import agent_runtime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class AgentServiceAPI:
    """
    Orchestrates the Agent-as-a-Service layer.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tiers = AgentTierService(db)
        self.rate_limits = AgentRateLimitService()
        self.sync_invoker = SyncInvocationService(db)

    async def invoke_agent(
        self, agent_id: uuid.UUID, tenant_id: str, input_text: str, mode: str = "async", tier_name: str = "free"
    ) -> Dict[str, Any]:
        # 1. Check Tier and Rate Limit
        tier = await self.tiers.get_tier(tier_name)
        if not tier:
            raise ValueError(f"Tier {tier_name} not found")

        if not await self.rate_limits.check_rate_limit(tenant_id, tier.rate_limit_per_minute):
            return {"status": "error", "message": "Rate limit exceeded"}

        # 2. Invoke based on mode
        if mode == "sync":
            # Check if tier allows sync
            if not tier.features.get("sync_mode", True):
                 return {"status": "error", "message": "Sync mode not allowed for this tier"}
            
            result = await self.sync_invoker.invoke_sync(agent_id, tenant_id, input_text)
            await self._record_usage(agent_id, tenant_id, uuid.UUID(result["run_id"]), tier.id, "sync")
            return result
        else:
            run = await agent_runtime.start_run(self.db, agent_id, tenant_id, input_text)
            await self._record_usage(agent_id, tenant_id, run.id, tier.id, "async")
            return {"run_id": str(run.id), "status": run.status}

    async def _record_usage(self, agent_id: uuid.UUID, tenant_id: str, run_id: uuid.UUID, tier_id: uuid.UUID, mode: str):
        existing = await self.db.execute(
            select(AgentServiceUsage).where(AgentServiceUsage.run_id == run_id)
        )
        if existing.scalar_one_or_none() is not None:
            return
        usage = AgentServiceUsage(
            agent_id=agent_id,
            tenant_id=tenant_id,
            run_id=run_id,
            tier_id=tier_id,
            invocation_mode=mode
        )
        self.db.add(usage)
        await self.db.flush()
