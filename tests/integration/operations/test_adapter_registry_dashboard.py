def test_dashboard_contains_registry_section():
    admin_html_path = "control_plane/app/static/admin/index.html"
    portal_html_path = "control_plane/app/static/portal/index.html"

    with open(admin_html_path) as f:
        admin_content = f.read()
    assert "Signed Adapter Registry" in admin_content
    assert "adapterRegistryCount" in admin_content
    assert "signature placeholder only" in admin_content

    with open(portal_html_path) as f:
        portal_content = f.read()
    assert "Signed Adapter Registry" in portal_content
    assert "portalRegistryEntries" in portal_content
    assert "Signature placeholder only" in portal_content
