import os
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../control_plane"))
from app.services.platform.ga_readiness import GAReadinessService


@pytest.fixture
def service():
    config_path = os.path.join(os.path.dirname(__file__), "../../config/ga-readiness-rules.yaml")
    return GAReadinessService(config_path=config_path)


def get_perfect_state():
    return {
        "operational_readiness_passed": True,
        "agentic_readiness_passed": True,
        "release_gate_passed": True,
        "platform_freeze_passed": True,
        "surface_audit_clean": True,
        "no_orphaned_flags": True,
        "security_warnings_classified": True,
        "eval_gate_enforced": True,
        "provider_validation_recent": True,
        "no_silent_mock_in_production": True,
        "no_silent_task_simulation": True,
        "tenant_isolation_validated": True,
        "_reasons": {
            "provider_validation_recent": "validated providers: local_gateway",
        },
    }


def test_all_12_criteria_pass_is_ga_ready(service):
    result = service.evaluate_readiness(get_perfect_state())
    assert result["maturity_level"] == "ga_ready"
    assert result["score"] == 12
    assert result["total_possible"] == 12


def test_surface_audit_dirty_blocks_ga(service):
    state = get_perfect_state()
    state["surface_audit_clean"] = False
    state["_reasons"]["surface_audit_clean"] = "surface audit is dirty: 6 unregistered API routes"

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["surface_audit_clean"] == "failed: surface audit is dirty: 6 unregistered API routes"


def test_provider_validation_missing_blocks_ga(service):
    state = get_perfect_state()
    state["provider_validation_recent"] = False
    state["_reasons"]["provider_validation_recent"] = (
        "provider validation latest/results.json has no non-mock provider with a passing basic_model_call"
    )

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["provider_validation_recent"] == (
        "failed: provider validation latest/results.json has no non-mock provider with a passing basic_model_call"
    )


def test_silent_mock_blocks_ga(service):
    state = get_perfect_state()
    state["no_silent_mock_in_production"] = False
    state["_reasons"]["no_silent_mock_in_production"] = "mock LLM is explicitly allowed in production-capable mode"

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["no_silent_mock_in_production"] == (
        "failed: mock LLM is explicitly allowed in production-capable mode"
    )


def test_task_simulation_blocks_ga(service):
    state = get_perfect_state()
    state["no_silent_task_simulation"] = False
    state["_reasons"]["no_silent_task_simulation"] = (
        "task_engine.py still contains AGENT_TASK_SIMULATION_MODE execution path"
    )

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["no_silent_task_simulation"] == (
        "failed: task_engine.py still contains AGENT_TASK_SIMULATION_MODE execution path"
    )


def test_report_generation(service, tmpdir):
    state = get_perfect_state()
    report_path = os.path.join(tmpdir, "ga-readiness.md")
    service.generate_report(state, filepath=report_path)

    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "GA_READY" in content
        assert "12 / 12" in content
        assert "Platform is GA_READY 12/12." in content
