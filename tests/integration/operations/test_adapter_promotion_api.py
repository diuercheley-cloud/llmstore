import uuid

import pytest
from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.models.operations.adapter_sandbox import AdapterManifest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestAdapterPromotionAPI:
    async def test_create_workflow_api(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest = AdapterManifest(
            client_id=client_id,
            adapter_name="promo_adapter",
            adapter_version="1.0.0",
            adapter_type="remediation",
            manifest_hash="phash",
            immutable_hash="imm_phash",
            capabilities_json={},
            denied_capabilities_json={},
        )
        session.add(manifest)
        await session.flush()

        entry = SignedAdapterRegistryEntry(
            client_id=client_id,
            adapter_name="promo_adapter",
            adapter_version="1.0.0",
            adapter_type="remediation",
            manifest_id=manifest.id,
            manifest_hash="phash",
            registry_status="approved",
            registry_hash="rhash",
            signature="sig",
            immutable_hash="e_imm",
        )
        session.add(entry)
        await session.commit()

        # Mock admin and db
        async def mock_get_current_admin():
            return type("Admin", (), {"email": "admin@test.com"})()

        app.dependency_overrides[get_current_admin] = mock_get_current_admin
        app.dependency_overrides[get_db] = lambda: session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "client_id": str(client_id),
                "registry_entry_id": str(entry.id),
                "target_stage": "production_eligible",
                "context": {
                    "sandbox_simulation_passed": True,
                    "no_policy_violations": True,
                    "staging_simulation_passed": True,
                    "production_approval_granted": True,
                },
            }
            response = await ac.post("/admin/operations/adapter-promotion/workflows", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["workflow"]["adapter_name"] == "promo_adapter"
        assert all(r["gate_status"] == "passed" for r in data["gate_results"])

        app.dependency_overrides.clear()
