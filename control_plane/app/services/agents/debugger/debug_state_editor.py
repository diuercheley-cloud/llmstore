# Owner: agent-platform
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_debugger import AgentDebugStateEdit, AgentDebugReplay
from app.core.config import get_settings

class DebugStateEditor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def edit_state(
        self, 
        replay_id: uuid.UUID, 
        field_path: str, 
        new_value: Any, 
        editor_id: str
    ) -> Dict[str, Any]:
        """
        Manually modifies a field in the debug session state before continuing execution.
        """
        if not self.settings.agent_debug_state_editing_enabled:
            raise PermissionError("Debug state editing is disabled by feature flag.")

        replay = await self.db.get(AgentDebugReplay, replay_id)
        if not replay:
            raise ValueError("Replay session not found")
            
        if replay.status != "active":
            raise ValueError("State edits can only be applied to active debug sessions.")

        # Record the edit
        edit = AgentDebugStateEdit(
            replay_id=replay_id,
            field_path=field_path,
            new_value=new_value,
            editor_id=editor_id
        )
        self.db.add(edit)
        await self.db.commit()

        return {"status": "edit_applied", "edit_id": str(edit.id)}
