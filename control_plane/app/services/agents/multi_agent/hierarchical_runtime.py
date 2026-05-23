# Owner: agent-platform
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.multi_agent import AgentTeamRun, AgentTeamMember, AgentTeamDelegation
from app.services.agents.multi_agent.team_runtime import TeamRuntime
from app.services.agents.agent_executor import AgentExecutor

logger = logging.getLogger(__name__)

class HierarchicalRuntime(TeamRuntime):
    """
    Implements Hierarchical topology: Manager -> Specialists.
    """
    async def execute(self, team_id: uuid.UUID, goal: str):
        stmt = select(AgentTeamMember).where(AgentTeamMember.team_id == team_id)
        res = await self.db.execute(stmt)
        members = res.scalars().all()
        
        manager = next((m for m in members if m.role == "manager"), None)
        if not manager:
            raise ValueError("Team must have a manager for hierarchical topology")
            
        run = await self.start_run(team_id, "default", goal) # Tenant hardcoded for proto
        
        try:
            # 1. Manager analyzes goal and creates delegations
            # (Simplified: logic would call AgentExecutor for the manager agent)
            specialists = [m for m in members if m.role == "specialist"]
            
            for spec in specialists:
                delegation = AgentTeamDelegation(
                    run_id=run.id,
                    parent_agent_id=manager.agent_id,
                    child_agent_id=spec.agent_id,
                    task_description=f"Analyze part of: {goal}",
                    status="active"
                )
                self.db.add(delegation)
                await self.obs.record_trace(run.id, "task_delegated", {
                    "parent_id": str(manager.agent_id),
                    "child_id": str(spec.agent_id)
                })
            
            await self.db.flush()
            
            # 2. Specialists execute
            # (Mocked execution)
            results = []
            for spec in specialists:
                results.append(f"Specialist {spec.agent_id} completed task.")
            
            # 3. Manager synthesizes
            final_result = f"Aggregated analysis: {' '.join(results)}"
            
            await self.complete_run(run.id, final_result)
            return final_result
            
        except Exception as e:
            logger.exception("Error in hierarchical execution")
            await self.fail_run(run.id, str(e))
            raise
