import pytest
from app.db.base import Base
from app.services.mesh.control_plane_mesh import ControlPlaneMeshService
from app.services.mesh.mesh_failover import MeshFailoverService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_orchestrate_failover(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    failover_service = MeshFailoverService(db_session)
    
    node1 = mesh_service.register_node("node-1", "us-east-1", "pub")
    node2 = mesh_service.register_node("node-2", "us-east-2", "pub")
    
    new_leader = failover_service.orchestrate_failover(node1.id, 5)
    assert new_leader is not None
    assert node1.status == "inactive"
    assert not node1.is_leader
    assert new_leader.is_leader

def test_detect_and_resolve_partition(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    failover_service = MeshFailoverService(db_session)
    
    node1 = mesh_service.register_node("node-1", "us-east-1", "pub")
    node2 = mesh_service.register_node("node-2", "eu-west-1", "pub")
    
    event = failover_service.detect_partition("part-1", [node2.id])
    assert event.partition_id == "part-1"
    assert node2.mode == "sovereign_partitioned"
    assert node2.status == "partitioned"
    
    resolved_event = failover_service.resolve_partition("part-1", {"sync": "complete"})
    assert resolved_event.resolved_at is not None
    assert node2.mode == "multi_region"
    assert node2.status == "syncing"
