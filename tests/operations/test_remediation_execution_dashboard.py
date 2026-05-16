import os

def test_dashboard_remediation_execution_markers():
    """Verifies that the remediation execution markers are present in the dashboards."""
    admin_path = "control_plane/app/static/admin/index.html"
    portal_path = "control_plane/app/static/portal/index.html"
    
    marker = "Approval-Gated Remediation Execution"
    
    with open(admin_path, 'r') as f:
        admin_content = f.read()
    assert marker in admin_content
    assert "Simulation-only in Phase 72" in admin_content
    
    with open(portal_path, 'r') as f:
        portal_content = f.read()
    assert marker in portal_content
    assert "Simulation-only in Phase 72" in portal_content
