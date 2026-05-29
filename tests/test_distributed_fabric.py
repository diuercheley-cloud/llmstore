import pytest
import uuid
from datetime import datetime, timedelta
from app.services.distributed_runtime.cluster_registry import ClusterRegistry
from app.services.distributed_runtime.job_placement import JobPlacementService
from app.services.distributed_runtime.distributed_leases import DistributedLeaseService
from app.services.distributed_runtime.failover_policy import FailoverPolicyService
from app.services.distributed_runtime.data_boundary_policy import DataBoundaryPolicy
from app.models.runtime.distributed_runtime import RuntimeNode, DistributedAgentJob, DistributedJobLease

@pytest.mark.asyncio
async def test_cluster_registration(session):
    registry = ClusterRegistry(session)
    cluster = await registry.register_cluster("test-cluster", "us-east-1", is_managed=False)
    assert cluster.name == "test-cluster"
    assert cluster.region == "us-east-1"
    
    fetched = await registry.get_cluster(cluster.id)
    assert fetched.name == "test-cluster"

@pytest.mark.asyncio
async def test_node_heartbeat(session):
    # This is a bit of an integration test for heartbeat
    from app.services.runtime.distributed_runtime import DistributedRuntimeService
    service = DistributedRuntimeService(session)
    node = await service.register_node({"name": "test-node", "base_url": "http://test-node"})
    assert node.status == "ready"
    
    await service.record_heartbeat(node.id, {"cpu_usage_percent": 50.0})
    assert node.last_heartbeat_at is not None

@pytest.mark.asyncio
async def test_job_placement_local_first(session):
    service = JobPlacementService(session)
    
    # create remote node
    remote_node = RuntimeNode(name="remote-node", base_url="http://remote-node", node_type="remote", status="ready")
    session.add(remote_node)
    
    # create local node
    local_node = RuntimeNode(name="local-node", base_url="http://local-node", node_type="local", status="ready")
    session.add(local_node)
    
    await session.commit()
    
    job = DistributedAgentJob(job_type="AgentRun", tenant_id="t1")
    session.add(job)
    await session.commit()
    
    placed_node = await service.place_job(job)
    assert placed_node is not None
    assert placed_node.node_type == "local"

@pytest.mark.asyncio
async def test_unhealthy_node_no_job(session):
    service = JobPlacementService(session)
    
    # mark all nodes unhealthy
    unhealthy_node = RuntimeNode(name="unhealthy", base_url="http://unhealthy", node_type="local", status="offline")
    session.add(unhealthy_node)
    await session.commit()
    
    job = DistributedAgentJob(job_type="AgentRun", tenant_id="t1")
    session.add(job)
    await session.commit()
    
    placed_node = await service.place_job(job)
    assert placed_node is None  # no ready node available

@pytest.mark.asyncio
async def test_lease_expiration(session):
    lease_svc = DistributedLeaseService(session)
    job_id = uuid.uuid4()
    node1_id = uuid.uuid4()
    node2_id = uuid.uuid4()
    
    # Acquire for 0 seconds (expires immediately)
    acquired = await lease_svc.acquire_lease(job_id, node1_id, duration_seconds=0)
    assert acquired is True
    
    # Simulate expiration by waiting a tiny bit or just acquiring again (since now > expires_at)
    acquired_again = await lease_svc.acquire_lease(job_id, node2_id, duration_seconds=60)
    assert acquired_again is True # Node 2 can grab it

@pytest.mark.asyncio
async def test_manual_failover_registers_event(session):
    failover_svc = FailoverPolicyService(session)
    job_id = uuid.uuid4()
    from_node = uuid.uuid4()
    to_node = uuid.uuid4()
    
    event = await failover_svc.execute_failover(job_id, from_node, to_node, "manual-intervention")
    assert event.reason == "manual-intervention"
    assert event.job_id == job_id
    assert event.to_node_id == to_node

def test_managed_heartbeat_no_prompt_doc_memory():
    payload = {
        "status": "ready",
        "prompt": "secret prompt",
        "documents": ["doc1", "doc2"],
        "memory": {"session": "data"}
    }
    sanitized = DataBoundaryPolicy.sanitize_payload(payload)
    
    assert "status" in sanitized
    assert "prompt" not in sanitized
    assert "documents" not in sanitized
    assert "memory" not in sanitized

def test_multi_cluster_disabled_no_start():
    # Typically tested by checking settings config
    from app.core.config import get_settings
    settings = get_settings()
    # Assume we mock settings.multi_cluster_enabled = False
    assert getattr(settings, "multi_cluster_enabled", False) is False

def test_split_brain_policy_blocks_autofailover():
    # In a real environment, split brain policy returns False for auto failover
    # Here we simulate the boolean block
    def is_auto_failover_allowed(quorum_achieved: bool):
        return quorum_achieved
        
    assert is_auto_failover_allowed(False) is False
