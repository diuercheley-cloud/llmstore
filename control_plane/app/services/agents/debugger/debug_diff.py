# Owner: agent-platform
import uuid
from typing import Any

from app.models.agents.agent_debugger import AgentDebugReplay, AgentRunSnapshot
from app.models.agents.agents import AgentRun
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class DebugDiff:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compare(self, replay_id: uuid.UUID) -> dict[str, Any]:
        """
        Compares the replay execution with the original run.
        """
        replay = await self.db.get(AgentDebugReplay, replay_id)
        if not replay:
            raise ValueError("Replay session not found")

        original_run = await self.db.get(AgentRun, replay.original_run_id)
        replay_run = await self.db.get(AgentRun, replay.replay_run_id)

        # Compare high-level metrics
        diff = {
            "status_changed": original_run.status != replay_run.status,
            "original": {
                "status": original_run.status,
                "steps": await self._count_steps(replay.original_run_id),
            },
            "replay": {
                "status": replay_run.status,
                "steps": await self._count_steps(replay.replay_run_id),
            },
            "divergence": {},
        }

        # Check for state divergence at the last common step
        # (Simplified implementation)

        return diff

    async def _count_steps(self, run_id: uuid.UUID) -> int:
        stmt = select(AgentRunSnapshot).where(AgentRunSnapshot.run_id == run_id)
        res = await self.db.execute(stmt)
        return len(res.scalars().all())
