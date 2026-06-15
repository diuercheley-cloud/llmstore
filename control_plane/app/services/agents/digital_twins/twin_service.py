# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.models.agents.digital_twin import DigitalTwinCommand
from sqlalchemy.ext.asyncio import AsyncSession

from .safety_interlock import SafetyInterlock
from .twin_connector import TwinConnector

logger = logging.getLogger(__name__)


class DigitalTwinService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.interlock = SafetyInterlock(db)
        self.connector = TwinConnector(db)

    async def read_twin(self, twin_id: uuid.UUID) -> dict[str, Any]:
        if not self.settings.agent_digital_twins_enabled:
            raise PermissionError("Digital Twin subsystem is disabled.")
        return await self.connector.read(twin_id)

    async def send_command(
        self,
        twin_id: uuid.UUID,
        command: str,
        params: dict[str, Any],
        run_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Sends a command to a digital twin with full policy and safety enforcement.
        """
        if not self.settings.agent_digital_twins_enabled:
            raise PermissionError("Digital Twin subsystem is disabled.")

        if not self.settings.agent_physical_actuation_enabled:
            raise PermissionError("Physical actuation is globally disabled.")

        # 1. Register intent
        record = DigitalTwinCommand(
            twin_id=twin_id, run_id=run_id, command=command, parameters=params, status="authorizing"
        )
        self.db.add(record)
        await self.db.flush()

        # 2. Safety Interlock
        is_safe, reason = await self.interlock.check_command(twin_id, command, params)
        if not is_safe:
            record.status = "rejected"
            await self.db.commit()
            return {"status": "blocked_by_safety", "reason": reason}

        # 3. Policy & Approval (Mocked)
        # In real implementation: check RBAC, check Human Approval status
        needs_approval = True  # Hardcoded for prototype security posture
        if needs_approval and not params.get("human_signature"):
            record.status = "pending"
            await self.db.commit()
            return {"status": "pending_approval", "command_id": str(record.id)}

        # 4. Execute
        record.status = "executing"
        await self.db.flush()

        try:
            res = await self.connector.execute_command(twin_id, command, params)
            record.status = "completed"
            record.actuation_receipt = res
            await self.db.commit()
            return {"status": "success", "receipt": res}
        except Exception:
            record.status = "failed"
            await self.db.commit()
            raise
