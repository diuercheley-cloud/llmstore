import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_deployments import AgentApiDeployment, AgentApiUsageEvent
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DeploymentAutoscaler:
    """
    Horizontally auto-scales agent deployments based on real-time load.
    Adjusts concurrency_limit and rate_limit to match demand.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._watchers: Dict[uuid.UUID, asyncio.Task] = {}

    async def evaluate(self, deployment_id: uuid.UUID) -> Optional[int]:
        stmt = select(AgentApiDeployment).where(AgentApiDeployment.id == deployment_id)
        res = await self.db.execute(stmt)
        deploy = res.scalar_one_or_none()
        if not deploy or deploy.status != "active":
            return None

        now = time.time()
        window_sec = self.settings.deployment_autoscale_window_sec
        since = utc_now().timestamp() - window_sec

        count_stmt = (
            select(func.count())
            .select_from(AgentApiUsageEvent)
            .where(
                AgentApiUsageEvent.deployment_id == deployment_id,
                AgentApiUsageEvent.created_at >= since,
            )
        )
        count_res = await self.db.execute(count_stmt)
        recent_count = count_res.scalar_one()

        prev_stmt = (
            select(func.count())
            .select_from(AgentApiUsageEvent)
            .where(
                AgentApiUsageEvent.deployment_id == deployment_id,
                AgentApiUsageEvent.created_at < since,
                AgentApiUsageEvent.created_at >= (utc_now().timestamp() - 2 * window_sec),
            )
        )
        prev_res = await self.db.execute(prev_stmt)
        prev_count = prev_res.scalar_one()

        trend = recent_count / max(prev_count, 1)

        current_capacity = deploy.max_concurrency * deploy.rate_limit_per_minute
        target_concurrency = deploy.concurrency_limit

        if trend > 1.5 and recent_count > deploy.max_concurrency * 10:
            target = min(deploy.max_concurrency * 2, deploy.max_concurrency + 5)
            if target > deploy.concurrency_limit:
                logger.info(
                    f"Scaling UP deployment {deployment_id}: "
                    f"concurrency {deploy.concurrency_limit} -> {target} "
                    f"(trend={trend:.2f}, recent={recent_count})"
                )
                deploy.concurrency_limit = target
                deploy.rate_limit_per_minute = int(deploy.rate_limit_per_minute * 1.5)
                await self.db.flush()
                return target

        elif trend < 0.5 and deploy.concurrency_limit > 1:
            target = max(1, deploy.concurrency_limit // 2)
            logger.info(
                f"Scaling DOWN deployment {deployment_id}: "
                f"concurrency {deploy.concurrency_limit} -> {target} "
                f"(trend={trend:.2f}, recent={recent_count})"
            )
            deploy.concurrency_limit = target
            deploy.rate_limit_per_minute = max(10, int(deploy.rate_limit_per_minute * 0.75))
            await self.db.flush()
            return -target

        return None

    async def watch(self, deployment_id: uuid.UUID, interval_sec: int = 30):
        if deployment_id in self._watchers and not self._watchers[deployment_id].done():
            return

        async def _loop():
            try:
                while True:
                    await self.evaluate(deployment_id)
                    await asyncio.sleep(interval_sec)
            except asyncio.CancelledError:
                pass

        self._watchers[deployment_id] = asyncio.create_task(_loop())

    def stop_watching(self, deployment_id: uuid.UUID):
        task = self._watchers.pop(deployment_id, None)
        if task and not task.done():
            task.cancel()

    async def evaluate_all(self) -> List[Dict]:
        stmt = select(AgentApiDeployment).where(AgentApiDeployment.status == "active")
        res = await self.db.execute(stmt)
        results = []
        for deploy in res.scalars().all():
            change = await self.evaluate(deploy.id)
            results.append({"deployment_id": str(deploy.id), "change": change})
        return results
