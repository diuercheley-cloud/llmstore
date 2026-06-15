def test_dashboard_markers_phase_75():
    admin_path = "control_plane/app/static/admin/index.html"
    with open(admin_path) as f:
        content = f.read()

    assert "Adapter Promotion Workflow" in content
    assert "adapterPromotionCount" in content
    assert "promotion controls eligibility only" in content

    portal_path = "control_plane/app/static/portal/index.html"
    with open(portal_path) as f:
        content = f.read()

    assert "Adapter Promotion Workflow" in content
    assert "portalPromotionCount" in content
    assert "Eligibility only" in content
