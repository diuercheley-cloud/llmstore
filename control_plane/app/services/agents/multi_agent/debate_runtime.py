# Owner: agent-platform
import uuid
import logging
from typing import List, Dict, Any, Optional
from app.services.agents.multi_agent.team_runtime import TeamRuntime

logger = logging.getLogger(__name__)

class DebateRuntime(TeamRuntime):
    """
    Implements Debate topology: Proposers -> Critics -> Synthesizer.
    """
    async def execute(self, team_id: uuid.UUID, goal: str, max_rounds: int = 3):
        team = await self.get_team(team_id)
        members = await self.get_members(team_id)
        
        proposers = [m for m in members if m.role == "proposer"]
        critics = [m for m in members if m.role == "critic"]
        synthesizer = next((m for m in members if m.role == "synthesizer"), None)
        
        if not proposers or not critics or not synthesizer:
            raise ValueError("Debate team needs proposers, critics, and a synthesizer")
            
        run = await self.start_run(team_id, team.tenant_id, goal)
        workspace = self.get_workspace(team.tenant_id)
        
        try:
            round_summaries = []
            for round_num in range(1, max_rounds + 1):
                run.current_round = round_num
                await self.obs.record_trace(run.id, "debate_round_started", {"round": round_num})
                
                proposals = []
                for p in proposers:
                    proposal = (
                        f"Proposal from {p.agent_id} in round {round_num}: "
                        f"approach {round_num} for goal '{goal}'."
                    )
                    await self.obs.record_message(run.id, p.agent_id, None, proposal, "proposal")
                    proposals.append(proposal)
                
                critiques = []
                for c in critics:
                    critique = (
                        f"Critique from {c.agent_id} in round {round_num}: "
                        f"risk review for proposals on '{goal}'."
                    )
                    await self.obs.record_message(run.id, c.agent_id, None, critique, "critique")
                    critiques.append(critique)

                round_summary = {
                    "round": round_num,
                    "proposals": proposals,
                    "critiques": critiques,
                }
                round_summaries.append(round_summary)
                await workspace.put(run.id, f"round:{round_num}", round_summary)
                await self.obs.record_trace(
                    run.id,
                    "debate_round_completed",
                    {
                        "round": round_num,
                        "proposal_count": len(proposals),
                        "critique_count": len(critiques),
                    },
                )
            
            final_answer = (
                f"Debate concluded for '{goal}'. "
                f"Final synthesized answer based on {max_rounds} rounds, "
                f"{len(proposers)} proposers and {len(critics)} critics."
            )
            await workspace.put(
                run.id,
                "synthesizer:summary",
                {
                    "agent_id": str(synthesizer.agent_id),
                    "goal": goal,
                    "rounds": round_summaries,
                    "final_answer": final_answer,
                },
            )
            await self.obs.record_message(run.id, synthesizer.agent_id, None, final_answer, "result")
            await self.complete_run(run.id, final_answer)
            return final_answer
            
        except Exception as e:
            logger.exception("Error in debate execution")
            await self.fail_run(run.id, str(e))
            raise
