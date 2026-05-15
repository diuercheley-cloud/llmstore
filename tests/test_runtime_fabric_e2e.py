import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_runtime_fabric_status(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.get("/admin/runtime/fabric", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_runtime_fabric_heartbeat(admin_client: AsyncClient, admin_token_headers: dict):
    payload = {
        "node_id": "test-node-1",
        "status": "healthy",
        "metrics": {"cpu": 10, "mem": 20}
    }
    response = await admin_client.post("/admin/runtime/fabric/heartbeat", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == "test-node-1"
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_runtime_drift_report_and_repair(admin_client: AsyncClient, admin_token_headers: dict):
    # 1. Report drift
    drift_payload = {
        "workflow_id": "test-wf-1",
        "step_index": 5,
        "expected_hash": "abc",
        "actual_hash": "def",
        "drift_details": {"error": "mismatch"}
    }
    response = await admin_client.post("/admin/runtime/drift/report", json=drift_payload, headers=admin_token_headers)
    assert response.status_code == 200
    drift_id = response.json()["id"]

    # 2. List active drifts
    response = await admin_client.get("/admin/runtime/drift", headers=admin_token_headers)
    assert response.status_code == 200
    drifts = response.json()
    assert any(d["id"] == drift_id for d in drifts)

    # 3. Trigger replay repair
    response = await admin_client.post(f"/admin/runtime/replay-repair/{drift_id}", headers=admin_token_headers)
    assert response.status_code == 200
    plan = response.json()
    assert plan["status"] == "completed"

@pytest.mark.asyncio
async def test_runtime_portal_status(admin_client: AsyncClient):
    # Portal status doesn't require admin token (as per router definition)
    response = await admin_client.get("/portal/runtime/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "nodes_online" in data
