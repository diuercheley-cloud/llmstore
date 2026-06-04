# Owner: agent-platform
import uuid

from app.models.agent_canary import AgentCanaryComparison, AgentShadowRun
from app.models.agents import AgentRun
from sqlalchemy.ext.asyncio import AsyncSession


class CanaryComparator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compare_runs(self, shadow_run_record_id: uuid.UUID) -> AgentCanaryComparison:
        """
        Compares the results of a primary run and its shadow counterpart.
        """
        record = await self.db.get(AgentShadowRun, shadow_run_record_id)
        if not record:
            raise ValueError("Shadow run record not found")

        primary = await self.db.get(AgentRun, record.primary_run_id)
        shadow = await self.db.get(AgentRun, record.shadow_run_id)
        
        # Mock comparison logic
        metrics = {
            "success_match": primary.status == shadow.status,
            "latency_diff_ms": 100, # Placeholder
            "cost_diff_brl": 0.05, # Placeholder
            "tool_divergence": False
        }
        
        findings = []
        if primary.status != shadow.status:
            findings.append(f"Status divergence: Primary={primary.status}, Shadow={shadow.status}")
            
        comparison = AgentCanaryComparison(
            shadow_run_id=shadow_run_record_id,
            metrics=metrics,
            findings=findings,
            is_regression=not metrics["success_match"]
        )
        self.db.add(comparison)
        await self.db.commit()
        await self.db.refresh(comparison)
        return comparison
