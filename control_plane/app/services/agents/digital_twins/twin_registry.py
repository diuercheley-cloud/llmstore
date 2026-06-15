# Owner: agent-platform
import uuid
from typing import Any

from app.models.agents.digital_twin import DigitalTwin
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class TwinRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, tenant_id: str, data: dict[str, Any]) -> DigitalTwin:
        twin = DigitalTwin(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            twin_type=data["twin_type"],
            connector_type=data.get("connector_type", "mock"),
            config=data.get("config", {}),
        )
        self.db.add(twin)
        await self.db.commit()
        await self.db.refresh(twin)
        return twin

    async def get_twin(self, twin_id: uuid.UUID) -> DigitalTwin | None:
        return await self.db.get(DigitalTwin, twin_id)

    async def list_twins(self, tenant_id: str) -> list[DigitalTwin]:
        stmt = select(DigitalTwin).where(DigitalTwin.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
