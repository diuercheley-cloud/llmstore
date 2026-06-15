# Owner: agent-platform
import logging
import uuid

from app.core.time import utc_now
from app.models.agents.multi_agent import AgentTeam, AgentTeamMember, AgentTeamRun
from app.services.agents.multi_agent.shared_workspace import SharedWorkspace
from app.services.agents.multi_agent.team_observability import TeamObservability
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TeamRuntime:
    """
    Base runtime for multi-agent team execution.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.obs = TeamObservability(db)

    async def get_team(self, team_id: uuid.UUID) -> AgentTeam:
        stmt = select(AgentTeam).where(AgentTeam.id == team_id)
        res = await self.db.execute(stmt)
        team = res.scalar_one_or_none()
        if not team:
            raise ValueError("Team not found")
        return team

    async def get_members(self, team_id: uuid.UUID) -> list[AgentTeamMember]:
        stmt = select(AgentTeamMember).where(AgentTeamMember.team_id == team_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def start_run(self, team_id: uuid.UUID, tenant_id: str, goal: str) -> AgentTeamRun:
        run = AgentTeamRun(team_id=team_id, tenant_id=tenant_id, input_goal=goal, status="running")
        self.db.add(run)
        await self.db.flush()

        await self.obs.record_trace(run.id, "run_started", {"goal": goal})
        return run

    def get_workspace(self, tenant_id: str) -> SharedWorkspace:
        return SharedWorkspace(self.db, tenant_id)

    async def record_handoff(
        self,
        run_id: uuid.UUID,
        sender_id: uuid.UUID | None,
        recipient_id: uuid.UUID | None,
        task_description: str,
        message_type: str = "instruction",
    ) -> None:
        await self.obs.record_message(
            run_id,
            sender_id,
            recipient_id,
            task_description,
            message_type,
        )
        await self.obs.record_trace(
            run_id,
            "agent_handoff",
            {
                "sender_id": str(sender_id) if sender_id else None,
                "recipient_id": str(recipient_id) if recipient_id else None,
                "task_description": task_description,
            },
            agent_id=sender_id,
        )

    async def complete_run(self, run_id: uuid.UUID, result: str):
        stmt = select(AgentTeamRun).where(AgentTeamRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one()

        run.status = "completed"
        run.output_result = result
        run.completed_at = utc_now()

        await self.obs.record_trace(run.id, "run_completed", {"result_summary": result[:100]})
        await self.db.commit()

    async def fail_run(self, run_id: uuid.UUID, reason: str):
        stmt = select(AgentTeamRun).where(AgentTeamRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one()

        run.status = "failed"
        await self.obs.record_trace(run.id, "run_failed", {"reason": reason})
        await self.db.commit()
