import pytest
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../control_plane"))
from app.services.platform.ga_readiness import GAReadinessService

@pytest.fixture
def service():
    # Make sure we use the right config path
    config_path = os.path.join(os.path.dirname(__file__), "../../config/ga-readiness-rules.yaml")
    return GAReadinessService(config_path=config_path)

def get_perfect_state():
    return {
        "readiness_passing": True,
        "release_gate_passing": True,
        "no_orphaned_flags": True,
        "no_orphaned_apis": True,
        "eval_pass_rate": 0.99,
        "slo_stability_required": True,
        "incident_recovery_tested": True,
        "operational_playbooks_present": True,
        "observability_dashboards_provisioned": True,
        "promotion_gates_enabled": True,
        "security_warnings_classified": True,
        "tenant_isolation_validated": True
    }

def test_perfect_state_is_ga_ready(service):
    state = get_perfect_state()
    result = service.evaluate_readiness(state)
    assert result["maturity_level"] == "ga_ready"
    assert result["score"] == 12

def test_missing_playbook_reduces_maturity(service):
    state = get_perfect_state()
    state["operational_playbooks_present"] = False
    result = service.evaluate_readiness(state)
    
    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert "failed" in result["details"]["operational_playbooks_present"]

def test_orphaned_flags_reduces_maturity(service):
    state = get_perfect_state()
    state["no_orphaned_flags"] = False
    result = service.evaluate_readiness(state)
    
    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert "failed" in result["details"]["no_orphaned_flags"]

def test_failed_evals_reduces_maturity(service):
    state = get_perfect_state()
    state["eval_pass_rate"] = 0.80  # Below 0.95 threshold
    result = service.evaluate_readiness(state)
    
    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert "failed" in result["details"]["eval_pass_rate"]

def test_slo_instability_reduces_maturity(service):
    state = get_perfect_state()
    state["slo_stability_required"] = False
    result = service.evaluate_readiness(state)
    
    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert "failed" in result["details"]["slo_stability"]

def test_multiple_failures_reduce_to_pilot_or_beta(service):
    state = get_perfect_state()
    state["slo_stability_required"] = False
    state["eval_pass_rate"] = 0.80
    state["no_orphaned_flags"] = False
    state["operational_playbooks_present"] = False
    
    result = service.evaluate_readiness(state)
    # Score drops by 4 -> 8. Pilot ready threshold is 8.
    assert result["maturity_level"] == "pilot_ready"
    assert result["score"] == 8

def test_report_generation(service, tmpdir):
    state = get_perfect_state()
    report_path = os.path.join(tmpdir, "ga-readiness.md")
    service.generate_report(state, filepath=report_path)
    
    assert os.path.exists(report_path)
    with open(report_path, "r") as f:
        content = f.read()
        assert "GA_READY" in content
        assert "12 / 12" in content
