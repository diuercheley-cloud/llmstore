import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
import httpx

from app.core.config import Settings
from app.services.platform.deployment_modes import DeploymentModeService
from app.api.system import get_operational_readiness

def test_deployment_modes_service_fallback_defaults():
    service = DeploymentModeService(config_path="/invalid/path/deployment-modes.yaml")
    assert service.get_governance_posture("appliance") == "Strict Air-gapped / Local Only"
    assert service.get_governance_posture("pilot") == "Governed Testing / Human-in-the-loop"
    assert service.get_governance_posture("production") == "Production Grade / Automatic Evals & SLOs"
    assert service.get_governance_posture("enterprise_managed") == "Enterprise Managed / Federated & Strict Isolation"

def test_deployment_modes_service_load_config():
    service = DeploymentModeService()
    appliance_defaults = service.get_mode_defaults("appliance")
    assert appliance_defaults["AGENT_RUNTIME_ENABLED"] is False
    assert appliance_defaults["AGENT_SAAS_CONNECTORS_ENABLED"] is False

    pilot_defaults = service.get_mode_defaults("pilot")
    assert pilot_defaults["AGENT_RUNTIME_ENABLED"] is True
    assert pilot_defaults["AGENT_CONNECTOR_WRITE_ENABLED"] is False
    assert pilot_defaults["AGENT_HUMAN_APPROVAL_ENABLED"] is True
    assert pilot_defaults["AGENT_STRICT_BUDGETS"] is True

def test_settings_defaults_propagation():
    with patch.dict(os.environ, {"DEPLOYMENT_MODE": "appliance"}, clear=True):
        settings = Settings(DEPLOYMENT_MODE="appliance")
        assert settings.agent_runtime_enabled is False
        assert settings.agent_saas_connectors_enabled is False
        assert settings.agent_stateful_workflows_enabled is False

    with patch.dict(os.environ, {"DEPLOYMENT_MODE": "pilot"}, clear=True):
        settings = Settings(DEPLOYMENT_MODE="pilot")
        assert settings.agent_runtime_enabled is True
        assert settings.agent_connector_write_enabled is False
        assert settings.agent_human_approval_enabled is True
        assert settings.agent_strict_budgets is True
        assert settings.agent_multi_agent_enabled is False

    with patch.dict(os.environ, {"DEPLOYMENT_MODE": "production"}, clear=True):
        settings = Settings(DEPLOYMENT_MODE="production")
        assert settings.agent_runtime_enabled is True
        assert settings.agent_promotion_requires_evals is True
        assert settings.agent_eval_regression_gate_enabled is True
        assert settings.agent_worker_autoscaling_enabled is True

    with patch.dict(os.environ, {"DEPLOYMENT_MODE": "enterprise_managed"}, clear=True):
        settings = Settings(DEPLOYMENT_MODE="enterprise_managed")
        assert settings.agent_runtime_enabled is True
        assert settings.agent_tenant_isolation_strict is True
        assert settings.managed_control_plane_enabled is True

def test_coherence_validation_appliance():
    service = DeploymentModeService()
    
    settings = Settings(
        DEPLOYMENT_MODE="appliance",
        AGENT_RUNTIME_ENABLED=False,
        AGENT_SAAS_CONNECTORS_ENABLED=False,
        AGENT_MULTI_AGENT_ENABLED=False,
        AGENT_STATEFUL_WORKFLOWS_ENABLED=False
    )
    settings.model_fields_set.update({"deployment_mode", "agent_runtime_enabled", "agent_saas_connectors_enabled", "agent_multi_agent_enabled", "agent_stateful_workflows_enabled"})
    
    is_coherent, blockers, warnings = service.validate_coherence(settings)
    assert is_coherent is True
    assert len(blockers) == 0

    settings_invalid = Settings(
        DEPLOYMENT_MODE="appliance",
        AGENT_RUNTIME_ENABLED=True
    )
    settings_invalid.model_fields_set.update({"deployment_mode", "agent_runtime_enabled"})
    is_coherent, blockers, warnings = service.validate_coherence(settings_invalid)
    assert is_coherent is False
    assert any("AGENT_RUNTIME_ENABLED" in b for b in blockers)

def test_coherence_validation_pilot():
    service = DeploymentModeService()
    
    settings = Settings(
        DEPLOYMENT_MODE="pilot",
        AGENT_RUNTIME_ENABLED=True,
        AGENT_CONNECTOR_WRITE_ENABLED=False,
        AGENT_HUMAN_APPROVAL_ENABLED=True
    )
    settings.model_fields_set.update({"deployment_mode", "agent_runtime_enabled", "agent_connector_write_enabled", "agent_human_approval_enabled"})
    
    is_coherent, blockers, warnings = service.validate_coherence(settings)
    assert is_coherent is True

    settings_invalid = Settings(
        DEPLOYMENT_MODE="pilot",
        AGENT_CONNECTOR_WRITE_ENABLED=True
    )
    settings_invalid.model_fields_set.update({"deployment_mode", "agent_connector_write_enabled"})
    is_coherent, blockers, warnings = service.validate_coherence(settings_invalid)
    assert is_coherent is False
    assert any("AGENT_CONNECTOR_WRITE_ENABLED" in b for b in blockers)

    settings_no_approval = Settings(
        DEPLOYMENT_MODE="pilot",
        AGENT_HUMAN_APPROVAL_ENABLED=False
    )
    settings_no_approval.model_fields_set.update({"deployment_mode", "agent_human_approval_enabled"})
    is_coherent, blockers, warnings = service.validate_coherence(settings_no_approval)
    assert is_coherent is False
    assert any("AGENT_HUMAN_APPROVAL_ENABLED" in b for b in blockers)

    settings_multi = Settings(
        DEPLOYMENT_MODE="pilot",
        AGENT_MULTI_AGENT_ENABLED=True
    )
    settings_multi.model_fields_set.update({"deployment_mode", "agent_multi_agent_enabled"})
    is_coherent, blockers, warnings = service.validate_coherence(settings_multi)
    assert len(blockers) == 0
    assert any("AGENT_MULTI_AGENT_ENABLED" in w for w in warnings)

def test_coherence_validation_production():
    service = DeploymentModeService()
    
    settings = Settings(
        DEPLOYMENT_MODE="production",
        AGENT_RUNTIME_ENABLED=True,
        AGENT_PROMOTION_REQUIRES_EVALS=True,
        AGENT_EVAL_REGRESSION_GATE_ENABLED=True
    )
    settings.model_fields_set.update({"deployment_mode", "agent_runtime_enabled", "agent_promotion_requires_evals", "agent_eval_regression_gate_enabled"})
    is_coherent, blockers, warnings = service.validate_coherence(settings)
    assert is_coherent is True

    settings_invalid = Settings(
        DEPLOYMENT_MODE="production",
        AGENT_PROMOTION_REQUIRES_EVALS=False
    )
    settings_invalid.model_fields_set.update({"deployment_mode", "agent_promotion_requires_evals"})
    is_coherent, blockers, warnings = service.validate_coherence(settings_invalid)
    assert is_coherent is False
    assert any("AGENT_PROMOTION_REQUIRES_EVALS" in b for b in blockers)

def test_coherence_validation_enterprise_managed():
    service = DeploymentModeService()
    
    settings = Settings(
        DEPLOYMENT_MODE="enterprise_managed",
        AGENT_RUNTIME_ENABLED=True,
        AGENT_TENANT_ISOLATION_STRICT=True,
        MANAGED_CONTROL_PLANE_ENABLED=True
    )
    settings.model_fields_set.update({"deployment_mode", "agent_runtime_enabled", "agent_tenant_isolation_strict", "managed_control_plane_enabled"})
    is_coherent, blockers, warnings = service.validate_coherence(settings)
    assert is_coherent is True

    settings_invalid = Settings(
        DEPLOYMENT_MODE="enterprise_managed",
        AGENT_TENANT_ISOLATION_STRICT=False
    )
    settings_invalid.model_fields_set.update({"deployment_mode", "agent_tenant_isolation_strict"})
    is_coherent, blockers, warnings = service.validate_coherence(settings_invalid)
    assert is_coherent is False
    assert any("AGENT_TENANT_ISOLATION_STRICT" in b for b in blockers)

@pytest.mark.asyncio
async def test_operational_readiness_endpoint_integration(admin_client):
    response = await admin_client.get("/operational-readiness")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "deployment_mode" in data["checks"]
    
    mode_data = data["checks"]["deployment_mode"]
    assert "mode" in mode_data
    assert "is_coherent" in mode_data
    assert "governance_posture" in mode_data

@pytest.mark.asyncio
async def test_ready_check_blocked_when_incoherent(admin_client):
    with patch("app.api.system.get_settings") as mock_get_settings:
        mock_settings = Settings(
            DEPLOYMENT_MODE="appliance",
            AGENT_RUNTIME_ENABLED=True
        )
        mock_settings.model_fields_set.update({"deployment_mode", "agent_runtime_enabled"})
        mock_get_settings.return_value = mock_settings

        response = await admin_client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["deployment_mode"] == "blocked"
