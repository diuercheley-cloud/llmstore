import os

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.base import Base
from app.models.admin_rbac import AdminAuditEvent, AdminPermission, AdminRoleModel, AdminUser
from app.services.admin_rbac import ensure_admin_rbac_seed


@pytest_asyncio.fixture
async def rbac_env(isolated_db_url, fake_redis, monkeypatch):
    monkeypatch.setenv("RBAC_ADMIN_ENABLED", "true")
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")

    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.main import app
    from app.db.session import get_db_session, get_redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session_local() as session:
        await ensure_admin_rbac_seed(session)
        await session.commit()

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        yield {"client": client, "sessionmaker": testing_session_local}

    app.dependency_overrides.clear()
    await engine.dispose()
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def legacy_admin_env(isolated_db_url, fake_redis, monkeypatch):
    monkeypatch.setenv("RBAC_ADMIN_ENABLED", "false")
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")

    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.main import app
    from app.db.session import get_db_session, get_redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()
    get_settings.cache_clear()


async def _create_admin_user(client: httpx.AsyncClient, payload: dict) -> dict:
    response = await client.post(
        "/admin/rbac/users",
        json=payload,
        headers={"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_rbac_user_without_permission_gets_403(rbac_env):
    client = rbac_env["client"]
    created = await _create_admin_user(
        client,
        {
            "username": "security-auditor",
            "display_name": "Security Auditor",
            "role_names": ["security_auditor"],
        },
    )

    response = await client.get(
        "/admin/clients",
        headers={"X-Admin-Token": created["admin_token"]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rbac_user_with_permission_can_access(rbac_env):
    client = rbac_env["client"]
    created = await _create_admin_user(
        client,
        {
            "username": "readonly-admin",
            "display_name": "Readonly Admin",
            "role_names": ["read_only"],
        },
    )

    response = await client.get(
        "/admin/clients",
        headers={"X-Admin-Token": created["admin_token"]},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_superadmin_accesses_everything_when_rbac_enabled(rbac_env):
    client = rbac_env["client"]
    response = await client.post(
        "/admin/clients",
        json={"name": "rbac-super-client"},
        headers={"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")},
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_rbac_disabled_preserves_legacy_admin_token_flow(legacy_admin_env):
    response = await legacy_admin_env.get(
        "/admin/clients",
        headers={"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_audit_events_are_recorded(rbac_env):
    client = rbac_env["client"]
    sessionmaker = rbac_env["sessionmaker"]

    created = await _create_admin_user(
        client,
        {
            "username": "audit-user",
            "display_name": "Audit User",
            "role_names": ["security_auditor"],
        },
    )
    denied = await client.get("/admin/clients", headers={"X-Admin-Token": created["admin_token"]})
    assert denied.status_code == 403

    async with sessionmaker() as session:
        result = await session.execute(select(AdminAuditEvent.event_type))
        event_types = [row[0] for row in result.all()]

    assert "admin.auth.success" in event_types
    assert "admin.user.created" in event_types
    assert "admin.permission.denied" in event_types


@pytest.mark.asyncio
async def test_admin_rbac_seed_is_idempotent(session):
    await ensure_admin_rbac_seed(session)
    await session.commit()
    counts_first = {
        "users": await session.scalar(select(func.count()).select_from(AdminUser)),
        "roles": await session.scalar(select(func.count()).select_from(AdminRoleModel)),
        "permissions": await session.scalar(select(func.count()).select_from(AdminPermission)),
    }

    await ensure_admin_rbac_seed(session)
    await session.commit()
    counts_second = {
        "users": await session.scalar(select(func.count()).select_from(AdminUser)),
        "roles": await session.scalar(select(func.count()).select_from(AdminRoleModel)),
        "permissions": await session.scalar(select(func.count()).select_from(AdminPermission)),
    }

    assert counts_first == counts_second
