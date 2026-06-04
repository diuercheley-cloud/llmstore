from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_dashboard_html_contains_new_elements(admin_client: AsyncClient):
    # This tests the static file content
    candidates_html = [
        Path("control_plane/app/static/admin/index.legacy.html"),
        Path("app/static/admin/index.legacy.html"),
    ]
    candidates_js = [
        Path("control_plane/app/static/admin/index.legacy.js"),
        Path("app/static/admin/index.legacy.js"),
    ]
    html_path = next((path for path in candidates_html if path.exists()), None)
    js_path = next((path for path in candidates_js if path.exists()), None)
    
    assert html_path is not None, "admin dashboard legacy html file not found"
    assert js_path is not None, "admin dashboard legacy js file not found"
    
    html_content = html_path.read_text()
    js_content = js_path.read_text()
    
    assert "Runtime & Hardening Status" in html_content
    assert "runtimeCard" in html_content
    assert "readinessCard" in html_content
    assert "securityReportCard" in html_content
    assert "renderRuntimeSummary" in js_content
    assert "renderReadinessReport" in js_content
    assert "renderSecurityReport" in js_content
