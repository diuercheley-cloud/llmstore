import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.services.routing.commercial_cluster_registry import register_cluster

@pytest.fixture
def admin_token():
    return os.environ.get("ADMIN_TOKEN", "test-admin-token")

@pytest.mark.asyncio
async def test_global_router_overview_empty(admin_client: AsyncClient, admin_token: str):
    response = await admin_client.get(
        "/admin/routing/global-router/overview",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "mode" in data
    assert "clusters" in data

@pytest.mark.asyncio
async def test_global_router_ranking(session: AsyncSession, admin_client: AsyncClient, admin_token: str):
    # Register some clusters
    await register_cluster(session, cluster_id="cluster-a", region="us-east", status="active", priority=100)
    await register_cluster(session, cluster_id="cluster-b", region="us-west", status="active", priority=200)
    await session.commit()
    
    response = await admin_client.get(
        "/admin/routing/global-router/overview",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["clusters"]) >= 2
    # Cluster A should have higher score than B because of priority
    scores = {c["cluster_id"]: c["score"] for c in data["clusters"]}
    assert scores["cluster-a"] > scores["cluster-b"]

@pytest.mark.asyncio
async def test_global_router_offline_rejected(session: AsyncSession, admin_client: AsyncClient, admin_token: str):
    await register_cluster(session, cluster_id="cluster-offline", status="offline")
    await session.commit()
    
    response = await admin_client.get(
        "/admin/routing/global-router/overview",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    rejected_ids = [c["cluster_id"] for c in data["rejected"]]
    assert "cluster-offline" in rejected_ids

@pytest.mark.asyncio
async def test_global_router_simulate(admin_client: AsyncClient, admin_token: str):
    payload = {
        "tenant_id": "tenant-test",
        "region_preference": "us-east",
    }
    response = await admin_client.post(
        "/admin/routing/global-router/simulate",
        headers={"X-Admin-Token": admin_token},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommended_cluster" in data
    assert data["simulation_params"]["tenant_id"] == "tenant-test"

@pytest.mark.asyncio
async def test_global_router_export(admin_client: AsyncClient, admin_token: str):
    # JSON
    response = await admin_client.get(
        "/admin/routing/global-router/export?format=json",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    assert response.json()["clusters"] is not None
    
    # CSV
    response = await admin_client.get(
        "/admin/routing/global-router/export?format=csv",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    
    # HTML
    response = await admin_client.get(
        "/admin/routing/global-router/export?format=html",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_global_router_auth_required(admin_client: AsyncClient):
    # We need to clear dependency overrides or use a client without headers
    # admin_client fixture doesn't automatically add headers, so this should work
    response = await admin_client.get("/admin/routing/global-router/overview")
    assert response.status_code == 401
