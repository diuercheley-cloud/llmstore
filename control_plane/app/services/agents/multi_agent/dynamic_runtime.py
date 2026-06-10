# Owner: agent-platform
import asyncio
import logging
import uuid
from typing import Any

from app.models.agents.multi_agent import AgentTeamDelegation
from app.services.agents.multi_agent.loop_guard import LoopGuard
from app.services.agents.multi_agent.team_runtime import TeamRuntime

logger = logging.getLogger(__name__)


class DynamicRoutingRuntime(TeamRuntime):
    """
    Capability-aware team execution with fallback routing and bounded recovery.
    """

    async def execute(self, team_id: uuid.UUID, goal: str, work_items: list[dict[str, Any]] | None = None):
        team = await self.get_team(team_id)
        members = await self.get_members(team_id)
        run = await self.start_run(team_id, team.tenant_id, goal)
        workspace = self.get_workspace(team.tenant_id)
        loop_guard = LoopGuard(self.db)

        candidates = [member for member in members if member.role in {"specialist", "worker", "router", "manager"}]
        if not candidates:
            raise ValueError("Dynamic team requires at least one executable member")

        work_items = work_items or team.config.get("work_items") or [
            {"task_id": "task-1", "description": goal, "required_capability": None}
        ]

        results: list[str] = []
        try:
            from app.services.agents import agent_runtime

            for index, item in enumerate(work_items, start=1):
                selected = self._select_member(candidates, item)
                if selected is None:
                    raise ValueError(f"No eligible member found for work item '{item.get('task_id', index)}'")

                if await loop_guard.detect_cycle(run.id, selected.agent_id, selected.agent_id):
                    raise ValueError("Self-loop detected in dynamic routing")

                delegation = AgentTeamDelegation(
                    run_id=run.id,
                    parent_agent_id=selected.agent_id,
                    child_agent_id=selected.agent_id,
                    task_description=item.get("description", goal),
                    status="active",
                )
                self.db.add(delegation)
                await self.record_handoff(
                    run.id,
                    None,
                    selected.agent_id,
                    item.get("description", goal),
                    "instruction",
                )

                try:
                    if selected.metadata_json.get("simulate_failure"):
                        raise RuntimeError(f"simulated failure for agent {selected.agent_id}")
                    sub_run = await agent_runtime.start_run(
                        db=self.db,
                        agent_id=selected.agent_id,
                        tenant_id=team.tenant_id,
                        input_text=item.get("description", goal),
                        parent_run_id=run.id,
                        correlation_id=str(run.id),
                    )
                    while sub_run.status not in ("completed", "failed", "cancelled"):
                        await asyncio.sleep(1)
                        await self.db.refresh(sub_run)

                    if sub_run.status != "completed":
                        raise RuntimeError(f"Agent {selected.agent_id} failed with status {sub_run.status}")

                    result_text = f"Result from {selected.agent_id} (run {sub_run.id}): Task completed."
                    delegation.status = "completed"
                    chosen_agent = selected
                except RuntimeError:
                    delegation.status = "failed"
                    fallback = self._select_member(
                        [member for member in candidates if member.agent_id != selected.agent_id],
                        item,
                    )
                    if fallback is None:
                        raise
                    
                    sub_run_fb = await agent_runtime.start_run(
                        db=self.db,
                        agent_id=fallback.agent_id,
                        tenant_id=team.tenant_id,
                        input_text=f"RECOVERY: {item.get('description', goal)}",
                        parent_run_id=run.id,
                        correlation_id=str(run.id),
                    )
                    while sub_run_fb.status not in ("completed", "failed", "cancelled"):
                        await asyncio.sleep(1)
                        await self.db.refresh(sub_run_fb)

                    result_text = f"Recovery result from {fallback.agent_id} (run {sub_run_fb.id}): Task completed after fallback."
                    chosen_agent = fallback

                await workspace.put(
                    run.id,
                    f"dynamic:{item.get('task_id', index)}",
                    {
                        "task": item,
                        "agent_id": str(chosen_agent.agent_id),
                        "result": result_text,
                    },
                )
                await self.obs.record_message(run.id, chosen_agent.agent_id, None, result_text, "result")
                results.append(result_text)

            summary = f"Dynamic team completed '{goal}' with {len(work_items)} routed work items. " + " ".join(results)
            await workspace.put(
                run.id,
                "dynamic:summary",
                {"goal": goal, "work_item_count": len(work_items), "results": results, "summary": summary},
            )
            await self.complete_run(run.id, summary)
            return summary
        except Exception as exc:
            logger.exception("Error in dynamic multi-agent execution")
            await self.fail_run(run.id, str(exc))
            raise

    def _select_member(self, members: list[Any], work_item: dict[str, Any]):
        required_capability = work_item.get("required_capability")

        def score(member: Any) -> tuple[int, int]:
            capabilities = member.metadata_json.get("capabilities", [])
            priority = int(member.metadata_json.get("priority", 0))
            capability_match = 1 if required_capability in capabilities or required_capability is None else 0
            return (capability_match, priority)

        eligible = []
        for member in members:
            capabilities = member.metadata_json.get("capabilities", [])
            if required_capability is None or required_capability in capabilities:
                eligible.append(member)
        pool = eligible or members
        return max(pool, key=score, default=None)

    def _execute_work_item(
        self,
        member: Any,
        work_item: dict[str, Any],
        goal: str,
        recovered_from: uuid.UUID | None = None,
    ) -> str:
        if member.metadata_json.get("simulate_failure"):
            raise RuntimeError(f"simulated failure for agent {member.agent_id}")
        recovery_note = f" after recovery from {recovered_from}" if recovered_from else ""
        capability = work_item.get("required_capability") or "general"
        return (
            f"Agent {member.agent_id} handled task '{work_item.get('task_id', 'unknown')}' "
            f"with capability '{capability}' for goal '{goal}'{recovery_note}."
        )
