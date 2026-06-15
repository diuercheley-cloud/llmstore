import pytest
from app.services.operations.environment_preflight import EnvironmentPreflightService


@pytest.mark.asyncio
async def test_environment_preflight_reports_failures(monkeypatch):
    service = EnvironmentPreflightService()

    async def fake_ports():
        return {"postgres": "PASS", "redis": "FAIL", "api": "PASS"}

    async def fake_deps():
        return {"fastapi": "PASS", "sqlalchemy": "PASS"}

    monkeypatch.setattr(service, "_check_required_ports", fake_ports)
    monkeypatch.setattr(service, "_check_python_deps", fake_deps)
    monkeypatch.setattr(
        service, "_check_env_files", lambda: {".env": "PASS", ".env.example": "PASS"}
    )

    report = await service.run_full_preflight()

    assert report["status"] == "FAIL"
    assert report["failures"] == ["ports"]


@pytest.mark.asyncio
async def test_environment_preflight_passes_when_all_checks_pass(monkeypatch):
    service = EnvironmentPreflightService()

    async def fake_ports():
        return {"postgres": "PASS", "redis": "PASS", "api": "PASS"}

    async def fake_deps():
        return {"fastapi": "PASS", "sqlalchemy": "PASS"}

    monkeypatch.setattr(service, "_check_required_ports", fake_ports)
    monkeypatch.setattr(service, "_check_python_deps", fake_deps)
    monkeypatch.setattr(
        service, "_check_env_files", lambda: {".env": "PASS", ".env.example": "PASS"}
    )

    report = await service.run_full_preflight()

    assert report["status"] == "PASS"
    assert "failures" not in report
