import os
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../control_plane"))
from app.core.config import get_settings
from app.services.platform.ga_readiness import GAReadinessService


@pytest.fixture
def service():
    config_path = os.path.join(os.path.dirname(__file__), "../../config/ga-readiness-rules.yaml")
    return GAReadinessService(config_path=config_path)


def get_perfect_state():
    return {
        "runtime_enabled": True,
        "worker_heartbeat_active": True,
        "real_execution_readiness_passed": True,
        "production_agentic_e2e_passed": True,
        "plugin_runtime_verified": True,
        "cryptographic_receipts_real": True,
        "observability_real_data": True,
        "profile_validation_strict": True,
        "no_placeholder_production_surface": True,
        "clean_working_tree": True,
        "supported_surface_no_production_beta_stub": True,
        "release_gate_passed": True,
        "_reasons": {
            "supported_surface_no_production_beta_stub": "validated providers: local_gateway",
        },
    }


def test_all_12_criteria_pass_is_ga_ready(service):
    result = service.evaluate_readiness(get_perfect_state())
    assert result["maturity_level"] == "ga_ready"
    assert result["score"] == 12
    assert result["total_possible"] == 12


def test_surface_audit_dirty_blocks_ga(service):
    state = get_perfect_state()
    state["no_placeholder_production_surface"] = False
    state["_reasons"]["no_placeholder_production_surface"] = "surface audit is dirty: 6 unregistered API routes"

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["no_placeholder_production_surface"] == "failed: surface audit is dirty: 6 unregistered API routes"


def test_provider_validation_missing_blocks_ga(service):
    state = get_perfect_state()
    state["supported_surface_no_production_beta_stub"] = False
    state["_reasons"]["supported_surface_no_production_beta_stub"] = (
        "provider validation latest/results.json has no non-mock provider with a passing basic_model_call"
    )

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["supported_surface_no_production_beta_stub"] == (
        "failed: provider validation latest/results.json has no non-mock provider with a passing basic_model_call"
    )


def test_silent_mock_blocks_ga(service):
    state = get_perfect_state()
    state["supported_surface_no_production_beta_stub"] = False
    state["_reasons"]["supported_surface_no_production_beta_stub"] = "mock LLM is explicitly allowed in production-capable mode"

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["supported_surface_no_production_beta_stub"] == (
        "failed: mock LLM is explicitly allowed in production-capable mode"
    )


def test_task_simulation_blocks_ga(service):
    state = get_perfect_state()
    state["supported_surface_no_production_beta_stub"] = False
    state["_reasons"]["supported_surface_no_production_beta_stub"] = (
        "task_engine.py still contains incomplete execution markers"
    )

    result = service.evaluate_readiness(state)

    assert result["maturity_level"] == "production_ready"
    assert result["score"] == 11
    assert result["details"]["supported_surface_no_production_beta_stub"] == (
        "failed: task_engine.py still contains incomplete execution markers"
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


def test_executor_mock_active_in_production_blocks_ga_runtime_check(service):
    settings = get_settings()
    original_mode = settings.deployment_mode
    original_mock = settings.agent_executor_mock_mode
    original_dry_run = settings.agent_executor_dry_run_mode
    original_simulation = settings.agent_executor_allow_simulation
    original_payment = settings.payment_provider
    original_embeddings = settings.embeddings_backend
    original_mock_backend = settings.mock_backend_enabled
    original_llm_provider = settings.agent_llm_provider
    original_worker_enabled = settings.agent_worker_enabled
    try:
        settings.deployment_mode = "production"
        settings.agent_executor_mock_mode = True
        settings.agent_executor_dry_run_mode = False
        settings.agent_executor_allow_simulation = False

        settings.payment_provider = "stripe"
        settings.embeddings_backend = "sentence-transformers"
        settings.mock_backend_enabled = False
        settings.agent_llm_provider = "gateway"
        settings.agent_worker_enabled = True

        ok, reason = service._production_surface_dependencies_ok(service._resolve_base_dir())

        assert ok is False
        assert "agentic-runtime requires real executor modes only; found mock" in reason
    finally:
        settings.deployment_mode = original_mode
        settings.agent_executor_mock_mode = original_mock
        settings.agent_executor_dry_run_mode = original_dry_run
        settings.agent_executor_allow_simulation = original_simulation
        settings.payment_provider = original_payment
        settings.embeddings_backend = original_embeddings
        settings.mock_backend_enabled = original_mock_backend
        settings.agent_llm_provider = original_llm_provider
        settings.agent_worker_enabled = original_worker_enabled


def test_supported_surface_mock_dependencies_block_ga(service):
    settings = get_settings()
    original_payment = settings.payment_provider
    original_embeddings = settings.embeddings_backend
    original_mock_backend = settings.mock_backend_enabled
    original_llm_provider = settings.agent_llm_provider
    original_worker_enabled = settings.agent_worker_enabled
    original_executor_mock = settings.agent_executor_mock_mode
    original_executor_dry_run = settings.agent_executor_dry_run_mode
    original_executor_sim = settings.agent_executor_allow_simulation
    try:
        settings.payment_provider = "mock"
        settings.embeddings_backend = "mock"
        settings.mock_backend_enabled = True
        settings.agent_llm_provider = "mock"
        settings.agent_worker_enabled = False
        settings.agent_executor_mock_mode = True
        settings.agent_executor_dry_run_mode = False
        settings.agent_executor_allow_simulation = False

        ok, reason = service._production_surface_dependencies_ok(service._resolve_base_dir())

        assert ok is False
        assert "billing requires PAYMENT_PROVIDER real" in reason
        assert "rag requires EMBEDDINGS_BACKEND real" in reason
        assert "agentic-runtime requires AGENT_LLM_PROVIDER not mock" in reason
    finally:
        settings.payment_provider = original_payment
        settings.embeddings_backend = original_embeddings
        settings.mock_backend_enabled = original_mock_backend
        settings.agent_llm_provider = original_llm_provider
        settings.agent_worker_enabled = original_worker_enabled
        settings.agent_executor_mock_mode = original_executor_mock
        settings.agent_executor_dry_run_mode = original_executor_dry_run
        settings.agent_executor_allow_simulation = original_executor_sim
