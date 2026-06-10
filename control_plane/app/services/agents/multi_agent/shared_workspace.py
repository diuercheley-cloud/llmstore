# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, Optional

from app.models.agents.multi_agent import AgentSharedWorkspace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class SharedWorkspace:
    """
    Manages shared state for a team run.
    """
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def put(self, run_id: uuid.UUID, key: str, value: Dict[str, Any]):
        stmt = select(AgentSharedWorkspace).where(
            AgentSharedWorkspace.team_run_id == run_id,
            AgentSharedWorkspace.key == key
        )
        res = await self.db.execute(stmt)
        entry = res.scalar_one_or_none()
        
        if entry:
            entry.value = value
        else:
            entry = AgentSharedWorkspace(
                tenant_id=self.tenant_id,
                team_run_id=run_id,
                key=key,
                value=value
            )
            self.db.add(entry)
        
        await self.db.flush()

    async def get(self, run_id: uuid.UUID, key: str) -> Optional[Dict[str, Any]]:
        stmt = select(AgentSharedWorkspace).where(
            AgentSharedWorkspace.team_run_id == run_id,
            AgentSharedWorkspace.key == key
        )
        res = await self.db.execute(stmt)
        entry = res.scalar_one_or_none()
        return entry.value if entry else None
