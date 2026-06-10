import pytest
from app.services.isms_manager import ISMSManagerService


def test_policy_validation():
    service = ISMSManagerService()
    valid_policy = "# Policy\n| **Owner** | Admin |\n| **Review Frequency** | Annual |"
    service.validate_policy(valid_policy) # Should pass
    
    invalid_policy = "# Policy\nNo metadata here"
    with pytest.raises(ValueError, match="missing an owner definition"):
        service.validate_policy(invalid_policy)

def test_risk_validation():
    service = ISMSManagerService()
    valid_risk = {"id": "R1", "treatment_plan": "Do something"}
    service.validate_risk(valid_risk)
    
    invalid_risk = {"id": "R2"}
    with pytest.raises(ValueError, match="missing a treatment plan"):
        service.validate_risk(invalid_risk)

def test_soa_validation():
    service = ISMSManagerService()
    valid_soa = {"code": "A.5.1", "included": True, "justification": "Required"}
    service.validate_soa_entry(valid_soa)
    
    invalid_soa = {"code": "A.5.1", "included": True}
    with pytest.raises(ValueError, match="missing justification"):
        service.validate_soa_entry(invalid_soa)
