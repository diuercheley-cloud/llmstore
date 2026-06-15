from app.models.runtime.distributed_runtime import RuntimeNode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class NodeRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_nodes(self) -> list[RuntimeNode]:
        result = await self.db.execute(select(RuntimeNode))
        return list(result.scalars().all())
