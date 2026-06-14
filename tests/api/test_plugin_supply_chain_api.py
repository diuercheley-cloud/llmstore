import pytest
import tempfile
from pathlib import Path
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

from app.api.dependencies import get_current_admin, get_db
from app.main import app
from app.models.core.client import Client
from app.models.operations.plugin_runtime import PluginABIContract
from app.services.operations.plugin_supply_chain.sbom_service import PluginSBOMService
from app.services.operations.plugin_supply_chain.provenance_service import PluginProvenanceService
from app.utils.crypto_signer import sign_payload

async def _override_admin():
    return {"role": "super_admin"}

async def _setup_test_db_records(session):
    client = Client(name="test-client")
    session.add(client)
    await session.flush()
    
    contract = PluginABIContract(
        id=uuid4().hex,
        client_id=client.id,
        plugin_name="test-plugin",
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
    
    provenance_service = PluginProvenanceService()
    provenance = provenance_service.create_provenance_record({
        "client_id": client.id,
        "plugin_contract_id": contract.id,
        "artifact_name": "bundle-art",
        "artifact_version": "1.0.0",
        "provenance_scope": "plugin",
    })
    session.add(provenance)
    await session.commit()
    return client, contract, provenance

@pytest.mark.asyncio
async def test_api_python_plugin_generates_sbom(session):
    client, contract, provenance = await _setup_test_db_records(session)
    
    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pyproject = temp_path / "pyproject.toml"
            pyproject.write_text("[project]\nname=\"py-plug\"\nversion=\"1.1.1\"\ndependencies=[\"fastapi>=0.115.0\"]\n", encoding="utf-8")
            
            service = PluginSBOMService()
            pkg_hash = service.calculate_package_hash(temp_path)
            
            response = await ac.post(
                f"/admin/operations/plugin-supply-chain/provenance/{provenance.id}/sbom",
                json={
                    "client_id": str(client.id),
                    "plugin_path": str(temp_path),
                    "expected_hash": pkg_hash,
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["sbom"]["sbom_format"] == "cyclonedx_json"
            assert data["validation"]["valid"] is True
            assert data["sbom"]["dependency_summary_json"]["metadata"]["component"]["name"] == "py-plug"

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_api_node_plugin_generates_sbom(session):
    client, contract, provenance = await _setup_test_db_records(session)
    
    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            package_json = temp_path / "package.json"
            package_json.write_text('{"name": "node-plug", "version": "1.2.3", "dependencies": {"lodash": "^4.17.21"}}', encoding="utf-8")
            
            service = PluginSBOMService()
            pkg_hash = service.calculate_package_hash(temp_path)
            
            response = await ac.post(
                f"/admin/operations/plugin-supply-chain/provenance/{provenance.id}/sbom",
                json={
                    "client_id": str(client.id),
                    "plugin_path": str(temp_path),
                    "expected_hash": pkg_hash,
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["sbom"]["sbom_format"] == "cyclonedx_json"
            assert data["validation"]["valid"] is True
            assert data["sbom"]["dependency_summary_json"]["metadata"]["component"]["name"] == "node-plug"

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_api_hash_mismatch_fails(session):
    client, contract, provenance = await _setup_test_db_records(session)
    
    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pyproject = temp_path / "pyproject.toml"
            pyproject.write_text("[project]\nname=\"py-plug\"\nversion=\"1.1.1\"\n", encoding="utf-8")
            
            response = await ac.post(
                f"/admin/operations/plugin-supply-chain/provenance/{provenance.id}/sbom",
                json={
                    "client_id": str(client.id),
                    "plugin_path": str(temp_path),
                    "expected_hash": "wrong_expected_hash",
                }
            )
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["sbom_status"] == "unavailable"
            assert "Integrity check failed" in data["detail"]["reason"]

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_api_absence_of_sbom_does_not_silently_pass(session):
    client, contract, provenance = await _setup_test_db_records(session)
    
    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin] = _override_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        # Request with a non-existent plugin_path to trigger unavailable SBOM
        response = await ac.post(
            f"/admin/operations/plugin-supply-chain/provenance/{provenance.id}/sbom",
            json={
                "client_id": str(client.id),
                "plugin_path": "/path/to/nonexistent/directory",
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["sbom_status"] == "unavailable"
        assert "does not exist" in data["detail"]["reason"]

    app.dependency_overrides.clear()
