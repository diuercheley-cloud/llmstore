import pytest


@pytest.fixture
def service():
    from app.services.operations.correlation.correlation_risk_analysis import (
        OperationalCorrelationRiskAnalysisService,
    )
    return OperationalCorrelationRiskAnalysisService()

def test_classify_operational_risk(service):
    # Low confidence -> Low risk
    assert service.classify_operational_risk(0.9, 0.1) == "low"
    
    # High confidence, various scores
    assert service.classify_operational_risk(0.2, 0.9) == "low"
    assert service.classify_operational_risk(0.5, 0.9) == "medium"
    assert service.classify_operational_risk(0.7, 0.9) == "high"
    assert service.classify_operational_risk(0.9, 0.9) == "critical"

def test_analyze_correlation_risk_high(service):
    correlation = {
        "correlation_score": 0.75,
        "confidence": 0.8,
        "involved_domains": ["billing", "runtime"],
        "correlation_key": "test_key"
    }
    
    result = service.analyze_correlation_risk(correlation)
    
    assert result["risk_level"] == "high"
    assert result["advisory_only"] is True
    assert result["dry_run"] is True
    assert result["suggest_approval_workflow"] is True
    assert "High risk operational pattern" in result["recommendation"]
    assert "assessment_hash" in result

def test_analyze_correlation_risk_low(service):
    correlation = {
        "correlation_score": 0.2,
        "confidence": 0.5,
        "involved_domains": ["auth"],
        "correlation_key": "low_key"
    }
    
    result = service.analyze_correlation_risk(correlation)
    
    assert result["risk_level"] == "low"
    assert result["suggest_approval_workflow"] is False
    assert "Low operational risk" in result["recommendation"]

def test_determinism(service):
    correlation = {
        "correlation_score": 0.9,
        "confidence": 0.95,
        "involved_domains": ["runtime", "infra"],
        "correlation_key": "crit_key"
    }
    
    res1 = service.analyze_correlation_risk(correlation)
    res2 = service.analyze_correlation_risk(correlation)
    
    assert res1 == res2
    assert res1["assessment_hash"] == res2["assessment_hash"]
