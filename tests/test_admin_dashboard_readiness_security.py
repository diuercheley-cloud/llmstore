import pytest
from httpx import AsyncClient
from pathlib import Path

@pytest.mark.asyncio
async def test_admin_dashboard_html_contains_new_elements(admin_client: AsyncClient):
    # This tests the static file content
    candidates = [
        Path("control_plane/app/static/admin/index.html"),
        Path("app/static/admin/index.html"),
    ]
    dashboard_path = next((path for path in candidates if path.exists()), None)
    assert dashboard_path is not None, "admin dashboard static file not found"
    content = dashboard_path.read_text()
    
    assert "Runtime & Hardening Status" in content
    assert "runtimeCard" in content
    assert "readinessCard" in content
    assert "securityReportCard" in content
    assert "renderRuntimeSummary" in content
    assert "renderReadinessReport" in content
    assert "renderSecurityReport" in content
