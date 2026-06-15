# Owner: agent-platform
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .debug_diff import DebugDiff
from .debug_state_editor import DebugStateEditor
from .replay_from_step import ReplayFromStep
from .run_snapshot_store import RunSnapshotStore


class TimeTravelDebugger:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.store = RunSnapshotStore(db)
        self.replay = ReplayFromStep(db)
        self.editor = DebugStateEditor(db)
        self.diff = DebugDiff(db)

    async def get_run_snapshots(self, run_id: uuid.UUID) -> list[dict[str, Any]]:
        snapshots = await self.store.get_snapshots(run_id)
        return [
            {
                "id": str(s.id),
                "step_number": s.step_number,
                "state_hash": s.state_hash,
                "created_at": s.created_at.isoformat(),
            }
            for s in snapshots
        ]

    async def start_replay(self, run_id: uuid.UUID, step_number: int) -> dict[str, Any]:
        return await self.replay.initiate_replay(run_id, step_number)

    async def apply_edit(
        self, replay_id: uuid.UUID, field: str, value: Any, editor: str
    ) -> dict[str, Any]:
        return await self.editor.edit_state(replay_id, field, value, editor)

    async def get_comparison(self, replay_id: uuid.UUID) -> dict[str, Any]:
        return await self.diff.compare(replay_id)
