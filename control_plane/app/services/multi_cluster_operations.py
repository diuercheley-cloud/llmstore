from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.models.operations.multi_cluster import (
    Cluster,
    ClusterFailoverEvent,
    ClusterHealthSnapshot,
    ClusterSyncEvent,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class MultiClusterOperationsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def create_cluster(self, name: str, cluster_type: str, base_url: str, location: str = None) -> Cluster:
        cluster = Cluster(
            name=name,
            cluster_type=cluster_type,
            base_url=base_url,
            location=location,
            status="active"
        )
        self.db.add(cluster)
        await self.db.commit()
        await self.db.refresh(cluster)
        return cluster

    async def list_clusters(self) -> List[Cluster]:
        result = await self.db.execute(select(Cluster))
        return result.scalars().all()

    async def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        result = await self.db.execute(
            select(Cluster)
            .options(selectinload(Cluster.health_snapshots))
            .options(selectinload(Cluster.failover_events))
            .where(Cluster.id == cluster_id)
        )
        return result.scalars().first()

    async def set_cluster_status(self, cluster_id: str, status: str, reason: str = None, operator_id: str = None) -> Cluster:
        cluster = await self.db.get(Cluster, cluster_id)
        if not cluster:
            raise ValueError("Cluster not found")
            
        old_status = cluster.status
        cluster.status = status
        
        # Log failover/status event
        event = ClusterFailoverEvent(
            cluster_id=cluster_id,
            from_status=old_status,
            to_status=status,
            reason=reason or f"Status changed to {status}",
            operator_id=operator_id,
            is_automatic=False
        )
        self.db.add(event)
        
        await self.db.commit()
        await self.db.refresh(cluster)
        return cluster

    async def generate_health_snapshot(self, cluster_id: str) -> ClusterHealthSnapshot:
        # In a real scenario, this would probe the remote cluster base_url
        snapshot = ClusterHealthSnapshot(
            cluster_id=cluster_id,
            health_score=0.95,
            metrics_json={
                "cpu_usage": 45.2,
                "memory_usage": 68.1,
                "gpu_usage": 32.5,
                "error_rate": 0.001
            }
        )
        self.db.add(snapshot)
        await self.db.commit()
        return snapshot

    async def sync_cluster_config(self, source_id: str, target_id: str, payload: Dict[str, Any]) -> ClusterSyncEvent:
        # Safeguard: No prompts or documents allowed in sync payload
        sensitive_keys = {"prompt", "content", "document", "file_data", "api_key", "secret"}
        if any(key in str(payload).lower() for key in sensitive_keys):
            event = ClusterSyncEvent(
                source_cluster_id=source_id,
                target_cluster_id=target_id,
                sync_type="CONFIG",
                status="failed",
                payload_size_bytes=len(str(payload)),
                error_message="Security Violation: Sensitive data detected in sync payload."
            )
            self.db.add(event)
            await self.db.commit()
            raise ValueError("Security Violation: Multi-cluster sync cannot carry sensitive data (prompts/docs).")

        event = ClusterSyncEvent(
            source_cluster_id=source_id,
            target_cluster_id=target_id,
            sync_type="CONFIG",
            status="success",
            payload_size_bytes=len(str(payload))
        )
        self.db.add(event)
        await self.db.commit()
        return event

    async def list_sync_events(self, cluster_id: str) -> List[ClusterSyncEvent]:
        result = await self.db.execute(
            select(ClusterSyncEvent)
            .where((ClusterSyncEvent.source_cluster_id == cluster_id) | (ClusterSyncEvent.target_cluster_id == cluster_id))
            .order_by(ClusterSyncEvent.timestamp.desc())
            .limit(50)
        )
        return result.scalars().all()
