import os
import tempfile
from pathlib import Path
import pytest
import uuid

from app.models.operations.plugin_supply_chain import PluginProvenanceRecord
from app.services.operations.plugin_supply_chain.sbom_service import (
    PluginSBOMService,
    SBOMGenerationError,
)
from app.utils.crypto_signer import sign_payload

def _mock_provenance():
    return PluginProvenanceRecord(
        id="mock-provenance-id",
        client_id=uuid.uuid4(),
        plugin_contract_id="contract-id",
        artifact_name="test-plugin",
        artifact_version="1.0.0",
        provenance_scope="plugin",
        provenance_status="proposed",
        provenance_hash="h" * 64,
        replay_safe=True,
        immutable_hash="i" * 64,
    )

def test_python_plugin_generates_sbom():
    service = PluginSBOMService()
    provenance = _mock_provenance()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_path = Path(temp_dir)
        # Create pyproject.toml
        pyproject = plugin_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = \"my-python-plugin\"\nversion = \"1.2.3\"\ndependencies = [\"requests>=2.25.0\"]\nlicense = \"MIT\"\n",
            encoding="utf-8"
        )
        
        # Calculate real hash
        real_hash = service.calculate_package_hash(plugin_path)
        assert len(real_hash) == 64
        
        # Generate SBOM
        sbom_record = service.generate_sbom(
            provenance_record=provenance,
            plugin_path=plugin_path,
            expected_hash=real_hash,
        )
        
        assert sbom_record.sbom_format == "cyclonedx_json"
        sbom = sbom_record.dependency_summary_json
        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["metadata"]["component"]["name"] == "my-python-plugin"
        assert sbom["metadata"]["component"]["version"] == "1.2.3"
        assert sbom["metadata"]["component"]["hashes"][0]["content"] == real_hash
        assert sbom["metadata"]["component"]["licenses"][0]["license"]["id"] == "MIT"
        
        assert len(sbom["components"]) == 1
        assert sbom["components"][0]["name"] == "requests"
        assert sbom["components"][0]["version"] == "2.25.0"
        
        # Validate SBOM
        validation = service.validate_sbom(sbom_record, expected_hash=real_hash)
        assert validation["valid"] is True

def test_node_plugin_generates_sbom():
    service = PluginSBOMService()
    provenance = _mock_provenance()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_path = Path(temp_dir)
        # Create package.json
        package_json = plugin_path / "package.json"
        package_json.write_text(
            '{"name": "my-node-plugin", "version": "2.0.0", "dependencies": {"express": "^4.17.1"}, "license": "Apache-2.0"}',
            encoding="utf-8"
        )
        
        # Create package-lock.json
        package_lock = plugin_path / "package-lock.json"
        package_lock.write_text(
            '{"name": "my-node-plugin", "version": "2.0.0", "lockfileVersion": 2, "packages": {"node_modules/express": {"version": "4.17.1"}}}',
            encoding="utf-8"
        )
        
        # Calculate real hash
        real_hash = service.calculate_package_hash(plugin_path)
        
        # Generate SBOM
        sbom_record = service.generate_sbom(
            provenance_record=provenance,
            plugin_path=plugin_path,
            expected_hash=real_hash,
        )
        
        assert sbom_record.sbom_format == "cyclonedx_json"
        sbom = sbom_record.dependency_summary_json
        assert sbom["metadata"]["component"]["name"] == "my-node-plugin"
        assert sbom["metadata"]["component"]["version"] == "2.0.0"
        assert sbom["metadata"]["component"]["licenses"][0]["license"]["id"] == "Apache-2.0"
        
        deps = {comp["name"]: comp["version"] for comp in sbom["components"]}
        assert "express" in deps
        assert deps["express"] == "4.17.1"

def test_hash_mismatch_fails():
    service = PluginSBOMService()
    provenance = _mock_provenance()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_path = Path(temp_dir)
        pyproject = plugin_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"pkg\"\nversion = \"1.0.0\"\n", encoding="utf-8")
        
        bad_hash = "a" * 64
        with pytest.raises(SBOMGenerationError, match="Integrity check failed"):
            service.generate_sbom(
                provenance_record=provenance,
                plugin_path=plugin_path,
                expected_hash=bad_hash,
            )

def test_unexpected_critical_file_fails():
    service = PluginSBOMService()
    provenance = _mock_provenance()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_path = Path(temp_dir)
        pyproject = plugin_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"pkg\"\nversion = \"1.0.0\"\n", encoding="utf-8")
        
        # Create a critical unexpected file (.env)
        env_file = plugin_path / ".env"
        env_file.write_text("SECRET_KEY=12345", encoding="utf-8")
        
        with pytest.raises(SBOMGenerationError, match="Critical unexpected file found"):
            service.generate_sbom(
                provenance_record=provenance,
                plugin_path=plugin_path,
            )

def test_signature_validation():
    service = PluginSBOMService()
    provenance = _mock_provenance()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_path = Path(temp_dir)
        pyproject = plugin_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"pkg\"\nversion = \"1.0.0\"\ndependencies = []\n", encoding="utf-8")
        
        real_hash = service.calculate_package_hash(plugin_path)
        valid_signature = sign_payload(real_hash)
        
        # Valid signature should pass
        sbom_record = service.generate_sbom(
            provenance_record=provenance,
            plugin_path=plugin_path,
            signature=valid_signature,
        )
        assert sbom_record.sbom_format == "cyclonedx_json"
        
        # Invalid signature should fail
        with pytest.raises(SBOMGenerationError, match="signature verification failed"):
            service.generate_sbom(
                provenance_record=provenance,
                plugin_path=plugin_path,
                signature="invalid_signature_hex",
            )
