import uuid
from typing import List, Optional

from app.models.commercial.commercial_control_plane_mesh import CommercialMeshHealthState, CommercialMeshNode
from sqlalchemy.orm import Session


class ControlPlaneMeshService:
    def __init__(self, db: Session):
        self.db = db

    def register_node(self, name: str, region: str, public_key: str, mode: str = "multi_region") -> CommercialMeshNode:
        node = CommercialMeshNode(
            id=str(uuid.uuid4()),
            name=name,
            region=region,
            mode=mode,
            public_key=public_key,
            status="active"
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_node(self, node_id: str) -> Optional[CommercialMeshNode]:
        return self.db.query(CommercialMeshNode).filter(CommercialMeshNode.id == node_id).first()

    def list_nodes(self) -> List[CommercialMeshNode]:
        return self.db.query(CommercialMeshNode).all()

    def update_node_status(self, node_id: str, status: str):
        node = self.get_node(node_id)
        if node:
            node.status = status
            self.db.commit()
            self.db.refresh(node)
        return node

    def report_health(self, node_id: str, peer_node_id: str, latency_ms: int, status: str):
        health = CommercialMeshHealthState(
            id=str(uuid.uuid4()),
            node_id=node_id,
            peer_node_id=peer_node_id,
            latency_ms=latency_ms,
            status=status
        )
        self.db.add(health)
        self.db.commit()
        return health

    def enable_sovereign_partition_mode(self, node_id: str):
        node = self.get_node(node_id)
        if node:
            node.mode = "sovereign_partitioned"
            node.status = "partitioned"
            self.db.commit()
            self.db.refresh(node)
        return node

    def recover_offline_sync(self, node_id: str):
        node = self.get_node(node_id)
        if node:
            node.status = "syncing"
            self.db.commit()
            self.db.refresh(node)
        return node
