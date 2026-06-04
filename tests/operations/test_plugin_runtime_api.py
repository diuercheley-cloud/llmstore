import pytest
from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.client import Client
from httpx import ASGITransport, AsyncClient


async def _override_admin():
    return {"role": "super_admin"}


@pytest.mark.asyncio
async def test_plugin_runtime_api_flow(session):
    client = Client(name="phase79-api")
    other = Client(name="phase79-api-other")
    session.add_all([client, other])
    await session.commit()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        created = await ac.post(
            "/admin/operations/plugin-runtime/contracts",
            json={
                "client_id": str(client.id),
                "plugin_name": "plugin",
                "plugin_version": "1.0.0",
                "abi_version": "1.0.0",
                "schema_version": "1.0.0",
                "contract_scope": "workflow",
                "contract_status": "active",
            },
        )
        assert created.status_code == 200
        contract_id = created.json()["contract"]["id"]

        listed = await ac.get(f"/admin/operations/plugin-runtime/contracts?client_id={client.id}")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        detail = await ac.get(f"/admin/operations/plugin-runtime/contracts/{contract_id}?client_id={client.id}")
        blocked_detail = await ac.get(f"/admin/operations/plugin-runtime/contracts/{contract_id}?client_id={other.id}")
        assert detail.status_code == 200
        assert blocked_detail.status_code == 404

        capabilities = await ac.post(
            f"/admin/operations/plugin-runtime/contracts/{contract_id}/capabilities",
            json={"client_id": str(client.id), "allowed_capabilities_json": ["read_logs", "network", "dynamic_import"]},
        )
        assert capabilities.status_code == 200
        assert "network" in capabilities.json()["evaluation"]["denied_capabilities"]

        compatibility = await ac.post(
            f"/admin/operations/plugin-runtime/contracts/{contract_id}/compatibility-check",
            json={"client_id": str(client.id), "runtime_version": "2.0.0"},
        )
        assert compatibility.status_code == 200
        assert compatibility.json()["compatibility"]["compatibility_status"] == "incompatible"

        load_plans = await ac.post(
            "/admin/operations/plugin-runtime/load-plans",
            json={"client_id": str(client.id), "contract_ids": [contract_id]},
        )
        assert load_plans.status_code == 200
        load_plan_id = load_plans.json()["load_plans"][0]["id"]
        assert load_plans.json()["load_plans"][0]["load_status"] == "blocked"

        simulated = await ac.post(
            f"/admin/operations/plugin-runtime/load-plans/{load_plan_id}/simulate",
            json={"client_id": str(client.id)},
        )
        assert simulated.status_code == 200
        assert simulated.json()["simulation"]["executed_plugins"] == 0

        lifecycle = await ac.post(
            f"/admin/operations/plugin-runtime/contracts/{contract_id}/lifecycle",
            json={"client_id": str(client.id), "lifecycle_event_type": "placeholder_certified", "reason": "doc only"},
        )
        assert lifecycle.status_code == 200

        replay = await ac.post(
            f"/admin/operations/plugin-runtime/contracts/{contract_id}/replay-verify",
            json={"client_id": str(client.id)},
        )
        assert replay.status_code == 200
        assert replay.json()["replay_verification"]["replay_safe"] is True

        federation = await ac.post(
            f"/admin/operations/plugin-runtime/contracts/{contract_id}/federation-compatibility",
            json={"client_id": str(client.id), "source_environment": "a", "target_environment": "b"},
        )
        assert federation.status_code == 200

        receipt = await ac.post(
            f"/admin/operations/plugin-runtime/contracts/{contract_id}/receipt",
            json={"client_id": str(client.id), "receipt_type": "abi_contract_receipt"},
        )
        assert receipt.status_code == 200
        assert receipt.json()["receipt"]["signature"].startswith("placeholder-signature:")

        cross_tenant = await ac.post(
            f"/admin/operations/plugin-runtime/contracts/{contract_id}/replay-verify",
            json={"client_id": str(other.id)},
        )
        assert cross_tenant.status_code == 404

    app.dependency_overrides.clear()
