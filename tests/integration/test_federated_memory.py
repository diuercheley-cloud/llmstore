
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.models.agents.agent_federated_memory import (
    FederatedMemoryPeer,
    FederatedMemorySummary,
    RemoteMemoryReference,
)
from app.services.agents.federated_memory.memory_summary_sync import MemorySummarySync
from app.services.agents.federated_memory.remote_memory_reference import (
    RemoteMemoryReferenceService,
)
from app.services.agents.federated_memory.sovereignty_policy import SovereigntyPolicy


@pytest_asyncio.fixture
async def setup_peer(session):
    peer = FederatedMemoryPeer(
        cluster_id="cluster-us-1",
        cluster_name="US Production",
        endpoint_url="http://us.local",
        trust_level="standard",
        data_residency_region="us-east-1"
    )
    session.add(peer)
    await session.commit()
    return peer

@pytest.mark.asyncio
async def test_raw_sync_bloqueado(session, setup_peer):
    policy = SovereigntyPolicy(session)
    # Trust level 'standard' should block raw data
    authorized, reason = await policy.validate_sync(setup_peer.id, "summary", is_raw=True)
    assert authorized is False
    assert "Raw data sync forbidden" in reason

@pytest.mark.asyncio
async def test_summary_sanitizado_sincroniza(session, setup_peer):
    settings = get_settings()
    settings.agent_federated_memory_enabled = True
    
    sync_service = MemorySummarySync(session)
    data = {
        "memory_id": "mem-123",
        "origin_cluster_id": "cluster-us-1",
        "text": "Clean summary of event",
        "is_raw": False
    }
    res = await sync_service.sync_summary(setup_peer.id, "tenant-a", data)
    assert res["status"] == "synced"
    
    from sqlalchemy.future import select
    stmt = select(FederatedMemorySummary).where(FederatedMemorySummary.original_memory_id == "mem-123")
    summary = (await session.execute(stmt)).scalar_one_or_none()
    assert summary is not None

@pytest.mark.asyncio
async def test_data_residency_bloqueia_cluster_proibido(session):
    # Register peer in cn-north-1 (prohibited for telemetry)
    peer = FederatedMemoryPeer(
        cluster_id="cluster-cn-1",
        cluster_name="CN Local",
        endpoint_url="http://cn.local",
        trust_level="standard",
        data_residency_region="cn-north-1"
    )
    session.add(peer)
    await session.commit()
    
    policy = SovereigntyPolicy(session)
    authorized, reason = await policy.validate_sync(peer.id, "sensor_telemetry", is_raw=False)
    assert authorized is False
    assert "Data residency violation" in reason

@pytest.mark.asyncio
async def test_revocation_remove_remote_reference(session):
    ref_service = RemoteMemoryReferenceService(session)
    await ref_service.create_reference("tenant-a", {"cluster_id": "c1", "memory_id": "m1"})
    
    # Revoke
    count = await ref_service.revoke_reference("c1", "m1")
    assert count == 1
    
    from sqlalchemy.future import select
    stmt = select(RemoteMemoryReference).where(RemoteMemoryReference.remote_memory_id == "m1")
    ref = (await session.execute(stmt)).scalar_one()
    assert ref.is_valid is False
