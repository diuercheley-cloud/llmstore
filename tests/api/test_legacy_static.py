import pytest
from app.core.config import get_settings
from app.main import app
from fastapi.testclient import TestClient


def test_legacy_static_disabled_by_default():
    settings = get_settings()
    # Ensure it's disabled in the current test environment or force it
    if settings.enable_legacy_static:
        pytest.skip("ENABLE_LEGACY_STATIC is true in this environment")

    client = TestClient(app)
    # This should be disabled
    response = client.get("/static/admin/index.html")
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert "Legacy static mounts are disabled by default" in data["error"]


def test_modern_static_enabled_by_default():
    settings = get_settings()
    client = TestClient(app)

    # These should be ENABLED even if legacy static is disabled
    response = client.get("/static/admin-v2/index.html")
    assert response.status_code == 200
    # It should be the HTML file, not JSON
    assert "application/json" not in response.headers["content-type"]
    assert b"<!doctype html>" in response.content


def test_modern_static_assets_are_not_captured_by_legacy_admin_shim():
    client = TestClient(app)

    response = client.get("/static/admin-v2/assets/index-CSe-v-SK.js")
    assert response.status_code == 200
    assert "application/json" not in response.headers["content-type"]
    assert b"import" in response.content[:200]


@pytest.mark.filterwarnings("ignore:Legacy Admin UI.*is deprecated")
def test_legacy_admin_deprecation_shim():
    client = TestClient(app)
    response = client.get("/static/admin")

    assert response.status_code == 200
    data = response.json()
    assert "deprecated" in data["message"].lower()
    assert "/admin-dashboard" in data["message"]
