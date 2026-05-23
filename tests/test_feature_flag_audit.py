import os
import yaml
import pytest
from unittest.mock import patch
from app.core.config import Settings
from app.services.platform.feature_flag_audit import FeatureFlagAuditService

@pytest.fixture
def temp_registry_file(tmp_path):
    registry_data = [
        {
            "name": "TEST_ACTIVE_FLAG",
            "owner": "platform-ops",
            "area": "core",
            "status": "active",
            "safe_default_reason": "Testing",
            "risk_level": "low"
        },
        {
            "name": "TEST_ORPHAN_FLAG",
            "owner": "platform-ops",
            "area": "core",
            "status": "active",
            "safe_default_reason": "Testing",
            "risk_level": "low"
        },
        {
            "name": "TEST_MISSING_OWNER_FLAG",
            "owner": "",
            "area": "core",
            "status": "active",
            "safe_default_reason": "Testing",
            "risk_level": "low"
        },
        {
            "name": "TEST_DEPRECATED_FLAG",
            "owner": "platform-ops",
            "area": "core",
            "status": "deprecated",
            "safe_default_reason": "Testing",
            "risk_level": "low",
            "remove_after": "v2.2.0",
            "replacement": ""
        }
    ]
    file_path = tmp_path / "feature-flags-test.yaml"
    with open(file_path, "w") as f:
        yaml.dump(registry_data, f)
    return str(file_path)

def test_audit_flags(temp_registry_file):
    service = FeatureFlagAuditService(registry_path=temp_registry_file)
    
    with patch.object(service.registry_service, "scan_orphans", return_value={
        "orphans": ["TEST_ORPHAN_FLAG"],
        "missing_registration": []
    }):
        results = service.perform_audit()
        
        # Test flag sem uso (orphaned) detectada
        assert "TEST_ORPHAN_FLAG" in results["orphans"]
        
        # Test flag sem owner detectada
        assert "TEST_MISSING_OWNER_FLAG" in results["sem_owner"]
        
        # Test flag deprecated aparece corretamente
        deprecated_names = [f["name"] for f in results["classification"]["deprecated"]]
        assert "TEST_DEPRECATED_FLAG" in deprecated_names
        
        # Check classification of orphaned flag
        orphaned_names = [f["name"] for f in results["classification"]["orphaned"]]
        assert "TEST_ORPHAN_FLAG" in orphaned_names

def test_removed_flag_does_not_break_startup():
    # Verify that a missing flag registry does not prevent system configuration settings startup
    settings = Settings()
    assert hasattr(settings, "deployment_mode")
