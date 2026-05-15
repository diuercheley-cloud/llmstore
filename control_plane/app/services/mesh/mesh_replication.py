from sqlalchemy.orm import Session
from app.models.commercial_control_plane_mesh import CommercialMeshReplicationLog
import uuid
from typing import List

class MeshReplicationService:
    def __init__(self, db: Session):
        self.db = db

    def append_log(self, node_id: str, log_index: int, operation: str, target_entity: str, target_id: str, changes: dict, hash_signature: str) -> CommercialMeshReplicationLog:
        log = CommercialMeshReplicationLog(
            id=str(uuid.uuid4()),
            node_id=node_id,
            log_index=log_index,
            operation=operation,
            target_entity=target_entity,
            target_id=target_id,
            changes=changes,
            hash_signature=hash_signature,
            applied=False
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs_since(self, log_index: int) -> List[CommercialMeshReplicationLog]:
        return self.db.query(CommercialMeshReplicationLog).filter(CommercialMeshReplicationLog.log_index > log_index).order_by(CommercialMeshReplicationLog.log_index).all()

    def mark_log_applied(self, log_id: str):
        log = self.db.query(CommercialMeshReplicationLog).filter(CommercialMeshReplicationLog.id == log_id).first()
        if log:
            log.applied = True
            self.db.commit()
        return log

    def reconcile_state(self, peer_logs: List[dict]):
        # Iterate and apply missing logs
        applied_count = 0
        for log_data in peer_logs:
            existing_log = self.db.query(CommercialMeshReplicationLog).filter(CommercialMeshReplicationLog.log_index == log_data.get('log_index')).first()
            if not existing_log:
                self.append_log(
                    node_id=log_data.get('node_id'),
                    log_index=log_data.get('log_index'),
                    operation=log_data.get('operation'),
                    target_entity=log_data.get('target_entity'),
                    target_id=log_data.get('target_id'),
                    changes=log_data.get('changes'),
                    hash_signature=log_data.get('hash_signature')
                )
                applied_count += 1
        return applied_count
