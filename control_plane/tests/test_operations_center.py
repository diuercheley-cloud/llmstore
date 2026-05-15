import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_ops_center_overview(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/ops/overview", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_tenants" in data

@pytest.mark.asyncio
async def test_ops_center_governance(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/ops/governance", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "policies_active" in data

@pytest.mark.asyncio
async def test_ops_center_risk(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/ops/risk", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "overall_risk" in data

@pytest.mark.asyncio
async def test_ops_center_workflows(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/ops/workflows", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "dags_active" in data

@pytest.mark.asyncio
async def test_ops_center_receipts(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/ops/receipts", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_receipts" in data

@pytest.mark.asyncio
async def test_ops_center_compliance(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/ops/compliance", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "frameworks_active" in data

@pytest.mark.asyncio
async def test_ops_center_attestation(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/ops/attestation", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "trust_chains" in data
