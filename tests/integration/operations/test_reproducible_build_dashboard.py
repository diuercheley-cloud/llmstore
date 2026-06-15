def test_reproducible_build_dashboard_markers():
    admin = open("control_plane/app/static/admin/index.html", encoding="utf-8").read()
    portal = open("control_plane/app/static/portal/index.html", encoding="utf-8").read()
    assert "Reproducible Build &amp; Artifact Verification Framework" in admin
    assert "reproducibleBuildManifestCount" in admin
    assert "deterministic verification only" in admin
    assert "no real external build execution" in admin
    assert "offline-first reproducible build framework" in admin
    assert "Reproducible Build &amp; Artifact Verification Framework" in portal
    assert "portalReproducibleBuildManifestCount" in portal
    assert "deterministic verification only" in portal
