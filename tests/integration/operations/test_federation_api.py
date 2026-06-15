import pytest
from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.core.client import Client
from httpx import ASGITransport, AsyncClient


async def _override_admin():
    return {"role": "super_admin"}


@pytest.mark.asyncio
async def test_federation_api_flow(session):
    client = Client(name="phase77-api")
    other = Client(name="phase77-api-other")
    session.add_all([client, other])
    await session.commit()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        source = await ac.post(
            "/admin/operations/federation/environments",
            json={
                "client_id": str(client.id),
                "environment_name": "source",
                "environment_type": "airgap_node",
                "federation_scope": "ops",
                "trust_level": "trusted",
            },
        )
        target = await ac.post(
            "/admin/operations/federation/environments",
            json={
                "client_id": str(client.id),
                "environment_name": "target",
                "environment_type": "offline_staging",
                "federation_scope": "ops",
                "trust_level": "verified",
            },
        )
        assert source.status_code == 200
        source_id = source.json()["environment"]["id"]
        target_id = target.json()["environment"]["id"]

        list_envs = await ac.get(f"/admin/operations/federation/environments?client_id={client.id}")
        assert list_envs.status_code == 200
        assert len(list_envs.json()) == 2

        sync = await ac.post(
            "/admin/operations/federation/sessions",
            json={
                "client_id": str(client.id),
                "source_environment_id": source_id,
                "target_environment_id": target_id,
            },
        )
        assert sync.status_code == 200
        session_id = sync.json()["session"]["id"]

        detail = await ac.get(
            f"/admin/operations/federation/sessions/{session_id}?client_id={client.id}"
        )
        blocked_detail = await ac.get(
            f"/admin/operations/federation/sessions/{session_id}?client_id={other.id}"
        )
        assert detail.status_code == 200
        assert blocked_detail.status_code == 404

        exported = await ac.post(
            "/admin/operations/federation/bundles/export",
            json={
                "client_id": str(client.id),
                "session_id": session_id,
                "bundle_name": "bundle",
                "bundle_type": "mixed",
                "payload": {"secret_token": "hidden"},
            },
        )
        assert exported.status_code == 200
        bundle_id = exported.json()["bundle"]["id"]

        imported = await ac.post(
            "/admin/operations/federation/bundles/import",
            json={
                "client_id": str(client.id),
                "session_id": session_id,
                "bundle_payload": exported.json()["payload"],
            },
        )
        assert imported.status_code == 200

        verified = await ac.post(
            f"/admin/operations/federation/bundles/{bundle_id}/verify",
            json={"client_id": str(client.id)},
        )
        assert verified.status_code == 200
        assert verified.json()["verification"]["offline_verified"] is True

        negotiated = await ac.post(
            "/admin/operations/federation/trust-negotiate",
            json={
                "client_id": str(client.id),
                "source_environment_id": source_id,
                "target_environment_id": target_id,
            },
        )
        assert negotiated.status_code == 200

        lineage = await ac.get(
            f"/admin/operations/federation/lineage/{bundle_id}?client_id={client.id}"
        )
        assert lineage.status_code == 200

        receipt = await ac.post(
            f"/admin/operations/federation/sessions/{session_id}/receipt",
            json={"client_id": str(client.id)},
        )
        assert receipt.status_code == 200

        cross_tenant_export = await ac.post(
            "/admin/operations/federation/bundles/export",
            json={
                "client_id": str(other.id),
                "session_id": session_id,
                "bundle_name": "bundle",
                "bundle_type": "mixed",
                "payload": {},
            },
        )
        assert cross_tenant_export.status_code == 404

    app.dependency_overrides.clear()
