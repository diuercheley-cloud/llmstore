import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.multi_agent import AgentTeamRun, AgentTeam
from app.services.agents.multi_agent.team_observability import TeamObservability
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class TeamRuntime:
    """
    Base runtime for multi-agent team execution.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.obs = TeamObservability(db)

    async def start_run(self, team_id: uuid.UUID, tenant_id: str, goal: str) -> AgentTeamRun:
        run = AgentTeamRun(
            team_id=team_id,
            tenant_id=tenant_id,
            input_goal=goal,
            status="running"
        )
        self.db.add(run)
        await self.db.flush()
        
        await self.obs.record_trace(run.id, "run_started", {"goal": goal})
        return run

    async def complete_run(self, run_id: uuid.UUID, result: str):
        stmt = select(AgentTeamRun).where(AgentTeamRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one()
        
        run.status = "completed"
        run.output_result = result
        run.completed_at = utc_now()
        
        await self.obs.record_trace(run.id, "run_completed", {"result_summary": result[:100]})
        await self.db.commit()

    async def fail_run(self, run_id: uuid.UUID, reason: str):
        stmt = select(AgentTeamRun).where(AgentTeamRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one()
        
        run.status = "failed"
        await self.obs.record_trace(run.id, "run_failed", {"reason": reason})
        await self.db.commit()
