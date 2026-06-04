import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deep_health_unauthorized(admin_client: AsyncClient):
    # admin_client from conftest doesn't include headers by default
    response = await admin_client.get("/admin/health/deep")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_deep_health_authorized(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    response = await admin_client.get(
        "/admin/health/deep", 
        headers={"X-Admin-Token": token}
    )
    assert response.status_code == 200
    data = response.json()
    
    sections = [
        "api", "postgres", "redis", "queues", 
        "inference_backends", "models", "rag", 
        "tts", "billing", "security", "readiness_score"
    ]
    for section in sections:
        assert section in data, f"Section {section} missing in deep health"
    
    assert data["api"]["status"] == "online"
    assert "uptime_seconds" in data["api"]
    assert "version" in data["api"]
    assert "readiness_score" in data
    assert data["readiness_score"] in ["READY", "DEGRADED", "NOT_READY"]
