"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from datetime import timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentSLOWindow, AgentRun, AgentDefinition
from app.core import metrics
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class AgentSLOService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_slo_window(
        self,
        agent_id: uuid.UUID,
        window_type: str = "24h"
    ) -> AgentSLOWindow:
        now = utc_now()
        if window_type == "1h":
            start_time = now - timedelta(hours=1)
        elif window_type == "24h":
            start_time = now - timedelta(days=1)
        elif window_type == "7d":
            start_time = now - timedelta(days=7)
        else:
            window_type = "30d"
            start_time = now - timedelta(days=30)

        # Aggregate run metrics for window
        res_total = await self.db.execute(
            select(func.count(AgentRun.id))
            .where(AgentRun.agent_id == agent_id)
            .where(AgentRun.created_at >= start_time)
        )
        total_runs = res_total.scalar() or 0

        res_success = await self.db.execute(
            select(func.count(AgentRun.id))
            .where(AgentRun.agent_id == agent_id)
            .where(AgentRun.created_at >= start_time)
            .where(AgentRun.status == "completed")
        )
        success_runs = res_success.scalar() or 0
        failed_runs = total_runs - success_runs

        success_rate = success_runs / total_runs if total_runs > 0 else 1.0
        
        # Simple SLO: success rate >= 95%
        slo_breached = success_rate < 0.95

        metrics_json = {
            "success_rate": success_rate,
            "target": 0.95,
            "failed_runs": failed_runs
        }

        window = AgentSLOWindow(
            agent_id=agent_id,
            window_type=window_type,
            start_time=start_time,
            end_time=now,
            total_runs=total_runs,
            success_runs=success_runs,
            failed_runs=failed_runs,
            slo_breached=slo_breached,
            metrics_json=metrics_json,
            created_at=now
        )
        self.db.add(window)
        
        if slo_breached:
            metrics.LLM_AGENT_SLO_BREACHES_TOTAL.labels(
                agent_id=str(agent_id), window_type=window_type
            ).inc()

        await self.db.commit()
        await self.db.refresh(window)
        return window

    async def get_latest_slo(self, agent_id: uuid.UUID) -> List[AgentSLOWindow]:
        res = await self.db.execute(
            select(AgentSLOWindow)
            .where(AgentSLOWindow.agent_id == agent_id)
            .order_by(AgentSLOWindow.created_at.desc())
            .limit(4) # One per type
        )
        return list(res.scalars().all())
