import pytest
from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.core.client import Client
from httpx import ASGITransport, AsyncClient


async def _override_admin():
    return {"role": "super_admin"}


@pytest.mark.asyncio
async def test_reproducible_build_api_flow(session):
    client = Client(name="phase81-api")
    other = Client(name="phase81-api-other")
    session.add_all([client, other])
    await session.commit()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        created = await ac.post(
            "/admin/operations/reproducible-builds/manifests",
            json={
                "client_id": str(client.id),
                "build_name": "plugin-build",
                "build_scope": "plugin",
                "source_reference": "plugins/example",
                "deterministic_version": "v1",
                "build_environment_hash": "a" * 64,
                "replay_safe": True,
            },
        )
        assert created.status_code == 200
        manifest_id = created.json()["manifest"]["id"]

        listed = await ac.get(f"/admin/operations/reproducible-builds/manifests?client_id={client.id}")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        detail = await ac.get(f"/admin/operations/reproducible-builds/manifests/{manifest_id}?client_id={client.id}")
        blocked_detail = await ac.get(f"/admin/operations/reproducible-builds/manifests/{manifest_id}?client_id={other.id}")
        assert detail.status_code == 200
        assert blocked_detail.status_code == 404

        verified = await ac.post(
            f"/admin/operations/reproducible-builds/manifests/{manifest_id}/verify",
            json={"client_id": str(client.id)},
        )
        assert verified.status_code == 200

        env = await ac.post(
            "/admin/operations/reproducible-builds/environment/validate",
            json={
                "client_id": str(client.id),
                "constraint_name": "offline-default",
                "constraint_scope": "plugin",
                "blocked_markers": [],
            },
        )
        assert env.status_code == 200
        assert env.json()["offline_validation"]["verification_status"] == "passed"

        artifact = await ac.post(
            "/admin/operations/reproducible-builds/artifacts/verify",
            json={
                "client_id": str(client.id),
                "build_manifest_id": manifest_id,
                "artifact_name": "bundle",
                "artifact_version": "1.0.0",
                "artifact_payload": {"files": ["a.py"]},
            },
        )
        assert artifact.status_code == 200
        artifact_id = artifact.json()["artifact_verification"]["id"]

        lineage = await ac.post(
            "/admin/operations/reproducible-builds/lineage/verify",
            json={
                "client_id": str(client.id),
                "build_manifest_id": manifest_id,
                "source_hash": "b" * 64,
                "artifact_hash": artifact.json()["artifact_verification"]["artifact_hash"],
            },
        )
        assert lineage.status_code == 200
        lineage_id = lineage.json()["lineage"]["id"]

        replay = await ac.post(
            "/admin/operations/reproducible-builds/replay/verify",
            json={
                "client_id": str(client.id),
                "build_manifest_id": manifest_id,
                "artifact_verification_id": artifact_id,
                "lineage_id": lineage_id,
            },
        )
        assert replay.status_code == 200
        assert replay.json()["manifest_replay"]["match"] is True

        receipt = await ac.post(
            f"/admin/operations/reproducible-builds/manifests/{manifest_id}/receipt",
            json={"client_id": str(client.id), "receipt_type": "reproducibility_receipt"},
        )
        assert receipt.status_code == 200

        dashboard = await ac.get(f"/admin/operations/reproducible-builds/dashboard?client_id={client.id}")
        assert dashboard.status_code == 200
        assert dashboard.json()["section"] == "Reproducible Build & Artifact Verification Framework"

        cross_tenant = await ac.post(
            f"/admin/operations/reproducible-builds/manifests/{manifest_id}/verify",
            json={"client_id": str(other.id)},
        )
        assert cross_tenant.status_code == 404

    app.dependency_overrides.clear()
