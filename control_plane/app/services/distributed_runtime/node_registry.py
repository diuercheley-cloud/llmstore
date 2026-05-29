import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.runtime.distributed_runtime import RuntimeNode

class NodeRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_nodes(self) -> List[RuntimeNode]:
        result = await self.db.execute(select(RuntimeNode))
        return list(result.scalars().all())