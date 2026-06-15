from app.models.runtime.distributed_runtime import DistributedAgentJob, RuntimeNode
from app.services.distributed_runtime.node_registry import NodeRegistry
from sqlalchemy.ext.asyncio import AsyncSession


class JobPlacementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def place_job(self, job: DistributedAgentJob) -> RuntimeNode | None:
        nodes = await NodeRegistry(self.db).list_nodes()
        ready_nodes = [n for n in nodes if n.status == "ready"]

        if not ready_nodes:
            return None

        # 1. GPU required filter
        if job.requires_gpu:
            ready_nodes = [n for n in ready_nodes if n.gpu_count > 0]

        # 2. Local first (assume node with node_type == "local" is local)
        local_nodes = [n for n in ready_nodes if n.node_type == "local"]
        if local_nodes:
            return local_nodes[0]

        # 3. Random ready node (fallback)
        return ready_nodes[0] if ready_nodes else None
