import pytest
from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.core.client import Client
from app.utils.crypto_signer import sign_payload
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _override_admin():
    return {"role": "super_admin"}


@pytest.mark.asyncio
async def test_attestation_api_flow(session: AsyncSession):
    client = Client(name="phase76-api")
    other_client = Client(name="phase76-api-other")
    session.add_all([client, other_client])
    await session.commit()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        create = await ac.post(
            "/admin/operations/attestations",
            json={
                "client_id": str(client.id),
                "attestation_type": "workflow",
                "subject_type": "workflow",
                "subject_ref": "wf-1",
                "attestation_scope": "operations",
                "payload": {"step": "execute", "secret_token": "hidden"},
                "signature": sign_payload("workflow"),
            },
        )
        assert create.status_code == 200
        attestation_id = create.json()["attestation"]["id"]

        listed = await ac.get(f"/admin/operations/attestations?client_id={client.id}")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        detail = await ac.get(
            f"/admin/operations/attestations/{attestation_id}?client_id={client.id}"
        )
        assert detail.status_code == 200

        blocked = await ac.get(
            f"/admin/operations/attestations/{attestation_id}?client_id={other_client.id}"
        )
        assert blocked.status_code == 404

        verify = await ac.post(
            f"/admin/operations/attestations/{attestation_id}/verify",
            json={"client_id": str(client.id)},
        )
        assert verify.status_code == 200
        assert verify.json()["verification"]["replay_verified"] is True

        receipt = await ac.post(
            f"/admin/operations/attestations/{attestation_id}/receipt",
            json={"client_id": str(client.id)},
        )
        assert receipt.status_code == 200

        bundle = await ac.post(
            "/admin/operations/attestation-bundles",
            json={
                "client_id": str(client.id),
                "attestation_ids": [attestation_id],
                "target_environment": "airgap-b",
            },
        )
        assert bundle.status_code == 200
        bundle_id = bundle.json()["bundle"]["id"]

        bundle_verify = await ac.post(
            f"/admin/operations/attestation-bundles/{bundle_id}/verify",
            json={"client_id": str(client.id)},
        )
        assert bundle_verify.status_code == 200

        imported = await ac.post(
            "/admin/operations/attestation-bundles/import",
            json={
                "client_id": str(client.id),
                "bundle_payload": bundle.json()["payload"],
            },
        )
        assert imported.status_code == 200

        chain = await ac.get(
            f"/admin/operations/attestation-chains/{attestation_id}?client_id={client.id}"
        )
        assert chain.status_code == 200
        assert chain.json()["integrity_valid"] is True

        revoke_missing_reason = await ac.post(
            f"/admin/operations/attestations/{attestation_id}/revoke",
            json={"client_id": str(client.id), "reason": ""},
        )
        assert revoke_missing_reason.status_code == 422

        revoke = await ac.post(
            f"/admin/operations/attestations/{attestation_id}/revoke",
            json={"client_id": str(client.id), "reason": "superseded"},
        )
        assert revoke.status_code == 200
        assert revoke.json()["attestation"]["attestation_status"] == "revoked"

    app.dependency_overrides.clear()
