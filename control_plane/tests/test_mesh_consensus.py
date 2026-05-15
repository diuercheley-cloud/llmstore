import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.services.mesh.control_plane_mesh import ControlPlaneMeshService
from app.services.mesh.mesh_consensus import MeshConsensusService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_propose_event(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    consensus_service = MeshConsensusService(db_session)
    node = mesh_service.register_node("node-1", "us-east-1", "pub-key-1")
    
    event = consensus_service.propose_event(1, "state_commit", node.id, {"data": "test"}, "sig")
    assert event.term == 1
    assert event.event_type == "state_commit"
    assert not event.quorum_reached

def test_validate_quorum(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    consensus_service = MeshConsensusService(db_session)
    node = mesh_service.register_node("node-1", "us-east-1", "pub-key-1")
    event = consensus_service.propose_event(1, "state_commit", node.id, {"data": "test"}, "sig")
    
    # 2 out of 3 is majority
    has_quorum = consensus_service.validate_quorum(event.id, 2, 3)
    assert has_quorum
    assert event.quorum_reached

def test_deterministic_leader_election(db_session):
    mesh_service = ControlPlaneMeshService(db_session)
    consensus_service = MeshConsensusService(db_session)
    
    # Create 3 nodes
    mesh_service.register_node("node-1", "us-east-1", "pub")
    mesh_service.register_node("node-2", "us-east-2", "pub")
    mesh_service.register_node("node-3", "eu-west-1", "pub")
    
    leader1 = consensus_service.deterministic_leader_election(1)
    assert leader1 is not None
    assert leader1.is_leader
    
    leader2 = consensus_service.deterministic_leader_election(1) # Same term, same leader
    assert leader1.id == leader2.id
    assert leader2.is_leader
    
    leader3 = consensus_service.deterministic_leader_election(2) # Different term, probably different leader
    assert leader3.is_leader
