import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import engine
from app.services.agents.agent_api_facade import sanitize_payload
from httpx import AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def setup_agent_db(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def test_client_id(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Agents Admin Test Client", "rate_limit_per_minute": 10},
    )
    return resp.json()["id"]


@pytest_asyncio.fixture
async def client_api_key(admin_client: AsyncClient, admin_token_headers, test_client_id):
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": test_client_id, "name": "Agents Admin Test Key"},
    )
    return create_resp.json()["api_key"]


@pytest_asyncio.fixture
def client_auth_headers(client_api_key):
    return {"Authorization": f"Bearer {client_api_key}"}


def test_sanitize_payload():
    payload = {
        "prompt": "super secret instruction",
        "nested": {"api-key": "xyz123", "safe_field": "hello"},
        "list_field": [{"password": "secret_password", "ok": True}],
    }
    sanitized = sanitize_payload(payload)
    assert sanitized["prompt"] == "[REDACTED]"
    assert sanitized["nested"]["api-key"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == "hello"
    assert sanitized["list_field"][0]["password"] == "[REDACTED]"
    assert sanitized["list_field"][0]["ok"] is True


@pytest.mark.asyncio
async def test_admin_deprecation_and_auth(
    admin_client: AsyncClient, admin_token_headers, client_auth_headers
):
    # Call with public client key -> should be rejected with 401 or 403 (admin only)
    dummy_id = uuid.uuid4()
    resp_client = await admin_client.get(f"/agents/runs/{dummy_id}", headers=client_auth_headers)
    assert resp_client.status_code in [401, 403]

    # Call with admin token -> should pass authorization (even if it returns 404 for non-existent run)
    # and return Deprecation: true header
    resp_admin = await admin_client.get(f"/agents/runs/{dummy_id}", headers=admin_token_headers)
    assert resp_admin.headers.get("Deprecation") == "true"
    assert resp_admin.status_code == 404


@pytest.mark.asyncio
async def test_list_runs_admin(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.get("/agents/runs", headers=admin_token_headers)
    assert resp.status_code == 200
    assert resp.headers.get("Deprecation") == "true"
    assert isinstance(resp.json(), list)
