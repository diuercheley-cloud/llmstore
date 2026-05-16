import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.client import Client


async def _override_admin():
    return {"role": "super_admin"}


@pytest.mark.asyncio
async def test_compatibility_api_flow(session):
    client = Client(name="phase78-api")
    other = Client(name="phase78-api-other")
    session.add_all([client, other])
    await session.commit()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        created = await ac.post(
            "/admin/operations/compatibility/contracts",
            json={
                "client_id": str(client.id),
                "contract_name": "bundle-compat",
                "contract_scope": "federation_bundle",
                "semantic_version": "1.2.0",
                "schema_version": "1.0.0",
                "feature_flags": ["flag-a"],
                "capabilities": ["read_logs"],
            },
        )
        assert created.status_code == 200
        contract_id = created.json()["contract"]["id"]

        listed = await ac.get(f"/admin/operations/compatibility/contracts?client_id={client.id}")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        detail = await ac.get(f"/admin/operations/compatibility/contracts/{contract_id}?client_id={client.id}")
        blocked_detail = await ac.get(f"/admin/operations/compatibility/contracts/{contract_id}?client_id={other.id}")
        assert detail.status_code == 200
        assert blocked_detail.status_code == 404

        matrix = await ac.post(
            "/admin/operations/compatibility/matrix",
            json={"client_id": str(client.id), "source_version": "1.2.0", "target_version": "1.3.0"},
        )
        assert matrix.status_code == 200
        assert matrix.json()["matrix"]["compatibility_type"] == "backward"

        negotiation = await ac.post(
            "/admin/operations/compatibility/negotiate",
            json={
                "client_id": str(client.id),
                "source_environment": "sovereign-a",
                "target_environment": "sovereign-b",
                "source_version": "1.2.0",
                "target_version": "1.3.0",
                "source_contract_id": contract_id,
            },
        )
        assert negotiation.status_code == 200
        session_id = negotiation.json()["session"]["id"]

        capabilities = await ac.post(
            "/admin/operations/compatibility/capabilities/negotiate",
            json={
                "client_id": str(client.id),
                "negotiation_session_id": session_id,
                "requested_capabilities": ["read_logs", "shell"],
                "available_capabilities": ["read_logs", "shell", "metrics"],
            },
        )
        assert capabilities.status_code == 200
        assert "shell" in capabilities.json()["capability_negotiation"]["denied_capabilities_json"]

        verification = await ac.post(
            f"/admin/operations/compatibility/contracts/{contract_id}/verify",
            json={"client_id": str(client.id)},
        )
        assert verification.status_code == 200
        assert verification.json()["verification"]["replay_safe"] is True

        deprecated = await ac.post(
            f"/admin/operations/compatibility/contracts/{contract_id}/deprecate",
            json={
                "client_id": str(client.id),
                "deprecation_reason": "phase-out",
                "migration_required": True,
                "replacement_contract": "replacement-v2",
                "announce": True,
                "enforce": True,
            },
        )
        assert deprecated.status_code == 200
        assert deprecated.json()["contract"]["compatibility_status"] == "blocked"

        deprecations = await ac.get(f"/admin/operations/compatibility/deprecations?client_id={client.id}")
        assert deprecations.status_code == 200
        assert len(deprecations.json()) == 1

        blocked_negotiation = await ac.post(
            "/admin/operations/compatibility/negotiate",
            json={
                "client_id": str(client.id),
                "source_environment": "sovereign-a",
                "target_environment": "sovereign-b",
                "source_version": "1.2.0",
                "target_version": "1.3.0",
                "source_contract_id": contract_id,
            },
        )
        assert blocked_negotiation.status_code == 409

        receipt = await ac.post(
            f"/admin/operations/compatibility/contracts/{contract_id}/receipt",
            json={"client_id": str(client.id), "receipt_type": "verification_receipt"},
        )
        assert receipt.status_code == 200
        assert receipt.json()["receipt"]["signature_placeholder"].startswith("placeholder-signature:")

        cross_tenant = await ac.post(
            f"/admin/operations/compatibility/contracts/{contract_id}/verify",
            json={"client_id": str(other.id)},
        )
        assert cross_tenant.status_code == 404

    app.dependency_overrides.clear()
