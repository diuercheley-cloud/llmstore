# Owner: agent-platform
import uuid
import logging
from app.models.multi_agent import AgentTeamDelegation
from app.services.agents.multi_agent.team_runtime import TeamRuntime

logger = logging.getLogger(__name__)

class HierarchicalRuntime(TeamRuntime):
    """
    Implements Hierarchical topology: Manager -> Specialists.
    """
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
            
            results = []
            for index, spec in enumerate(specialists, start=1):
                assignment = spec.metadata_json.get("task_description") or f"Analyze subproblem for goal: {goal}"
                specialist_result = (
                    f"Specialist {index} ({spec.agent_id}) analyzed '{assignment}' "
                    f"for goal '{goal}' and produced a bounded recommendation."
                )
                await workspace.put(
                    run.id,
                    f"specialist:{spec.agent_id}",
                    {
                        "agent_id": str(spec.agent_id),
                        "role": spec.role,
                        "task_description": assignment,
                        "result": specialist_result,
                    },
                )
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
                    },
                    agent_id=spec.agent_id,
                )
                delegations_by_child[spec.agent_id].status = "completed"
                results.append(specialist_result)
            
            final_result = f"Aggregated analysis for '{goal}': {' '.join(results)}"
            await workspace.put(
                run.id,
                "manager:summary",
                {
                    "manager_id": str(manager.agent_id),
                    "goal": goal,
                    "summary": final_result,
                    "delegation_count": len(specialists),
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
