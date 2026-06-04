# Owner: agent-platform
import logging
import uuid

from app.services.agents.multi_agent.arbitration_engine import ArbitrationEngine
from app.services.agents.multi_agent.governance_policy import MultiAgentPolicyService
from app.services.agents.multi_agent.team_runtime import TeamRuntime

logger = logging.getLogger(__name__)

class DebateRuntime(TeamRuntime):
    """
    Implements Debate topology: Proposers -> Critics -> Synthesizer.
    """
    def __init__(self, db):
        super().__init__(db)
        self.arbitrator = ArbitrationEngine(db)
        self.policy = MultiAgentPolicyService(db)

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
            # Policy check: Shared budget
            if not await self.policy.check_shared_budget(run.id, 0.01): # Initial cost estimate
                 raise ValueError("Shared budget exceeded for debate run")

            from app.services.agents import agent_runtime
            round_summaries = []
            for round_num in range(1, max_rounds + 1):
                run.current_round = round_num
                await self.obs.record_trace(run.id, "debate_round_started", {"round": round_num})
                
                proposals = []
                for p in proposers:
                    sub_run = await agent_runtime.start_run(
                        db=self.db,
                        agent_id=p.agent_id,
                        tenant_id=team.tenant_id,
                        input_text=f"Propose approach for goal: {goal}. Round {round_num}.",
                        parent_run_id=run.id,
                        correlation_id=run.correlation_id
                    )
                    # wait for completion
                    while sub_run.status not in ("completed", "failed", "cancelled"):
                        await asyncio.sleep(1)
                        await self.db.refresh(sub_run)
                    
                    proposal = f"Proposal from {p.agent_id} (run {sub_run.id}): {sub_run.failure_reason if sub_run.status == 'failed' else 'Proposal generated.'}"
                    await self.obs.record_message(run.id, p.agent_id, None, proposal, "proposal")
                    proposals.append({"agent_id": str(p.agent_id), "run_id": str(sub_run.id), "content": proposal})
                
                critiques = []
                for c in critics:
                    sub_run = await agent_runtime.start_run(
                        db=self.db,
                        agent_id=c.agent_id,
                        tenant_id=team.tenant_id,
                        input_text=f"Critique proposals: {proposals}. Goal: {goal}. Round {round_num}.",
                        parent_run_id=run.id,
                        correlation_id=run.correlation_id
                    )
                    while sub_run.status not in ("completed", "failed", "cancelled"):
                        await asyncio.sleep(1)
                        await self.db.refresh(sub_run)

                    critique = f"Critique from {c.agent_id} (run {sub_run.id}): Review completed."
                    await self.obs.record_message(run.id, c.agent_id, None, critique, "critique")
                    critiques.append({"agent_id": str(c.agent_id), "run_id": str(sub_run.id), "content": critique})

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
            
            # Arbitration and Synthesis at the end of rounds
            outputs_for_arbitration = []
            for rs in round_summaries:
                for prop in rs["proposals"]:
                    outputs_for_arbitration.append({
                        "result": prop,
                        "confidence": 0.7 # Base confidence for round proposals
                    })

            arbitration_res = await self.arbitrator.arbitrate(
                outputs_for_arbitration,
                {
                    "goal": goal,
                    "topology": "debate",
                    "rounds_count": max_rounds,
                    "critics": critics,
                    "tenant_id": team.tenant_id
                }
            )
            synthesis = arbitration_res["final_synthesis"]
            
            # Critic Review
            final_answer, safety_score = await self.arbitrator.run_critic_review(synthesis, critics)
            
            await workspace.put(
                run.id,
                "synthesizer:summary",
                {
                    "agent_id": str(synthesizer.agent_id),
                    "goal": goal,
                    "rounds": round_summaries,
                    "final_answer": final_answer,
                    "safety_score": safety_score
                },
            )
            await self.obs.record_message(run.id, synthesizer.agent_id, None, final_answer, "result")
            await self.complete_run(run.id, final_answer)
            return final_answer
            
        except Exception as e:
            logger.exception("Error in debate execution")
            await self.fail_run(run.id, str(e))
            raise
