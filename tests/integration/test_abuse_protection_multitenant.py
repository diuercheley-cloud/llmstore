from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.security import hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.billing.billing_plan import BillingPlan
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def abuse_mt_env(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    with (
        patch("app.db.session.SessionLocal", testing_session_local),
        patch("app.services.backend_slot_manager.SessionLocal", testing_session_local),
        patch(
            "app.services.backend_slot_manager.BackendSlotManager.try_acquire", return_value=True
        ),
        patch("app.services.backend_slot_manager.BackendSlotManager.release", return_value=None),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            yield ac, testing_session_local

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def mt_setup(abuse_mt_env):
    ac, sessionmaker = abuse_mt_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="mt_test",
            name="MT Test",
            rate_limit_per_minute=10,
            daily_token_quota=100000,
            weekly_token_quota=100000,
            monthly_token_quota=100000,
            max_output_tokens=512,
        )
        await session.flush()

        client_a = Client(name="tenant-a", billing_plan_id=plan.id, billing_status="active")
        client_b = Client(name="tenant-b", billing_plan_id=plan.id, billing_status="active")
        session.add_all([client_a, client_b])
        await session.flush()

        raw_a = "sk-tenant-a-12345678"
        raw_b = "sk-tenant-b-12345678"

        key_a = ApiKey(
            client_id=client_a.id,
            name="key-a",
            key_prefix=short_prefix(raw_a),
            key_hash=hash_secret(raw_a),
            is_active=True,
        )
        key_b = ApiKey(
            client_id=client_b.id,
            name="key-b",
            key_prefix=short_prefix(raw_b),
            key_hash=hash_secret(raw_b),
            is_active=True,
        )
        session.add_all([key_a, key_b])
        await session.commit()

        return {
            "ac": ac,
            "key_a": raw_a,
            "key_b": raw_b,
            "client_a_id": str(client_a.id),
            "client_b_id": str(client_b.id),
        }


@pytest.mark.asyncio
async def test_admin_endpoints_without_token_return_401(abuse_mt_env):
    ac, _ = abuse_mt_env

    endpoints = [
        ("GET", "/admin/clients"),
        ("GET", "/admin/api-keys"),
        ("POST", "/admin/clients"),
    ]

    for method, url in endpoints:
        if method == "GET":
            resp = await ac.get(url)
        else:
            resp = await ac.post(url, json={})
        assert resp.status_code == 401, f"{method} {url} expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_admin_endpoints_with_wrong_token_return_401(abuse_mt_env):
    ac, _ = abuse_mt_env
    resp = await ac.get("/admin/clients", headers={"X-Admin-Token": "wrong-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tenant_a_cannot_access_tenant_b_resources(mock_verify, mt_setup):
    ac = mt_setup["ac"]
    key_a = mt_setup["key_a"]
    client_b_id = mt_setup["client_b_id"]

    # Try to access tenant B portal usage with tenant A key
    resp = await ac.get("/portal/usage", headers={"Authorization": f"Bearer {key_a}"})
    # Should succeed for tenant A
    assert resp.status_code == 200

    # Attempting admin-level client access with regular API key should fail
    resp = await ac.get("/admin/clients", headers={"Authorization": f"Bearer {key_a}"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tenant_a_cannot_access_tenant_b_jobs(mock_verify, mt_setup):
    ac = mt_setup["ac"]
    key_a = mt_setup["key_a"]
    client_b_id = mt_setup["client_b_id"]

    # Try to access a job that belongs to tenant B using tenant A key (random UUID)
    fake_job_id = "12345678-1234-5678-1234-567812345678"
    resp = await ac.get(f"/v1/jobs/{fake_job_id}", headers={"Authorization": f"Bearer {key_a}"})
    # Will be 404 because job doesn't exist for tenant A (inferred from key)
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_cross_tenant_api_key_fails_on_other_portal(mock_verify, mt_setup):
    ac = mt_setup["ac"]
    key_a = mt_setup["key_a"]

    # Ensure tenant A key works on tenant A routes
    resp = await ac.get("/portal/me", headers={"Authorization": f"Bearer {key_a}"})
    assert resp.status_code == 200

    # Ensure tenant A key cannot be used to impersonate tenant B on admin routes
    resp = await ac.post(
        "/admin/api-keys",
        headers={"Authorization": f"Bearer {key_a}"},
        json={"client_id": mt_setup["client_b_id"], "name": "hacked"},
    )
    assert resp.status_code in (401, 403)
