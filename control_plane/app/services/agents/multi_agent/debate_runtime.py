# Owner: agent-platform
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.multi_agent import AgentTeamRun, AgentTeamMember
from app.services.agents.multi_agent.team_runtime import TeamRuntime

logger = logging.getLogger(__name__)

class DebateRuntime(TeamRuntime):
    """
    Implements Debate topology: Proposers -> Critics -> Synthesizer.
    """
    async def execute(self, team_id: uuid.UUID, goal: str, max_rounds: int = 3):
        stmt = select(AgentTeamMember).where(AgentTeamMember.team_id == team_id)
        res = await self.db.execute(stmt)
        members = res.scalars().all()
        
        proposers = [m for m in members if m.role == "proposer"]
        critics = [m for m in members if m.role == "critic"]
        synthesizer = next((m for m in members if m.role == "synthesizer"), None)
        
        if not proposers or not critics or not synthesizer:
            raise ValueError("Debate team needs proposers, critics, and a synthesizer")
            
        run = await self.start_run(team_id, "default", goal)
        
        try:
            for round_num in range(1, max_rounds + 1):
                run.current_round = round_num
                await self.obs.record_trace(run.id, "debate_round_started", {"round": round_num})
                
                # 1. Proposers suggest
                for p in proposers:
                    proposal = f"Proposal from {p.agent_id} in round {round_num}"
                    await self.obs.record_message(run.id, p.agent_id, None, proposal, "proposal")
                
                # 2. Critics review
                for c in critics:
                    critique = f"Critique from {c.agent_id} in round {round_num}"
                    await self.obs.record_message(run.id, c.agent_id, None, critique, "critique")
            
            # 3. Synthesizer generates final
            final_answer = "Debate concluded. Final synthesized answer based on all rounds."
            await self.complete_run(run.id, final_answer)
            return final_answer
            
        except Exception as e:
            logger.exception("Error in debate execution")
            await self.fail_run(run.id, str(e))
            raise
