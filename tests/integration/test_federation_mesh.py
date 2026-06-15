import pytest
from app.models.core.federation_mesh import ClusterNode, ConflictRecord, SyncCommit
from app.services.federation.mesh.mesh_sync import MeshSyncService
from sqlalchemy import select


@pytest.mark.asyncio
async def test_mesh_sync_export_import(session):
    node_id = "test-node-01"
    # Seed self node
    session.add(ClusterNode(id=node_id, is_self=True, logical_clock=0))
    await session.commit()

    service = MeshSyncService(session, node_id=node_id)

    # 1. Create a commit
    payload = {"setting": "enabled", "value": 42}
    commit = await service.create_commit(payload=payload)
    await session.commit()

    assert commit.hash is not None
    assert commit.logical_clock == 1

    # 2. Export bundle
    bundle = await service.export_bundle()
    assert bundle["source_node"] == node_id
    assert len(bundle["commits"]) == 1
    assert bundle["commits"][0]["hash"] == commit.hash

    # 3. Simulate import on "another node" (clearing DB or using fresh session)
    # For test simplicity, we just check if import skips existing and handles new
    results = await service.import_bundle(bundle)
    assert results["imported"] == 0  # Already exists in this DB session

    # 4. Dry run
    bundle["commits"][0]["hash"] = "new-hash-sim"
    results_dry = await service.import_bundle(bundle, dry_run=True)
    assert results_dry["imported"] == 1


@pytest.mark.asyncio
async def test_mesh_conflict_detection(session):
    node_id = "node-a"
    session.add(ClusterNode(id=node_id, is_self=True, logical_clock=10))
    await session.commit()

    service = MeshSyncService(session, node_id=node_id)

    # Parent commit
    parent = SyncCommit(hash="parent-123", author_node_id="node-a", payload={}, logical_clock=5)
    session.add(parent)
    # Existing local child
    local_child = SyncCommit(
        hash="local-child",
        parent_hash="parent-123",
        author_node_id="node-a",
        payload={"x": 1},
        logical_clock=6,
    )
    session.add(local_child)
    await session.commit()

    # Bundle with a conflicting commit (same parent, different hash)
    conflicting_bundle = {
        "schema_version": "1.0.0",
        "commits": [
            {
                "hash": "remote-child",
                "parent_hash": "parent-123",
                "author": "node-b",
                "payload": {"x": 2},
                "clock": 6,
                "signature": "sig",
            }
        ],
    }

    results = await service.import_bundle(conflicting_bundle)
    assert results["conflicts"] == 1
    assert results["imported"] == 0

    # Verify conflict record
    stmt = select(ConflictRecord).where(ConflictRecord.commit_hash == "remote-child")
    res = await session.execute(stmt)
    conflict = res.scalar_one()
    assert conflict.peer_node_id == "node-b"


@pytest.mark.asyncio
async def test_mesh_api_endpoints(admin_client, session):
    headers = {"X-Admin-Token": "test-admin-token"}
    node_id = "local-cluster-01"
    session.add(ClusterNode(id=node_id, is_self=True, logical_clock=0))
    await session.commit()

    # Export
    resp = await admin_client.post("/api/admin/federation/sync/export", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["source_node"] == node_id

    # Import (invalid version)
    resp_imp = await admin_client.post(
        "/api/admin/federation/sync/import", json={"schema_version": "0.0.1"}, headers=headers
    )
    assert resp_imp.status_code == 400
    assert "Unsupported bundle schema version" in resp_imp.json()["detail"]
