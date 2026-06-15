def test_dashboard_remediation_markers():
    """Verifies that the remediation planning markers are present in the dashboards."""
    admin_path = "control_plane/app/static/admin/index.html"
    portal_path = "control_plane/app/static/portal/index.html"

    marker = "Deterministic Remediation Planning"
    warning = "Planning only — no automatic remediation"

    with open(admin_path) as f:
        admin_content = f.read()
    assert marker in admin_content
    assert warning in admin_content

    with open(portal_path) as f:
        portal_content = f.read()
    assert marker in portal_content
    # Portal has a specific warning
    assert "Planning only — no automatic remediation" in portal_content
