# Owner: agent-platform
import uuid
from typing import Any

from app.models.agents.digital_twin import DigitalTwinSafetyEvent
from sqlalchemy.ext.asyncio import AsyncSession


class SafetyInterlock:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_command(
        self, twin_id: uuid.UUID, command: str, params: dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Final safety gate before physical actuation.
        Checks for known dangerous patterns or boundary violations.
        """
        # Hardcoded dangerous patterns for prototype
        dangerous_commands = ["emergency_stop_override", "factory_reset", "set_voltage_high"]

        if command in dangerous_commands:
            event = DigitalTwinSafetyEvent(
                twin_id=twin_id,
                event_type="interlock_trip",
                severity="critical",
                details={
                    "command": command,
                    "reason": "Attempted override of critical safety command.",
                },
            )
            self.db.add(event)
            await self.db.commit()
            return False, "Interlock tripped: dangerous command blocked."

        # Boundary check for generic set commands
        if "value" in params and isinstance(params["value"], (int, float)):
            if params["value"] > 1000:
                return False, "Value exceeds physical safety boundary (1000)."

        return True, "Safe"
