from app.core.config import get_settings
from app.main import app
from fastapi.testclient import TestClient


def test_startup_with_defaults():
    """
    Test that the app starts up successfully with default settings
    (which should have all agentic features disabled).
    """
    settings = get_settings()
    
    # Verify default flags are False as per requirements
    assert settings.agent_runtime_enabled is False
    assert settings.agent_worker_enabled is False
    assert settings.agent_stateful_workflows_enabled is False
    assert settings.agent_saas_connectors_enabled is False
    assert settings.agent_reasoning_loop_enabled is False
    assert settings.agent_multi_agent_enabled is False
    assert settings.agent_studio_enabled is False

    # Test actual startup
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_agentic_routers_not_leaking_on_default():
    """
    Check if agentic endpoints are active even when disabled.
    Since we moved them to include_optional_routers, they should return 404.
    """
    with TestClient(app) as client:
        # Example agentic endpoint
        response = client.get("/admin/agents/runtime/status")
        assert response.status_code == 404
