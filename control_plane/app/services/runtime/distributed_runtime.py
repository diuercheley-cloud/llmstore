import logging
import uuid
from datetime import timedelta

from app.core.metrics import (
    LLM_RUNTIME_FAILOVERS_TOTAL,
    LLM_RUNTIME_NODE_HEARTBEATS_TOTAL,
    LLM_RUNTIME_NODES_TOTAL,
)
from app.core.time import utc_now
from app.models.runtime.distributed_runtime import (
    RuntimeFailoverEvent,
    RuntimeModelPlacement,
    RuntimeNode,
    RuntimeNodeHeartbeat,
    RuntimeRoutingEvent,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DistributedRuntimeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_node(self, node_data: dict) -> RuntimeNode:
        # Check if node already exists by name or base_url
        query = select(RuntimeNode).where(
            (RuntimeNode.name == node_data["name"])
            | (RuntimeNode.base_url == node_data["base_url"])
        )
        result = await self.db.execute(query)
        existing_node = result.scalars().first()

        if existing_node:
            # Update existing node
            for key, value in node_data.items():
                setattr(existing_node, key, value)
            existing_node.status = "ready"
            existing_node.last_heartbeat_at = utc_now()
            await self.db.commit()
            await self.db.refresh(existing_node)
            return existing_node

        new_node = RuntimeNode(
            name=node_data["name"],
            base_url=node_data["base_url"],
            node_type=node_data.get("node_type", "remote"),
            gpu_count=node_data.get("gpu_count", 0),
            gpu_memory_total_mb=node_data.get("gpu_memory_total_mb", 0),
            cpu_count=node_data.get("cpu_count", 0),
            memory_total_mb=node_data.get("memory_total_mb", 0),
            capabilities=node_data.get("capabilities", {}),
            trust_level=node_data.get("trust_level", 1),
            status="ready",
            last_heartbeat_at=utc_now(),
        )
        self.db.add(new_node)
        await self.db.commit()
        await self.db.refresh(new_node)

        # Record metric
        LLM_RUNTIME_NODES_TOTAL.labels(node_type=new_node.node_type).inc()

        return new_node

    async def record_heartbeat(self, node_id: uuid.UUID, heartbeat_data: dict):
        # Update node last_heartbeat_at and status
        await self.db.execute(
            update(RuntimeNode)
            .where(RuntimeNode.id == node_id)
            .values(last_heartbeat_at=utc_now(), status="ready")
        )

        heartbeat = RuntimeNodeHeartbeat(
            node_id=node_id,
            cpu_usage_percent=heartbeat_data.get("cpu_usage_percent", 0.0),
            memory_usage_mb=heartbeat_data.get("memory_usage_mb", 0.0),
            gpu_usage_percent=heartbeat_data.get("gpu_usage_percent", {}),
            active_requests=heartbeat_data.get("active_requests", 0),
            metrics=heartbeat_data.get("metrics", {}),
        )
        self.db.add(heartbeat)
        await self.db.commit()

        # Record metrics
        LLM_RUNTIME_NODE_HEARTBEATS_TOTAL.labels(node_id=str(node_id)).inc()

    async def drain_node(self, node_id: uuid.UUID):
        await self.db.execute(
            update(RuntimeNode).where(RuntimeNode.id == node_id).values(status="draining")
        )
        await self.db.commit()

    async def list_nodes(self, status: str | None = None) -> list[RuntimeNode]:
        query = select(RuntimeNode)
        if status:
            query = query.where(RuntimeNode.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_node(self, node_id: uuid.UUID) -> RuntimeNode | None:
        result = await self.db.execute(select(RuntimeNode).where(RuntimeNode.id == node_id))
        return result.scalars().first()

    async def select_node_for_model(
        self, model_id: uuid.UUID, strategy: str = "least_load"
    ) -> RuntimeNode | None:
        # Get all nodes that have this model ready
        query = (
            select(RuntimeNode)
            .join(RuntimeModelPlacement)
            .where(
                RuntimeModelPlacement.model_id == model_id,
                RuntimeModelPlacement.status == "ready",
                RuntimeNode.status == "ready",
            )
        )

        # Check heartbeats (offline if no heartbeat in last 60s)
        cutoff = utc_now() - timedelta(seconds=60)
        query = query.where(RuntimeNode.last_heartbeat_at >= cutoff)

        result = await self.db.execute(query)
        nodes = result.scalars().all()

        if not nodes:
            return None

        if strategy == "round_robin":
            # Simple RR based on last selection or ID
            nodes.sort(key=lambda x: x.id)
            # This would need a way to track the last index, e.g. in Redis
            return nodes[0]

        if strategy == "least_load":
            # Get latest heartbeat for each node
            node_load = {}
            for node in nodes:
                hb_query = (
                    select(RuntimeNodeHeartbeat)
                    .where(RuntimeNodeHeartbeat.node_id == node.id)
                    .order_by(RuntimeNodeHeartbeat.created_at.desc())
                    .limit(1)
                )
                hb_result = await self.db.execute(hb_query)
                hb = hb_result.scalars().first()
                node_load[node.id] = getattr(hb, "active_requests", 0) if hb else 0

            best_node_id = min(node_load, key=node_load.get)
            return next(n for n in nodes if n.id == best_node_id)

        if strategy == "gpu_priority":
            # Select node with most free GPU memory or count
            return sorted(nodes, key=lambda x: x.gpu_count, reverse=True)[0]

        return nodes[0]

    async def record_routing_event(
        self, request_id: str, model_id: uuid.UUID, node_id: uuid.UUID, strategy: str
    ):
        event = RuntimeRoutingEvent(
            request_id=request_id,
            model_id=model_id,
            selected_node_id=node_id,
            routing_strategy=strategy,
        )
        self.db.add(event)
        await self.db.commit()

    async def record_failover_event(
        self,
        request_id: str,
        failed_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        reason: str,
        model_id: uuid.UUID | None = None,
    ):
        event = RuntimeFailoverEvent(
            request_id=request_id,
            failed_node_id=failed_node_id,
            target_node_id=target_node_id,
            reason=reason,
        )
        self.db.add(event)
        await self.db.commit()

        LLM_RUNTIME_FAILOVERS_TOTAL.labels(
            model_id=str(model_id) if model_id else "unknown", reason=reason
        ).inc()

    async def update_node_statuses(self):
        """Background task to mark nodes as offline if they missed heartbeats"""
        cutoff = utc_now() - timedelta(seconds=60)
        await self.db.execute(
            update(RuntimeNode)
            .where(RuntimeNode.status == "ready")
            .where(RuntimeNode.last_heartbeat_at < cutoff)
            .values(status="offline")
        )
        await self.db.commit()
