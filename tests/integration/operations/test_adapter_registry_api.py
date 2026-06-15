import uuid

import pytest
from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.operations.adapter_sandbox import AdapterManifest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestAdapterRegistryAPI:
    async def test_register_entry_api(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest = AdapterManifest(
            client_id=client_id,
            adapter_name="api_adapter",
            adapter_version="1.0.0",
            adapter_type="remediation",
            manifest_hash="apihash",
            immutable_hash="imm_apihash",
            sandbox_required=True,
            dry_run_default=True,
            network_access_allowed=False,
            subprocess_allowed=False,
            external_system_access_allowed=False,
            capabilities_json={"requested": []},
            denied_capabilities_json={"denied": []},
        )
        session.add(manifest)
        await session.commit()

        # Mock admin and db
        async def mock_get_current_admin():
            return type("Admin", (), {"email": "admin@test.com"})()

        app.dependency_overrides[get_current_admin] = mock_get_current_admin
        app.dependency_overrides[get_db] = lambda: session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {"client_id": str(client_id), "manifest_id": str(manifest.id)}
            response = await ac.post("/admin/operations/adapter-registry/entries", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["entry"]["adapter_name"] == "api_adapter"
        assert "receipt_id" in data

        app.dependency_overrides.clear()
