# Owner: agent-platform
from typing import Any

from app.models.agents.agent_federated_memory import RemoteMemoryReference
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class RemoteMemoryReferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_reference(self, tenant_id: str, data: dict[str, Any]) -> RemoteMemoryReference:
        ref = RemoteMemoryReference(
            local_tenant_id=tenant_id,
            remote_cluster_id=data["cluster_id"],
            remote_memory_id=data["memory_id"],
            reference_type=data.get("type", "pointer"),
        )
        self.db.add(ref)
        await self.db.commit()
        await self.db.refresh(ref)
        return ref

    async def revoke_reference(self, remote_cluster_id: str, remote_memory_id: str):
        """
        Invalidates references when a memory is revoked at the source cluster.
        """
        stmt = select(RemoteMemoryReference).where(
            RemoteMemoryReference.remote_cluster_id == remote_cluster_id,
            RemoteMemoryReference.remote_memory_id == remote_memory_id,
        )
        res = await self.db.execute(stmt)
        refs = res.scalars().all()

        for ref in refs:
            ref.is_valid = False

        await self.db.commit()
        return len(refs)
