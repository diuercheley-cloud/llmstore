import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_readiness_latest_api(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    response = await admin_client.get(
        "/admin/readiness/latest",
        headers={"X-Admin-Token": token}
    )
    assert response.status_code == 200
    data = response.json()
    if data.get("status") == "not_generated":
        pytest.skip("No readiness report generated yet")
    
    assert "score" in data
    assert "generated_at" in data
    assert "totals" in data
    assert "top_warnings" in data
    assert "top_failures" in data
    assert "report_path" in data

@pytest.mark.asyncio
async def test_admin_security_latest_api(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    response = await admin_client.get(
        "/admin/security/latest",
        headers={"X-Admin-Token": token}
    )
    assert response.status_code == 200
    data = response.json()
    if data.get("status") == "not_generated":
        pytest.skip("No security report generated yet")
    
    assert "score" in data
    assert "generated_at" in data
    assert "totals" in data
    assert "critical_failures" in data
    assert "warnings" in data
    assert "report_path" in data

@pytest.mark.asyncio
async def test_admin_runtime_summary_api(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    response = await admin_client.get(
        "/admin/runtime/summary",
        headers={"X-Admin-Token": token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "health" in data
    assert "ready" in data
    assert "deep_health" in data
    assert "backend_status" in data
    assert "latest_security_score" in data
    assert "latest_readiness_score" in data
