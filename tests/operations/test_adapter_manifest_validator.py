import pytest
from app.services.operations.adapter_sandbox.manifest_validator import AdapterManifestValidator

def test_manifest_validation_valid():
    validator = AdapterManifestValidator()
    manifest = {
        "network_access_allowed": False,
        "subprocess_allowed": False,
        "external_system_access_allowed": False,
        "sandbox_required": True,
        "dry_run_default": True,
        "capabilities_json": {"allowed": ["restart"]}
    }
    res = validator.validate_manifest(manifest)
    assert res["is_valid"] is True

def test_manifest_validation_invalid_network():
    validator = AdapterManifestValidator()
    manifest = {
        "network_access_allowed": True,
        "sandbox_required": True,
        "dry_run_default": True
    }
    res = validator.validate_manifest(manifest)
    assert res["is_valid"] is False
    assert "network_access_allowed" in res["errors"][0]

def test_manifest_validation_forbidden_capability():
    validator = AdapterManifestValidator()
    manifest = {
        "network_access_allowed": False,
        "subprocess_allowed": False,
        "external_system_access_allowed": False,
        "sandbox_required": True,
        "dry_run_default": True,
        "capabilities_json": {"allowed": ["shell"]}
    }
    res = validator.validate_manifest(manifest)
    assert res["is_valid"] is False
    assert "shell" in res["errors"][0]
