"""
Owner: agent-platform
Status: beta
"""
import logging
import uuid
from datetime import timedelta
from typing import List

from app.core import metrics
from app.core.time import utc_now
from app.models.agents import AgentDefinition, AgentRun, AgentSLOWindow
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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

        from app.services.agents.agent_budget import AgentBudgetService
        budget_svc = AgentBudgetService()
        agent_def = await self.db.get(AgentDefinition, agent_id)
        cls_cfg = budget_svc.get_class_config(agent_def.agent_class if agent_def else None)
        
        target_success_rate = cls_cfg.get("run_success_rate_target", 0.95)
        
        success_rate = success_runs / total_runs if total_runs > 0 else 1.0
        
        # Class-based SLO
        slo_breached = success_rate < target_success_rate

        metrics_json = {
            "success_rate": success_rate,
            "target": target_success_rate,
            "failed_runs": failed_runs,
            "agent_class": agent_def.agent_class if agent_def else "unknown"
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
            
            # Create incident
            from app.services.agents.agent_incidents import AgentIncidentService
            inc_svc = AgentIncidentService(self.db)
            await inc_svc.detect_and_create_incident(
                tenant_id=agent_def.tenant_id if agent_def else "unknown",
                agent_id=agent_id,
                run_id=None,
                incident_type="slo_breach",
                title=f"SLO Breach for agent class: {agent_def.agent_class if agent_def else 'unknown'}",
                severity="high",
                details=metrics_json
            )

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
