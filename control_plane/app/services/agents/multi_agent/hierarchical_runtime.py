# Owner: agent-platform
import uuid
import logging
from app.models.multi_agent import AgentTeamDelegation
from app.services.agents.multi_agent.team_runtime import TeamRuntime
from app.services.agents.multi_agent.arbitration_engine import ArbitrationEngine
from app.services.agents.multi_agent.governance_policy import MultiAgentPolicyService

logger = logging.getLogger(__name__)

class HierarchicalRuntime(TeamRuntime):
    """
    Implements Hierarchical topology: Manager -> Specialists.
    """
    def __init__(self, db):
        super().__init__(db)
        self.arbitrator = ArbitrationEngine(db)
        self.policy = MultiAgentPolicyService(db)

    async def execute(self, team_id: uuid.UUID, goal: str):
        team = await self.get_team(team_id)
        members = await self.get_members(team_id)
        
        manager = next((m for m in members if m.role == "manager"), None)
        if not manager:
            raise ValueError("Team must have a manager for hierarchical topology")
            
        run = await self.start_run(team_id, team.tenant_id, goal)
        workspace = self.get_workspace(team.tenant_id)
        
        try:
            specialists = [m for m in members if m.role == "specialist"]
            if not specialists:
                raise ValueError("Hierarchical team requires at least one specialist")
            delegations_by_child = {}

            await self.record_handoff(
                run.id,
                manager.agent_id,
                None,
                f"Manager accepted goal: {goal}",
            )
            
            for spec in specialists:
                # Enforcement: Max Depth/Fanout
                allowed, reason = await self.policy.validate_delegation(run.id, manager.agent_id, spec.agent_id)
                if not allowed:
                    logger.error(f"Delegation blocked by policy: {reason}")
                    raise ValueError(f"Policy violation: {reason}")

                task_description = spec.metadata_json.get("task_description") or f"Analyze subproblem for goal: {goal}"
                delegation = AgentTeamDelegation(
                    run_id=run.id,
                    parent_agent_id=manager.agent_id,
                    child_agent_id=spec.agent_id,
                    task_description=task_description,
                    status="active"
                )
                self.db.add(delegation)
                delegations_by_child[spec.agent_id] = delegation
                await self.record_handoff(
                    run.id,
                    manager.agent_id,
                    spec.agent_id,
                    task_description,
                )
                await self.obs.record_trace(run.id, "task_delegated", {
                    "parent_id": str(manager.agent_id),
                    "child_id": str(spec.agent_id),
                    "task_description": task_description,
                })
            
            await self.db.flush()
            
            specialist_outputs = []
            for index, spec in enumerate(specialists, start=1):
                assignment = spec.metadata_json.get("task_description") or f"Analyze subproblem for goal: {goal}"
                # In real scenario, we would call the agent here
                # Mocking specialist cost and failure tracking
                spec_cost = 0.005 # Mock cost per specialist call
                
                specialist_result = (
                    f"Specialist {index} ({spec.agent_id}) analyzed '{assignment}' "
                    f"for goal '{goal}' and produced a bounded recommendation."
                )
                
                output_payload = {
                    "agent_id": str(spec.agent_id),
                    "role": spec.role,
                    "task_description": assignment,
                    "result": specialist_result,
                    "confidence": 0.85 + (index * 0.02), # Mock varying confidence
                    "cost_brl": spec_cost
                }
                specialist_outputs.append(output_payload)

                await workspace.put(run.id, f"specialist:{spec.agent_id}", output_payload)
                await self.obs.record_message(
                    run.id,
                    spec.agent_id,
                    manager.agent_id,
                    specialist_result,
                    "result",
                )
                await self.obs.record_trace(
                    run.id,
                    "specialist_completed",
                    {
                        "agent_id": str(spec.agent_id),
                        "task_description": assignment,
                        "cost_brl": spec_cost
                    },
                    agent_id=spec.agent_id,
                )
                delegations_by_child[spec.agent_id].status = "completed"
            
            # Arbitration and Synthesis
            arbitration_res = await self.arbitrator.arbitrate(
                specialist_outputs,
                {
                    "goal": goal,
                    "topology": "hierarchical",
                    "tenant_id": team.tenant_id
                }
            )
            final_result = arbitration_res["final_synthesis"]
            
            await workspace.put(
                run.id,
                "manager:summary",
                {
                    "manager_id": str(manager.agent_id),
                    "goal": goal,
                    "summary": final_result,
                    "delegation_count": len(specialists),
                    "consensus": arbitration_res["consensus"],
                    "confidence_score": arbitration_res["confidence_score"]
                },
            )
            await self.obs.record_message(
                run.id,
                manager.agent_id,
                None,
                final_result,
                "result",
            )
            
            await self.complete_run(run.id, final_result)
            return final_result
            
        except Exception as e:
            logger.exception("Error in hierarchical execution")
            await self.fail_run(run.id, str(e))
            raise
