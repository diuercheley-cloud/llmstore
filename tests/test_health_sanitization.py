import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_status_sanitization(admin_client: AsyncClient):
    response = await admin_client.get("/status")
    assert response.status_code == 200
    content = response.text.lower()
    
    # Common sensitive terms
    forbidden = ["password", "database_url", "redis_url", "admin_token"]
    for word in forbidden:
        # Check if the word appears followed by a value that isn't masked
        # This is a bit simplified but effective for basic leak detection
        assert f'"{word}":' not in content or "masked" in content

@pytest.mark.asyncio
async def test_deep_health_sanitization(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    response = await admin_client.get(
        "/admin/health/deep", 
        headers={"X-Admin-Token": token}
    )
    assert response.status_code == 200
    content = response.text.lower()
    
    # We should never see the real database password or admin token
    # These are set in conftest.py
    assert "llm_gateway_dev_password" not in content
    assert "test-admin-token" not in content
    
    # Also check for standard patterns
    assert "sk-" not in content # OpenAI keys usually start with sk-
