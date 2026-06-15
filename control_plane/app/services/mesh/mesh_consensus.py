import uuid

from app.models.commercial.commercial_control_plane_mesh import (
    CommercialMeshConsensusEvent,
    CommercialMeshNode,
)
from sqlalchemy.orm import Session


class MeshConsensusService:
    def __init__(self, db: Session):
        self.db = db

    def propose_event(
        self, term: int, event_type: str, proposer_node_id: str, payload: dict, signature: str
    ) -> CommercialMeshConsensusEvent:
        event = CommercialMeshConsensusEvent(
            id=str(uuid.uuid4()),
            term=term,
            event_type=event_type,
            proposer_node_id=proposer_node_id,
            payload=payload,
            signature=signature,
            quorum_reached=False,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def validate_quorum(self, event_id: str, votes: int, total_nodes: int) -> bool:
        # Simple majority quorum
        if total_nodes == 0:
            return False

        has_quorum = votes > (total_nodes / 2)
        if has_quorum:
            event = (
                self.db.query(CommercialMeshConsensusEvent)
                .filter(CommercialMeshConsensusEvent.id == event_id)
                .first()
            )
            if event:
                event.quorum_reached = True
                self.db.commit()
        return has_quorum

    def deterministic_leader_election(self, term: int) -> CommercialMeshNode | None:
        # Implementation of deterministic leader election based on term and node priority/hash
        nodes = (
            self.db.query(CommercialMeshNode).filter(CommercialMeshNode.status == "active").all()
        )
        if not nodes:
            return None

        # Simplistic deterministic approach: sort by ID and pick based on modulo
        nodes.sort(key=lambda n: n.id)
        leader_index = term % len(nodes)
        leader = nodes[leader_index]

        # Demote current leader
        current_leaders = (
            self.db.query(CommercialMeshNode).filter(CommercialMeshNode.is_leader == True).all()
        )
        for cl in current_leaders:
            cl.is_leader = False

        # Promote new leader
        leader.is_leader = True
        self.db.commit()

        return leader
