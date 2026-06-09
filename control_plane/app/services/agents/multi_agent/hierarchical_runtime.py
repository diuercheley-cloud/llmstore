# Owner: agent-platform
import asyncio
import logging
import uuid

from app.models.multi_agent import AgentTeamDelegation
from app.services.agents.multi_agent.arbitration_engine import ArbitrationEngine
from app.services.agents.multi_agent.governance_policy import MultiAgentPolicyService
from app.services.agents.multi_agent.team_runtime import TeamRuntime

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
            from app.services.agents import agent_runtime
            
            for index, spec in enumerate(specialists, start=1):
                assignment = spec.metadata_json.get("task_description") or f"Analyze subproblem for goal: {goal}"
                
                # REAL DELEGATION: Start real sub-run
                sub_run = await agent_runtime.start_run(
                    db=self.db,
                    agent_id=spec.agent_id,
                    tenant_id=team.tenant_id,
                    input_text=assignment,
                    parent_run_id=run.id,
                    correlation_id=str(run.id),
                )
                
                # Wait for sub-run to complete (Simplified: poll or wait if sync)
                # In a real async system, we'd use a workflow or signals.
                # For this implementation, we wait if it's sync, or poll if async.
                max_retries = 60
                while sub_run.status not in ("completed", "failed", "cancelled") and max_retries > 0:
                    await asyncio.sleep(2)
                    await self.db.refresh(sub_run)
                    max_retries -= 1

                if sub_run.status != "completed":
                    logger.error(f"Specialist {spec.agent_id} failed with status {sub_run.status}")
                    specialist_result = f"Error: Specialist failed to complete task. Status: {sub_run.status}"
                else:
                    # Fetch real output hash and result
                    # Simplification: we'd ideally fetch the final_response from AgentRun
                    specialist_result = (
                        sub_run.failure_reason
                        if sub_run.status == "failed"
                        else f"Success: {assignment} completed by {spec.agent_id}"
                    )

                output_payload = {
                    "agent_id": str(spec.agent_id),
                    "sub_run_id": str(sub_run.id),
                    "role": spec.role,
                    "task_description": assignment,
                    "result": specialist_result,
                    "confidence": 0.9, # Real confidence would come from evaluation or model output
                    "cost_brl": sub_run.estimated_cost_brl
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
                        "sub_run_id": str(sub_run.id),
                        "task_description": assignment,
                        "cost_brl": sub_run.estimated_cost_brl
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
