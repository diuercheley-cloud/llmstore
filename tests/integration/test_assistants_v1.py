import httpx
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def assistants_client(isolated_db_url, fake_redis):
    # Set feature flag BEFORE importing app
    import os

    os.environ["AGENT_ASSISTANTS_API_ENABLED"] = "true"
    os.environ["AGENT_RUNTIME_ENABLED"] = "true"

    from app.api.assistants_v1 import router as assistants_v1_router
    from app.db.base import Base
    from app.db.session import get_db, get_redis
    from app.main import app

    # Ensure router is included even if app was initialized without the flag
    route_exists = any(
        getattr(route, "path", "").startswith("/v1/assistants") for route in app.routes
    )
    if not route_exists:
        app.include_router(assistants_v1_router)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_assistants_api_flow(assistants_client, session):
    tenant_id = "tenant-assistants-1"
    headers = {"X-Tenant-ID": tenant_id}

    # 1. Create Assistant
    assistant_data = {
        "name": "Math Tutor",
        "model": "gpt-4",
        "instructions": "You are a math tutor.",
    }
    response = await assistants_client.post("/v1/assistants", json=assistant_data, headers=headers)
    assert response.status_code == 200, response.text
    assistant_id = response.json()["id"]

    # 2. Create Thread
    response = await assistants_client.post("/v1/threads", headers=headers)
    assert response.status_code == 200, response.text
    thread_id = response.json()["id"]

    # 3. Add Message
    msg_data = {"role": "user", "content": "What is 2+2?"}
    response = await assistants_client.post(
        f"/v1/threads/{thread_id}/messages", json=msg_data, headers=headers
    )
    assert response.status_code == 200, response.text

    # 4. Create Run
    run_data = {"assistant_id": assistant_id}
    response = await assistants_client.post(
        f"/v1/threads/{thread_id}/runs", json=run_data, headers=headers
    )
    assert response.status_code == 200, response.text
    run_id = response.json()["id"]

    # 5. Check Run Status
    response = await assistants_client.get(
        f"/v1/threads/{thread_id}/runs/{run_id}", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] in ["queued", "running", "completed"]


@pytest.mark.asyncio
async def test_assistants_tenant_isolation(assistants_client, session):
    # Create thread in tenant 1
    response = await assistants_client.post("/v1/threads", headers={"X-Tenant-ID": "tenant-1"})
    assert response.status_code == 200
    thread_id = response.json()["id"]

    # Try to access from tenant 2
    response = await assistants_client.post(
        f"/v1/threads/{thread_id}/messages",
        json={"role": "user", "content": "hi"},
        headers={"X-Tenant-ID": "tenant-2"},
    )
    assert response.status_code == 404
