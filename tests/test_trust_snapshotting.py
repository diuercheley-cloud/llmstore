import pytest
from app.services.security.trust_snapshotting import TrustSnapshottingService


@pytest.mark.asyncio
async def test_create_snapshot(session):
    service = TrustSnapshottingService()
    snapshot = await service.create_snapshot(session)
    
    assert snapshot.id is not None
    assert snapshot.immutable_hash is not None
    assert snapshot.snapshot_data is not None
    assert "nodes" in snapshot.snapshot_data
    assert "edges" in snapshot.snapshot_data

@pytest.mark.asyncio
async def test_verify_snapshot(session):
    service = TrustSnapshottingService()
    snapshot = await service.create_snapshot(session)
    
    assert service.verify_snapshot(snapshot) is True
    
    # Tamper with snapshot data
    snapshot.snapshot_data["tampered"] = True
    assert service.verify_snapshot(snapshot) is False


@pytest.mark.asyncio
async def test_export_snapshot_bundle(session):
    service = TrustSnapshottingService()
    snapshot = await service.create_snapshot(session)

    bundle = await service.export_snapshot_bundle(session, snapshot=snapshot, format="offline_audit_package")

    assert bundle["manifest"]["format"] == "offline_audit_package"
    assert bundle["manifest"]["offline_capable"] is True
    assert bundle["manifest_hash"]
    assert bundle["payload"]["snapshot"]["graph_hash"]
