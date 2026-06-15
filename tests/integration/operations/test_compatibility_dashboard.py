def test_compatibility_dashboard_markers():
    admin = open("control_plane/app/static/admin/index.html", encoding="utf-8").read()
    portal = open("control_plane/app/static/portal/index.html", encoding="utf-8").read()
    assert "Compatibility Contracts & Version Negotiation" in admin
    assert "compatibilityContractCount" in admin
    assert "deterministic compatibility only" in admin
    assert "no real hardware-backed compatibility trust" in admin
    assert "Compatibility Contracts & Version Negotiation" in portal
    assert "portalCompatibilityContractCount" in portal
    assert "deterministic compatibility only" in portal
