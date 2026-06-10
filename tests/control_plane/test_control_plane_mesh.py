import pytest
from app.db.base import Base
from app.services.mesh.control_plane_mesh import ControlPlaneMeshService
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

def test_register_node(db_session):
    service = ControlPlaneMeshService(db_session)
    node = service.register_node("node-1", "us-east-1", "pub-key-1")
    assert node.name == "node-1"
    assert node.region == "us-east-1"
    assert node.status == "active"
    assert node.mode == "multi_region"

def test_report_health(db_session):
    service = ControlPlaneMeshService(db_session)
    node = service.register_node("node-1", "us-east-1", "pub-key-1")
    health = service.report_health(node.id, "node-2", 15, "healthy")
    assert health.node_id == node.id
    assert health.latency_ms == 15
    assert health.status == "healthy"

def test_enable_sovereign_partition_mode(db_session):
    service = ControlPlaneMeshService(db_session)
    node = service.register_node("node-1", "us-east-1", "pub-key-1")
    node = service.enable_sovereign_partition_mode(node.id)
    assert node.mode == "sovereign_partitioned"
    assert node.status == "partitioned"

def test_recover_offline_sync(db_session):
    service = ControlPlaneMeshService(db_session)
    node = service.register_node("node-1", "us-east-1", "pub-key-1")
    node = service.enable_sovereign_partition_mode(node.id)
    node = service.recover_offline_sync(node.id)
    assert node.status == "syncing"
