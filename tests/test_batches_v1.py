import pytest
import uuid
import httpx
import pytest_asyncio
from app.core.config import get_settings
from app.models.batches import BatchJob, BatchJobItem
from app.models.agents import AgentDefinition

@pytest_asyncio.fixture
async def batches_client(isolated_db_url, fake_redis):
    import os
    os.environ["AGENT_BATCH_API_ENABLED"] = "true"
    os.environ["AGENT_RUNTIME_ENABLED"] = "true"
    
    from app.main import app
    from app.db.session import get_db, get_redis
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.db.base import Base

    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_batch_api_flow(batches_client, session):
    tenant_id = "tenant-batches-1"
    headers = {"X-Tenant-ID": tenant_id}

    # 0. Create an agent to use in the batch
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Batch Agent",
        version="1.0.0",
        owner="batch_test",
        model_id="gpt-4",
        instructions="Test agent",
        tenant_id=tenant_id,
        status="active"
    )
    session.add(agent)
    await session.commit()

    # 1. Create Batch
    batch_data = {
        "endpoint": "/v1/agents/runs",
        "input_data": [
            {"custom_id": "req-1", "agent_id": str(agent.id), "input_text": "hello 1"},
            {"custom_id": "req-2", "agent_id": str(agent.id), "input_text": "hello 2"}
        ]
    }
    response = await batches_client.post("/v1/batches", json=batch_data, headers=headers)
    assert response.status_code == 200, response.text
    batch_id = response.json()["id"]
    assert response.json()["total_counts"] == 2
    
    # 2. Get Batch Status
    response = await batches_client.get(f"/v1/batches/{batch_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] in ["validating", "in_progress", "completed"]
    
    # 3. Get Batch Results
    response = await batches_client.get(f"/v1/batches/{batch_id}/results", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
    assert response.json()["data"][0]["custom_id"] == "req-1"

@pytest.mark.asyncio
async def test_batch_cancel(batches_client, session):
    tenant_id = "tenant-batches-1"
    headers = {"X-Tenant-ID": tenant_id}
    
    # Create batch
    batch_data = {
        "endpoint": "/v1/agents/runs",
        "input_data": [{"custom_id": "req-1", "agent_id": str(uuid.uuid4()), "input_text": "hi"}]
    }
    response = await batches_client.post("/v1/batches", json=batch_data, headers=headers)
    batch_id = response.json()["id"]
    
    # Cancel batch
    response = await batches_client.post(f"/v1/batches/{batch_id}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

@pytest.mark.asyncio
async def test_batch_tenant_isolation(batches_client, session):
    # Create batch in tenant 1
    batch_data = {
        "endpoint": "/v1/agents/runs",
        "input_data": [{"custom_id": "req-1", "agent_id": str(uuid.uuid4()), "input_text": "hi"}]
    }
    response = await batches_client.post("/v1/batches", json=batch_data, headers={"X-Tenant-ID": "tenant-1"})
    batch_id = response.json()["id"]
    
    # Try to access from tenant 2
    response = await batches_client.get(f"/v1/batches/{batch_id}", headers={"X-Tenant-ID": "tenant-2"})
    assert response.status_code == 404
