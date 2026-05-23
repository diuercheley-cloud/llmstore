# Owner: commercial-ops
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, require_admin_user
from app.services.mesh.control_plane_mesh import ControlPlaneMeshService
from app.services.mesh.mesh_consensus import MeshConsensusService
from app.services.mesh.mesh_replication import MeshReplicationService
from app.services.mesh.mesh_failover import MeshFailoverService
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter(prefix="/admin/mesh", tags=["Commercial Mesh Admin"])
portal_router = APIRouter(prefix="/portal/mesh", tags=["Customer Portal Mesh"])

# Schema definitions
class NodeCreate(BaseModel):
    name: str
    region: str
    public_key: str
    mode: Optional[str] = "multi_region"

class NodeHealthReport(BaseModel):
    peer_node_id: str
    latency_ms: int
    status: str

# Admin Endpoints
@router.post("/nodes")
def register_node(node: NodeCreate, db: Session = Depends(get_db), admin=Depends(require_admin_user)):
    service = ControlPlaneMeshService(db)
    return service.register_node(node.name, node.region, node.public_key, node.mode)

@router.get("/nodes")
def list_nodes(db: Session = Depends(get_db), admin=Depends(require_admin_user)):
    service = ControlPlaneMeshService(db)
    return service.list_nodes()

@router.post("/nodes/{node_id}/health")
def report_health(node_id: str, report: NodeHealthReport, db: Session = Depends(get_db), admin=Depends(require_admin_user)):
    service = ControlPlaneMeshService(db)
    return service.report_health(node_id, report.peer_node_id, report.latency_ms, report.status)

@router.get("/consensus")
def trigger_election(term: int, db: Session = Depends(get_db), admin=Depends(require_admin_user)):
    service = MeshConsensusService(db)
    return service.deterministic_leader_election(term)

@router.get("/replication")
def get_replication_logs(since_index: int = 0, db: Session = Depends(get_db), admin=Depends(require_admin_user)):
    service = MeshReplicationService(db)
    return service.get_logs_since(since_index)

@router.post("/failover/{failed_node_id}")
def orchestrate_failover(failed_node_id: str, term: int, db: Session = Depends(get_db), admin=Depends(require_admin_user)):
    service = MeshFailoverService(db)
    return service.orchestrate_failover(failed_node_id, term)

# Portal Endpoints
@portal_router.get("/status")
def get_mesh_status(db: Session = Depends(get_db)):
    service = ControlPlaneMeshService(db)
    nodes = service.list_nodes()
    return {"status": "healthy", "nodes_count": len(nodes), "active_leaders": sum(1 for n in nodes if n.is_leader)}
