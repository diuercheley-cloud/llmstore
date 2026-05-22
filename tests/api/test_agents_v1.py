import pytest
import pytest_asyncio
import uuid
import json
import asyncio
from httpx import AsyncClient
from datetime import datetime, timezone
from app.db.base import Base
from app.db.session import engine

@pytest_asyncio.fixture(autouse=True)
async def setup_agent_db(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    # Force import of all models
    import app.models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest_asyncio.fixture
async def test_client_id(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Agents Test Client", "rate_limit_per_minute": 10}
    )
    return resp.json()["id"]

@pytest_asyncio.fixture
async def client_api_key(admin_client: AsyncClient, admin_token_headers, test_client_id):
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": test_client_id, "name": "Agents API Key"}
    )
    return create_resp.json()["api_key"]

@pytest_asyncio.fixture
def auth_headers(client_api_key):
    return {"Authorization": f"Bearer {client_api_key}"}

@pytest.mark.asyncio
async def test_create_agent_v1(admin_client: AsyncClient, auth_headers):
    agent_data = {
        "name": "V1 Test Agent",
        "version": "1.0.0",
        "instructions": "Be helpful",
        "model_id": "gpt-4",
        "allowed_tools": ["t1"]
    }
    resp = await admin_client.post("/v1/agents", headers=auth_headers, json=agent_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "V1 Test Agent"
    assert "id" in data

@pytest.mark.asyncio
async def test_list_agents_v1(admin_client: AsyncClient, auth_headers):
    # Create one first
    await admin_client.post("/v1/agents", headers=auth_headers, json={
        "name": "Agent A", "version": "1", "instructions": "i", "model_id": "m"
    })
    
    resp = await admin_client.get("/v1/agents", headers=auth_headers)
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 1
    assert any(a["name"] == "Agent A" for a in agents)

@pytest.mark.asyncio
async def test_agent_v1_isolation(admin_client: AsyncClient, admin_token_headers, auth_headers, test_client_id):
    # Create another client
    resp2 = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Other Client", "rate_limit_per_minute": 10}
    )
    client2_id = resp2.json()["id"]
    
    create_resp2 = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client2_id, "name": "Key 2"}
    )
    api_key2 = create_resp2.json()["api_key"]
    auth2 = {"Authorization": f"Bearer {api_key2}"}
    
    # Create agent for client 1
    resp_a = await admin_client.post("/v1/agents", headers=auth_headers, json={
        "name": "Client 1 Agent", "version": "1", "instructions": "i", "model_id": "m"
    })
    agent_id = resp_a.json()["id"]
    
    # Try to access from client 2
    resp_get = await admin_client.get(f"/v1/agents/{agent_id}", headers=auth2)
    assert resp_get.status_code == 404

@pytest.mark.asyncio
async def test_agent_run_v1(admin_client: AsyncClient, auth_headers):
    # Create agent
    resp_a = await admin_client.post("/v1/agents", headers=auth_headers, json={
        "name": "Runner", "version": "1", "instructions": "i", "model_id": "m", "status": "approved"
    })
    agent_id = resp_a.json()["id"]
    
    # Start run
    resp_run = await admin_client.post(f"/v1/agents/{agent_id}/runs", headers=auth_headers, json={"input_text": "hello"})
    assert resp_run.status_code == 200
    run_id = resp_run.json()["id"]
    
    # Check status
    resp_status = await admin_client.get(f"/v1/agents/runs/{run_id}", headers=auth_headers)
    assert resp_status.status_code == 200
    assert resp_status.json()["status"] in ["queued", "running", "completed"]

@pytest.mark.asyncio
async def test_agent_sse_events_v1(admin_client: AsyncClient, auth_headers):
    # Create agent
    resp_a = await admin_client.post("/v1/agents", headers=auth_headers, json={
        "name": "SSE Agent", "version": "1", "instructions": "i", "model_id": "m", "status": "approved"
    })
    agent_id = resp_a.json()["id"]
    
    # Start run
    resp_run = await admin_client.post(f"/v1/agents/{agent_id}/runs", headers=auth_headers, json={"input_text": "hello"})
    assert resp_run.status_code == 200
    run_id = resp_run.json()["id"]
    
    # Use streaming response
    async with admin_client.stream("GET", f"/v1/agents/runs/{run_id}/events", headers=auth_headers) as response:
        assert response.status_code == 200
        # Read some events
        count = 0
        async for line in response.aiter_lines():
            if line:
                count += 1
                if count > 5: break # Don't wait forever
        assert count > 0
