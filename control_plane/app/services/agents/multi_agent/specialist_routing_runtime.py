import asyncio
import logging
import uuid
from typing import Dict, List

from app.models.multi_agent import AgentTeam, AgentTeamMember
from app.services.agents.multi_agent.arbitration_engine import ArbitrationEngine
from app.services.agents.multi_agent.delegation_policy import DelegationPolicy
from app.services.agents.multi_agent.governance_policy import MultiAgentPolicyService
from app.services.agents.multi_agent.team_runtime import TeamRuntime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SpecialistRoutingRuntime(TeamRuntime):
    """
    Implements the dispatcher-specialist pattern:
      Dispatcher agent routes incoming tasks to the right specialist agents.
      Specialists process in parallel; results are synthesized by an arbitrator.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db
        self.arbitrator = ArbitrationEngine()
        self.policy = MultiAgentPolicyService(db)
        self.delegation = DelegationPolicy(db)
        self._agent_runtime = None

    @property
    def agent_runtime(self):
        if self._agent_runtime is None:
            from app.services.agents import agent_runtime as ar
            self._agent_runtime = ar
        return self._agent_runtime

    async def execute(self, team_id: uuid.UUID, goal: str) -> str:
        team = await self.get_team(team_id)
        members = await self.get_members(team_id)

        dispatcher = next((m for m in members if m.role == "dispatcher"), None)
        if not dispatcher:
            raise ValueError("Team must have a dispatcher for specialist routing")

        specialists = [m for m in members if m.role == "specialist"]
        if not specialists:
            raise ValueError("Team must have at least one specialist")

        run = await self.start_run(team_id, team.tenant_id, goal)

        try:
            logger.info(
                "SpecialistRouting: team=%s goal=%s dispatcher=%s specialists=%d",
                team_id, goal[:80], dispatcher.agent_id, len(specialists),
            )

            selected = await self._select_specialists(dispatcher, specialists, goal)
            if not selected:
                return await self._fallback(dispatcher, goal, run.id)

            outputs = await self._delegate_to_specialists(
                selected, goal, team.tenant_id, run.id,
            )

            synthesis = await self.arbitrator.arbitrate(
                outputs, {"goal": goal, "team_id": str(team_id)}
            )
            final_result = synthesis.get("final_synthesis", str(outputs))

            await self.complete_run(run.id, final_result)
            return final_result

        except Exception as e:
            logger.exception("SpecialistRouting failed")
            await self.fail_run(run.id, str(e))
            raise

    async def _select_specialists(
        self,
        dispatcher: AgentTeamMember,
        specialists: List[AgentTeamMember],
        goal: str,
    ) -> List[AgentTeamMember]:
        selected = []
        for spec in specialists:
            allowed = await self.delegation.can_delegate(
                dispatcher.agent_id, spec.agent_id, "specialist_task"
            )
            if allowed:
                selected.append(spec)
        return selected or specialists[:2]

    async def _delegate_to_specialists(
        self,
        specialists: List[AgentTeamMember],
        goal: str,
        tenant_id: str,
        parent_run_id: uuid.UUID,
    ) -> List[Dict]:
        async def _run_specialist(spec: AgentTeamMember) -> Dict:
            try:
                allowed, reason = await self.policy.validate_delegation(
                    parent_run_id, specialists[0].agent_id, spec.agent_id
                )
                if not allowed:
                    return {
                        "agent_id": str(spec.agent_id),
                        "result": f"Blocked by policy: {reason}",
                        "confidence": 0.0,
                        "error": reason,
                    }

                sub_run = await self.agent_runtime.start_run(
                    db=self.db,
                    agent_id=spec.agent_id,
                    tenant_id=tenant_id,
                    input_text=f"Specialist task for goal: {goal}",
                    parent_run_id=parent_run_id,
                )

                while sub_run.status not in ("completed", "failed", "cancelled"):
                    await asyncio.sleep(0.5)
                    await self.db.refresh(sub_run)

                return {
                    "agent_id": str(spec.agent_id),
                    "run_id": str(sub_run.id),
                    "result": sub_run.result or f"Analysis from {spec.agent_id}",
                    "confidence": 0.85,
                    "cost_brl": getattr(sub_run, "estimated_cost_brl", 0.0),
                    "status": sub_run.status,
                }
            except Exception as e:
                logger.error("Specialist %s failed: %s", spec.agent_id, e)
                return {
                    "agent_id": str(spec.agent_id),
                    "result": str(e),
                    "confidence": 0.0,
                    "error": str(e),
                }

        tasks = [_run_specialist(spec) for spec in specialists]
        return await asyncio.gather(*tasks)

    async def _fallback(
        self, dispatcher: AgentTeamMember, goal: str, run_id: uuid.UUID
    ) -> str:
        fallback = await self.agent_runtime.start_run(
            db=self.db,
            agent_id=dispatcher.agent_id,
            tenant_id="system",
            input_text=f"Direct dispatch for: {goal}",
            parent_run_id=run_id,
        )
        while fallback.status not in ("completed", "failed", "cancelled"):
            await asyncio.sleep(0.5)
            await self.db.refresh(fallback)
        return fallback.result or "Fallback completed"
