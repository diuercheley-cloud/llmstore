import pytest
from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.core.client import Client
from app.models.operations.plugin_runtime import PluginABIContract
from httpx import ASGITransport, AsyncClient


async def _override_admin():
    return {"role": "super_admin"}


@pytest.mark.asyncio
async def test_plugin_supply_chain_api_flow(session):
    client = Client(name="phase80-api")
    other = Client(name="phase80-api-other")
    session.add_all([client, other])
    await session.flush()
    contract = PluginABIContract(
        id="c" * 64,
        client_id=client.id,
        plugin_name="plugin",
        plugin_version="1.0.0",
        abi_version="1.0.0",
        schema_version="1.0.0",
        contract_scope="workflow",
        contract_status="active",
        deterministic_version="v1",
        contract_hash="a" * 64,
        immutable_hash="b" * 64,
    )
    session.add(contract)
    await session.commit()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        created = await ac.post(
            "/admin/operations/plugin-supply-chain/provenance",
            json={
                "client_id": str(client.id),
                "plugin_contract_id": contract.id,
                "artifact_name": "bundle",
                "artifact_version": "1.0.0",
                "provenance_scope": "plugin",
            },
        )
        assert created.status_code == 200
        provenance_id = created.json()["provenance"]["id"]

        listed = await ac.get(f"/admin/operations/plugin-supply-chain/provenance?client_id={client.id}")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        detail = await ac.get(f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}?client_id={client.id}")
        blocked_detail = await ac.get(f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}?client_id={other.id}")
        assert detail.status_code == 200
        assert blocked_detail.status_code == 404

        verified = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/verify",
            json={"client_id": str(client.id)},
        )
        assert verified.status_code == 200

        import tempfile
        from pathlib import Path
        from app.services.operations.plugin_supply_chain.sbom_service import PluginSBOMService
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pyproject_file = temp_path / "pyproject.toml"
            pyproject_file.write_text(
                "[project]\nname = \"test-plugin\"\nversion = \"1.0.0\"\ndependencies = [\"requests>=2.20.0\"]\nlicense = \"MIT\"\n",
                encoding="utf-8"
            )
            
            service = PluginSBOMService()
            pkg_hash = service.calculate_package_hash(temp_path)
            
            sbom = await ac.post(
                f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/sbom",
                json={
                    "client_id": str(client.id),
                    "plugin_path": str(temp_path),
                    "expected_hash": pkg_hash,
                },
            )
            assert sbom.status_code == 200
            assert sbom.json()["validation"]["signature_only"] is True


        verification = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/dependency-verify",
            json={
                "client_id": str(client.id),
                "dependency_summary_json": {"dependency_classes": ["network_loaders"]},
            },
        )
        assert verification.status_code == 200
        assert verification.json()["verification"]["verification_status"] == "blocked"

        lineage = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/lineage",
            json={"client_id": str(client.id), "parent_artifact_hash": "f" * 64},
        )
        assert lineage.status_code == 200
        assert lineage.json()["verification"]["verified"] is True

        replay = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/replay-verify",
            json={"client_id": str(client.id)},
        )
        assert replay.status_code == 200
        assert replay.json()["replay_verification"]["match"] is True

        signature = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/sign-placeholder",
            json={"client_id": str(client.id)},
        )
        assert signature.status_code == 200
        sig = signature.json()["signature"]["signature"]
        assert isinstance(sig, str) and len(sig) > 0

        receipt = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/receipt",
            json={"client_id": str(client.id)},
        )
        assert receipt.status_code == 200

        dashboard = await ac.get(f"/admin/operations/plugin-supply-chain/dashboard?client_id={client.id}")
        assert dashboard.status_code == 200
        assert dashboard.json()["section"] == "Plugin Supply-Chain Provenance & SBOM Placeholder Framework"

        cross_tenant = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance_id}/replay-verify",
            json={"client_id": str(other.id)},
        )
        assert cross_tenant.status_code == 404

    app.dependency_overrides.clear()
