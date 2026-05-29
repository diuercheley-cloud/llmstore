import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure control plane is in PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "control_plane"))

from app.services.platform.ga_readiness import GAReadinessService

@pytest.mark.asyncio
async def test_ga_readiness_runtime_disabled():
    with patch("app.services.platform.ga_readiness.get_settings") as mock_settings:
        mock_settings.return_value.agent_runtime_enabled = False
        svc = GAReadinessService()
        
        state = {
            "runtime_enabled": False,
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
            "_reasons": {}
        }
        res = svc.evaluate_readiness(state)
        assert res["maturity_level"] != "ga_ready"
        assert "runtime_enabled" in res["failed_criteria"]

@pytest.mark.asyncio
async def test_ga_readiness_worker_absent():
    with patch("app.services.platform.ga_readiness.get_settings") as mock_settings:
        mock_settings.return_value.agent_runtime_enabled = True
        svc = GAReadinessService()
        
        state = {
            "runtime_enabled": True,
            "worker_heartbeat_active": False,
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
            "_reasons": {}
        }
        res = svc.evaluate_readiness(state)
        assert res["maturity_level"] != "ga_ready"
        assert "worker_heartbeat_active" in res["failed_criteria"]

@pytest.mark.asyncio
async def test_ga_readiness_all_pass():
    with patch("app.services.platform.ga_readiness.get_settings") as mock_settings:
        mock_settings.return_value.agent_runtime_enabled = True
        svc = GAReadinessService()
        
        state = {
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
            "_reasons": {}
        }
        res = svc.evaluate_readiness(state)
        assert res["maturity_level"] == "ga_ready"
        assert len(res["failed_criteria"]) == 0
