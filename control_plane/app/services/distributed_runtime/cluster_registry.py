import uuid
from typing import List, Optional

from app.models.runtime.distributed_runtime import RuntimeCluster
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ClusterRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_cluster(self, name: str, region: str, is_managed: bool = False) -> RuntimeCluster:
        result = await self.db.execute(select(RuntimeCluster).where(RuntimeCluster.name == name))
        cluster = result.scalars().first()
        if not cluster:
            cluster = RuntimeCluster(name=name, region=region, is_managed=is_managed)
            self.db.add(cluster)
        else:
            cluster.region = region
            cluster.is_managed = is_managed
        await self.db.commit()
        await self.db.refresh(cluster)
        return cluster

    async def list_clusters(self) -> List[RuntimeCluster]:
        result = await self.db.execute(select(RuntimeCluster))
        return list(result.scalars().all())

    async def get_cluster(self, cluster_id: uuid.UUID) -> Optional[RuntimeCluster]:
        result = await self.db.execute(select(RuntimeCluster).where(RuntimeCluster.id == cluster_id))
        return result.scalars().first()