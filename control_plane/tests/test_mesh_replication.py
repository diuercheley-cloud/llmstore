import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.services.mesh.control_plane_mesh import ControlPlaneMeshService
from app.services.mesh.mesh_replication import MeshReplicationService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_append_and_get_logs(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    repl_service = MeshReplicationService(db_session)
    node = mesh_service.register_node("node-1", "us-east-1", "pub")
    
    log = repl_service.append_log(node.id, 1, "CREATE", "Policy", "pol-1", {"rules": []}, "hash1")
    assert log.log_index == 1
    assert log.applied == False
    
    logs = repl_service.get_logs_since(0)
    assert len(logs) == 1
    assert logs[0].id == log.id

def test_mark_log_applied(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    repl_service = MeshReplicationService(db_session)
    node = mesh_service.register_node("node-1", "us-east-1", "pub")
    
    log = repl_service.append_log(node.id, 1, "CREATE", "Policy", "pol-1", {"rules": []}, "hash1")
    repl_service.mark_log_applied(log.id)
    assert log.applied == True

def test_reconcile_state(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    repl_service = MeshReplicationService(db_session)
    node = mesh_service.register_node("node-1", "us-east-1", "pub")
    
    peer_logs = [
        {"node_id": node.id, "log_index": 1, "operation": "CREATE", "target_entity": "T", "target_id": "T1", "changes": {}, "hash_signature": "h1"},
        {"node_id": node.id, "log_index": 2, "operation": "UPDATE", "target_entity": "T", "target_id": "T1", "changes": {}, "hash_signature": "h2"}
    ]
    
    applied = repl_service.reconcile_state(peer_logs)
    assert applied == 2
    
    # Run again, should not re-apply
    applied = repl_service.reconcile_state(peer_logs)
    assert applied == 0
