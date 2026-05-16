def test_federation_dashboard_markers():
    admin = open("control_plane/app/static/admin/index.html", "r", encoding="utf-8").read()
    portal = open("control_plane/app/static/portal/index.html", "r", encoding="utf-8").read()
    assert "Sovereign Federation Synchronization Protocol" in admin
    assert "federationEnvironmentCount" in admin
    assert "offline federation only" in admin
    assert "placeholder trust only" in admin
    assert "no real hardware-backed federation trust" in admin
    assert "Sovereign Federation Synchronization Protocol" in portal
    assert "portalFederationEnvironmentCount" in portal
    assert "placeholder trust only" in portal
