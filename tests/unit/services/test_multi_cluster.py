import pytest
from app.services.multi_cluster_operations import MultiClusterOperationsService


@pytest.mark.asyncio
async def test_cluster_creation_and_status(db_session):
    service = MultiClusterOperationsService(db_session)
    cluster = await service.create_cluster("DC-Alpha", "primary", "http://alpha.internal")
    
    assert cluster.name == "DC-Alpha"
    assert cluster.status == "active"
    
    updated = await service.set_cluster_status(cluster.id, "maintenance", reason="Updating BIOS")
    
    # Reload with failover events
    updated = await service.get_cluster(cluster.id)
    
    assert updated.status == "maintenance"
    assert len(updated.failover_events) == 1

@pytest.mark.asyncio
async def test_sync_security_safeguard(db_session):
    service = MultiClusterOperationsService(db_session)
    alpha = await service.create_cluster("Alpha", "primary", "http://alpha")
    beta = await service.create_cluster("Beta", "standby", "http://beta")
    
    # Payload with prompt should fail
    bad_payload = {"config_version": 1, "last_prompt": "Hello world"}
    with pytest.raises(ValueError, match="Security Violation"):
        await service.sync_cluster_config(alpha.id, beta.id, bad_payload)
    
    # Safe payload should succeed
    safe_payload = {"config_version": 1, "node_count": 5}
    event = await service.sync_cluster_config(alpha.id, beta.id, safe_payload)
    assert event.status == "success"

@pytest.mark.asyncio
async def test_health_snapshot_generation(db_session):
    service = MultiClusterOperationsService(db_session)
    cluster = await service.create_cluster("Alpha", "primary", "http://alpha")
    
    snapshot = await service.generate_health_snapshot(cluster.id)
    assert snapshot.health_score > 0
    assert "cpu_usage" in snapshot.metrics_json
