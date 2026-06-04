import uuid

import pytest
from app.db.session import get_db_session
from app.main import app
from app.models.client import Client
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_probe_cleanup_removes_client(isolated_db_url):
    from app.db.base import Base
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    admin_token = "test-admin-token"
    with pytest.MonkeyPatch().context() as m:
        m.setenv("ADMIN_TOKEN", admin_token)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            # 1. Create client
            resp = await ac.post("/admin/clients", 
                                headers={"X-Admin-Token": admin_token},
                                json={"name": "cleanup-test-client"})
            assert resp.status_code == 201
            client_id = resp.json()["id"]
            
            # 2. Verify it exists in DB
            async with testing_session_local() as session:
                client = await session.get(Client, uuid.UUID(client_id))
                assert client is not None
                assert client.deleted_at is None
            
            # 3. Delete client (as probe cleanup does)
            resp_del = await ac.delete(f"/admin/clients/{client_id}", 
                                      headers={"X-Admin-Token": admin_token})
            assert resp_del.status_code == 204
            
            # 4. Verify it's "deleted" (soft delete in admin.py)
            async with testing_session_local() as session:
                client = await session.get(Client, uuid.UUID(client_id))
                assert client is not None
                assert client.deleted_at is not None

    app.dependency_overrides.clear()
    await engine.dispose()
