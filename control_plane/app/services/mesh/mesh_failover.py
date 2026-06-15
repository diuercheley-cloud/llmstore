import uuid

from app.core.time import utc_now
from app.models.commercial.commercial_control_plane_mesh import (
    CommercialMeshNode,
    CommercialMeshPartitionEvent,
)
from sqlalchemy.orm import Session


class MeshFailoverService:
    def __init__(self, db: Session):
        self.db = db

    def orchestrate_failover(self, failed_node_id: str, term: int):
        # Trigger deterministic leader election to replace failed node
        from app.services.mesh.mesh_consensus import MeshConsensusService

        consensus_service = MeshConsensusService(self.db)

        # Mark node as inactive
        node = (
            self.db.query(CommercialMeshNode)
            .filter(CommercialMeshNode.id == failed_node_id)
            .first()
        )
        if node:
            node.status = "inactive"
            node.is_leader = False
            self.db.commit()

        new_leader = consensus_service.deterministic_leader_election(term)
        return new_leader

    def detect_partition(
        self, partition_id: str, isolated_node_ids: list[str]
    ) -> CommercialMeshPartitionEvent:
        event = CommercialMeshPartitionEvent(
            id=str(uuid.uuid4()),
            partition_id=partition_id,
            isolated_nodes={"nodes": isolated_node_ids},
            mode_fallback="sovereign_partitioned",
        )
        self.db.add(event)

        # Update node modes
        nodes = (
            self.db.query(CommercialMeshNode)
            .filter(CommercialMeshNode.id.in_(isolated_node_ids))
            .all()
        )
        for node in nodes:
            node.mode = "sovereign_partitioned"
            node.status = "partitioned"

        self.db.commit()
        self.db.refresh(event)
        return event

    def resolve_partition(self, partition_id: str, resolution_details: dict):
        event = (
            self.db.query(CommercialMeshPartitionEvent)
            .filter(CommercialMeshPartitionEvent.partition_id == partition_id)
            .first()
        )
        if event:
            event.resolved_at = utc_now()
            event.resolution_details = resolution_details

            isolated_node_ids = event.isolated_nodes.get("nodes", [])
            nodes = (
                self.db.query(CommercialMeshNode)
                .filter(CommercialMeshNode.id.in_(isolated_node_ids))
                .all()
            )
            for node in nodes:
                node.mode = "multi_region"
                node.status = "syncing"

            self.db.commit()
            self.db.refresh(event)
        return event
