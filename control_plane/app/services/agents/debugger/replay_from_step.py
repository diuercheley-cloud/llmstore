# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.models.agent_debugger import AgentDebugReplay, AgentRunSnapshot
from app.models.agents import AgentRun
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class ReplayFromStep:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def initiate_replay(self, run_id: uuid.UUID, step_number: int) -> Dict[str, Any]:
        """
        Creates a new debug run that starts from the state of a previous run at step N.
        """
        if not self.settings.agent_replay_from_step_enabled:
            raise PermissionError("Replay from step is disabled by feature flag.")

        # 1. Fetch source snapshot
        stmt = select(AgentRunSnapshot).where(
            AgentRunSnapshot.run_id == run_id,
            AgentRunSnapshot.step_number == step_number
        )
        res = await self.db.execute(stmt)
        snapshot = res.scalar_one_or_none()
        if not snapshot:
            raise ValueError(f"Snapshot for run {run_id} at step {step_number} not found.")

        # 2. Fetch original run for metadata
        original_run = await self.db.get(AgentRun, run_id)
        if not original_run:
            raise ValueError("Original run not found")

        # 3. Create a new Replay Run (shallow copy of metadata, different ID)
        replay_run = AgentRun(
            agent_id=original_run.agent_id,
            tenant_id=original_run.tenant_id,
            user_id=original_run.user_id,
            status="queued",
            input_text=f"[DEBUG REPLAY of {run_id} from step {step_number}]"
        )
        self.db.add(replay_run)
        await self.db.flush()

        # 4. Record the Replay relationship
        replay = AgentDebugReplay(
            original_run_id=run_id,
            replay_run_id=replay_run.id,
            source_snapshot_id=snapshot.id,
            step_rewind_to=step_number,
            status="active"
        )
        self.db.add(replay)
        await self.db.commit()

        return {
            "replay_id": str(replay.id),
            "replay_run_id": str(replay_run.id),
            "start_step": step_number,
            "initial_state": snapshot.full_state
        }
