import logging
import uuid
from datetime import timedelta

from app.core.time import utc_now
from app.models.runtime.distributed_runtime import RuntimeNodeHeartbeat
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ClusterHeartbeatService:
    """
    Processes cluster heartbeats and maintains health scores.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_heartbeat(self, cluster_id: str, data: dict) -> dict:
        node_id_str = data.get("node_id", "unknown")
        cpu = data.get("cpu_utilization", data.get("cpu_usage_percent", 0.0))
        memory = data.get("memory_utilization", data.get("memory_usage_mb", 0.0))
        gpu = data.get("gpu_utilization", 0.0)
        status = data.get("status", "active")

        try:
            node_uuid = (
                uuid.UUID(node_id_str)
                if isinstance(node_id_str, str) and len(node_id_str) == 36
                else uuid.uuid4()
            )
        except (ValueError, AttributeError):
            node_uuid = uuid.uuid4()

        heartbeat = RuntimeNodeHeartbeat(
            node_id=node_uuid,
            cpu_usage_percent=cpu,
            memory_usage_mb=memory,
            gpu_usage_percent={"avg": gpu},
            active_requests=data.get("active_requests", 0),
            metrics={"cluster_id": cluster_id, "status": status, "health_score": 0.0},
        )
        self.db.add(heartbeat)
        await self.db.flush()

        health_score = self._compute_health_score(cpu, memory, gpu, status)
        heartbeat.metrics["health_score"] = health_score

        logger.info(f"Cluster {cluster_id} node {node_id_str}: health={health_score:.2f}")
        return {"cluster_id": cluster_id, "node_id": node_id_str, "health_score": health_score}

    async def get_cluster_health(self, cluster_id: str, minutes: int = 5) -> dict:
        cutoff = utc_now() - timedelta(minutes=minutes)
        stmt = (
            select(RuntimeNodeHeartbeat)
            .where(
                RuntimeNodeHeartbeat.created_at >= cutoff,
            )
            .order_by(RuntimeNodeHeartbeat.created_at.desc())
        )
        res = await self.db.execute(stmt)
        recent = list(res.scalars().all())

        if not recent:
            return {"cluster_id": cluster_id, "healthy": False, "reason": "no recent heartbeats"}

        cluster_heartbeats = [h for h in recent if h.metrics.get("cluster_id") == cluster_id]
        if not cluster_heartbeats:
            return {
                "cluster_id": cluster_id,
                "healthy": False,
                "reason": f"no heartbeats for cluster {cluster_id}",
            }

        nodes = set(str(h.node_id) for h in cluster_heartbeats)
        avg_cpu = sum(h.cpu_usage_percent for h in cluster_heartbeats) / len(cluster_heartbeats)
        avg_mem = sum(h.memory_usage_mb for h in cluster_heartbeats) / len(cluster_heartbeats)
        avg_gpu_values = [
            h.gpu_usage_percent.get("avg", 0)
            if isinstance(h.gpu_usage_percent, dict)
            else h.gpu_usage_percent
            for h in cluster_heartbeats
        ]
        avg_gpu = sum(avg_gpu_values) / len(avg_gpu_values) if avg_gpu_values else 0

        return {
            "cluster_id": cluster_id,
            "healthy": avg_cpu < 90 and avg_mem < 90,
            "active_nodes": len(nodes),
            "total_heartbeats": len(cluster_heartbeats),
            "avg_cpu": round(avg_cpu, 1),
            "avg_memory": round(avg_mem, 1),
            "avg_gpu": round(avg_gpu, 1),
            "health_score": round(
                self._compute_health_score(avg_cpu, avg_mem, avg_gpu, "active"), 2
            ),
        }

    @staticmethod
    def _compute_health_score(cpu: float, memory: float, gpu: float, status: str) -> float:
        if status in ("offline", "failed", "unknown"):
            return 0.0
        cpu_score = max(0, 1 - cpu / 100)
        mem_score = max(0, 1 - memory / 100)
        gpu_score = max(0, 1 - gpu / 100)
        return (cpu_score * 0.4 + mem_score * 0.4 + gpu_score * 0.2) * 100
