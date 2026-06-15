def test_dashboard_adapter_sandbox_markers():
    """Verifies that the adapter sandbox markers are present in the dashboards."""
    admin_path = "control_plane/app/static/admin/index.html"
    portal_path = "control_plane/app/static/portal/index.html"

    marker = "Controlled Adapter Sandbox"
    warning = "sandbox simulation only"

    with open(admin_path) as f:
        admin_content = f.read()
    assert marker in admin_content
    assert "All adapter activities are restricted." in admin_content

    with open(portal_path) as f:
        portal_content = f.read()
    assert marker in portal_content
    assert "No real infrastructure commands are permitted." in portal_content
