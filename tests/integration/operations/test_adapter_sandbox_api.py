import uuid

import pytest
import pytest_asyncio

# Ensure models are registered
from httpx import AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def ensure_sandbox_tables(admin_client: AsyncClient):
    from app.db.base import Base
    from app.db.session import get_db_session

    async for session in get_db_session():
        engine = session.bind
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        break


@pytest.mark.asyncio
class TestAdapterSandboxAPI:
    async def test_register_manifest_endpoint(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        client_id = str(uuid.uuid4())
        payload = {
            "client_id": client_id,
            "adapter_name": "test_api_adapter",
            "adapter_version": "1.0.0",
            "adapter_type": "simulation",
            "capabilities": ["restart"],
        }
        response = await admin_client.post(
            "/admin/operations/adapter-sandbox/manifests", json=payload, headers=admin_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "manifest" in data
        assert data["manifest"]["adapter_name"] == "test_api_adapter"
        assert "receipt" in data

    async def test_simulate_run_flow(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        # 1. Register manifest
        m_payload = {
            "client_id": client_id,
            "adapter_name": "flow_adapter",
            "adapter_version": "1.0.0",
            "adapter_type": "simulation",
            "capabilities": ["restart"],
        }
        m_resp = await admin_client.post(
            "/admin/operations/adapter-sandbox/manifests",
            json=m_payload,
            headers=admin_token_headers,
        )
        manifest_id = m_resp.json()["manifest"]["id"]

        # 2. Prepare run
        p_payload = {
            "client_id": client_id,
            "manifest_id": manifest_id,
            "sandbox_mode": "simulation",
        }
        p_resp = await admin_client.post(
            "/admin/operations/adapter-sandbox/runs/prepare",
            json=p_payload,
            headers=admin_token_headers,
        )
        run_id = p_resp.json()["id"]

        # 3. Simulate
        s_payload = {
            "client_id": client_id,
            "run_id": run_id,
            "steps": [{"action_type": "restart", "target_domain": "worker"}],
        }
        s_resp = await admin_client.post(
            "/admin/operations/adapter-sandbox/runs/simulate",
            json=s_payload,
            headers=admin_token_headers,
        )
        assert s_resp.status_code == 200
        assert s_resp.json()["run"]["status"] == "simulated"
        assert len(s_resp.json()["results"]) == 1
