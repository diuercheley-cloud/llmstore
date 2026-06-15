import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_graph(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/ops-center/graph", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_create_snapshot_api(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.post("/admin/ops-center/snapshot", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "immutable_hash" in data


@pytest.mark.asyncio
async def test_get_trust_violations_api(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get(
        "/admin/ops-center/trust-violations", headers=admin_token_headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_integrity_api(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/ops-center/integrity", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "violation_count" in data


@pytest.mark.asyncio
async def test_get_lineage_api(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get(
        "/admin/ops-center/lineage?node_id=missing-node", headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
    assert data["node_id"] == "missing-node"


@pytest.mark.asyncio
async def test_snapshot_export_bundle_api(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.post(
        "/admin/ops-center/snapshot?format=signed_bundle",
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["manifest"]["format"] == "signed_bundle"
    assert data["detached_signature"]


@pytest.mark.asyncio
async def test_get_federation_map_api(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get(
        "/admin/ops-center/federation-map", headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "consistency" in data
