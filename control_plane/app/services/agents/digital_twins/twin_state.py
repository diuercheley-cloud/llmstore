# Owner: agent-platform
import uuid
from typing import Any, Dict, Optional

from app.models.digital_twin import DigitalTwinState
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class TwinState:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_state(self, twin_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        stmt = select(DigitalTwinState).where(DigitalTwinState.twin_id == twin_id).order_by(DigitalTwinState.observed_at.desc())
        res = await self.db.execute(stmt)
        record = res.scalars().first()
        return record.state_data if record else None

    async def update_state(self, twin_id: uuid.UUID, data: Dict[str, Any]):
        state = DigitalTwinState(twin_id=twin_id, state_data=data)
        self.db.add(state)
        await self.db.commit()
