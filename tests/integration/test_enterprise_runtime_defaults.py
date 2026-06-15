from types import SimpleNamespace

from app.bootstrap.routers import include_optional_routers
from app.core.config import Settings
from app.schemas.managed_control_plane import ApplianceHeartbeatPayload
from fastapi import FastAPI


def _settings(**overrides) -> Settings:
    base = {
        "ADMIN_TOKEN": "test-admin-token",
        "DATABASE_URL": "sqlite+aiosqlite:////tmp/enterprise-runtime-defaults.db",
        "REDIS_URL": "redis://test.invalid:6379/0",
        "DATA_PLANE_BASE_URL": "http://localhost:8081",
        "DEPLOYMENT_MODE": "appliance",
        "KUBERNETES_MODE": False,
        "DISTRIBUTED_RUNTIME_ENABLED": False,
        "GPU_AUTOSCALING_ENABLED": False,
        "PLUGIN_MARKETPLACE_ENABLED": False,
        "MANAGED_CONTROL_PLANE_ENABLED": False,
    }
    base.update(overrides)
    return Settings(**base)


def test_enterprise_runtime_defaults_are_safe_and_offline_first():
    settings = _settings()

    assert settings.deployment_mode == "appliance"
    assert settings.kubernetes_mode is False
    assert settings.distributed_runtime_enabled is False
    assert settings.gpu_autoscaling_enabled is False
    assert settings.plugin_marketplace_enabled is False
    assert settings.managed_control_plane_enabled is False


def test_gpu_autoscaling_is_not_enabled_without_distributed_runtime():
    settings = _settings(distributed_runtime_enabled=False, gpu_autoscaling_enabled=True)

    assert settings.distributed_runtime_enabled is False
    assert settings.gpu_autoscaling_enabled is False


def test_optional_routers_are_excluded_by_default():
    app = FastAPI()
    include_optional_routers(
        app,
        SimpleNamespace(
            distributed_runtime_enabled=False,
            gpu_autoscaling_enabled=False,
            plugin_marketplace_enabled=False,
            managed_control_plane_enabled=False,
            deployment_mode="appliance",
        ),
    )
    paths = {route.path for route in app.routes}

    assert "/runtime/nodes/" not in paths
    assert "/admin/gpu/devices" not in paths
    assert "/admin/plugins/marketplace" not in paths
    assert "/managed/organizations" not in paths


def test_optional_routers_are_included_only_when_explicitly_enabled():
    app = FastAPI()
    include_optional_routers(
        app,
        SimpleNamespace(
            deployment_mode="managed_control_plane",
            distributed_runtime_enabled=True,
            gpu_autoscaling_enabled=True,
            plugin_marketplace_enabled=True,
            managed_control_plane_enabled=True,
        ),
    )
    paths = {route.path for route in app.routes}

    assert "/runtime/nodes/" in paths
    assert "/admin/gpu/devices" in paths
    assert "/admin/plugins/marketplace" in paths
    assert "/managed/organizations" in paths


def test_managed_heartbeat_rejects_prompt_or_document_payloads():
    try:
        ApplianceHeartbeatPayload(
            version="1.0.0",
            health_status="healthy",
            readiness=True,
            capacity_summary={"prompt": "secret user prompt"},
            enabled_providers=["ollama"],
            available_models=["llama3"],
        )
    except Exception as exc:
        assert "capacity_summary key 'prompt' is not allowed" in str(exc)
    else:
        raise AssertionError("heartbeat payload accepted blocked prompt metadata")
