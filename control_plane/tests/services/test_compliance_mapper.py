import pytest
from app.services.compliance_control_mapper import ComplianceControlMapperService


def test_control_mapping_valid():
    service = ComplianceControlMapperService()
    controls = service.list_controls()
    assert len(controls) > 0
    
    for c in controls:
        service.validate_control(c) # Should not raise

def test_control_missing_owner():
    service = ComplianceControlMapperService()
    invalid_control = {
        "control_id": "ERR-001",
        "framework": "SOC2",
        "evidence_sources": ["log"]
    }
    with pytest.raises(ValueError, match="missing an owner role"):
        service.validate_control(invalid_control)

def test_control_missing_evidence():
    service = ComplianceControlMapperService()
    invalid_control = {
        "control_id": "ERR-002",
        "framework": "SOC2",
        "owner_role": "Admin"
    }
    with pytest.raises(ValueError, match="missing evidence sources"):
        service.validate_control(invalid_control)

def test_control_secret_leak():
    service = ComplianceControlMapperService()
    leaked_control = {
        "control_id": "ERR-003",
        "framework": "SOC2",
        "owner_role": "Admin",
        "evidence_sources": ["log"],
        "description": "This control uses PRIVATE KEY for something"
    }
    with pytest.raises(ValueError, match="contains sensitive info"):
        service.validate_control(leaked_control)
