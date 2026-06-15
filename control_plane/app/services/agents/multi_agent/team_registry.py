# Owner: Platform Operations
import logging
import uuid
from typing import Any

from app.models.agents.multi_agent import AgentTeam, AgentTeamMember
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TeamRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_team(
        self,
        tenant_id: str,
        name: str,
        topology: str,
        owner_user_id: str,
        description: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> AgentTeam:
        team = AgentTeam(
            tenant_id=tenant_id,
            name=name,
            topology=topology,
            owner_user_id=owner_user_id,
            description=description,
            config=config or {},
            status="active",
        )
        self.db.add(team)
        await self.db.flush()
        return team

    async def add_member(
        self,
        team_id: uuid.UUID,
        agent_id: uuid.UUID,
        role: str,
        metadata: dict[str, Any] | None = None,
    ) -> AgentTeamMember:
        member = AgentTeamMember(
            team_id=team_id, agent_id=agent_id, role=role, metadata_json=metadata or {}
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_team(self, team_id: uuid.UUID) -> AgentTeam | None:
        stmt = select(AgentTeam).where(AgentTeam.id == team_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_teams(self, tenant_id: str) -> list[AgentTeam]:
        stmt = select(AgentTeam).where(AgentTeam.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalars().all()
