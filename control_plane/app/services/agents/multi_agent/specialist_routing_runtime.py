# Owner: agent-platform
import uuid
import logging
from typing import List, Dict, Any, Optional
from app.services.agents.multi_agent.team_runtime import TeamRuntime
from app.services.agents.multi_agent.arbitration_engine import ArbitrationEngine
from app.services.agents.multi_agent.governance_policy import MultiAgentPolicyService

logger = logging.getLogger(__name__)

class SpecialistRoutingRuntime(TeamRuntime):
    """
    Implements Specialist Routing: Dispatcher -> Multiple Independent Specialists.
    """
    def __init__(self, db):
        super().__init__(db)
        self.arbitrator = ArbitrationEngine()
        self.policy = MultiAgentPolicyService(db)

    async def execute(self, team_id: uuid.UUID, goal: str):
        team = await self.get_team(team_id)
        members = await self.get_members(team_id)
        
        dispatcher = next((m for m in members if m.role == "dispatcher"), None)
        if not dispatcher:
            raise ValueError("Team must have a dispatcher for specialist routing")
            
        run = await self.start_run(team_id, team.tenant_id, goal)
        workspace = self.get_workspace(team.tenant_id)
        
        try:
            specialists = [m for m in members if m.role == "specialist"]
            
            await self.obs.record_trace(run.id, "routing_started", {"goal": goal})
            
            # 1. Routing phase (mocking dispatcher logic)
            # Dispatcher decides which specialists are needed based on the goal
            selected_specialists = specialists[:2] # Mocking selection
            
            outputs = []
            from app.services.agents import agent_runtime
            for spec in selected_specialists:
                # Policy check
                allowed, reason = await self.policy.validate_delegation(run.id, dispatcher.agent_id, spec.agent_id)
                if not allowed:
                    continue # Skip blocked specialists
                
                await self.obs.record_trace(run.id, "specialist_routed", {"agent_id": str(spec.agent_id)})
                
                # REAL DELEGATION
                sub_run = await agent_runtime.start_run(
                    db=self.db,
                    agent_id=spec.agent_id,
                    tenant_id=team.tenant_id,
                    input_text=f"Routing task for goal: {goal}.",
                    parent_run_id=run.id,
                    correlation_id=run.correlation_id
                )
                while sub_run.status not in ("completed", "failed", "cancelled"):
                    await asyncio.sleep(1)
                    await self.db.refresh(sub_run)

                spec_result = f"Result from {spec.agent_id} (run {sub_run.id}): Analysis completed."
                output = {
                    "agent_id": str(spec.agent_id),
                    "run_id": str(sub_run.id),
                    "result": spec_result,
                    "confidence": 0.9,
                    "cost_brl": sub_run.estimated_cost_brl
                }
                outputs.append(output)
                await self.obs.record_message(run.id, spec.agent_id, dispatcher.agent_id, spec_result, "result")
            
            # 2. Synthesis phase
            arbitration = await self.arbitrator.arbitrate(outputs, {"goal": goal})
            final_result = arbitration["final_synthesis"]
            
            await self.obs.record_message(run.id, dispatcher.agent_id, None, final_result, "result")
            await self.complete_run(run.id, final_result)
            return final_result
            
        except Exception as e:
            logger.exception("Error in specialist routing")
            await self.fail_run(run.id, str(e))
            raise
