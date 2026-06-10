def test_attestation_dashboard_markers():
    admin = open("control_plane/app/static/admin/index.html", "r", encoding="utf-8").read()
    portal = open("control_plane/app/static/portal/index.html", "r", encoding="utf-8").read()

    assert "Sovereign Execution Attestation Framework" in admin
    assert "attestationFrameworkCount" in admin
    assert "placeholder attestation only" in admin
    assert "no hardware-backed trust implemented" in admin

    assert "Sovereign Execution Attestation Framework" in portal
    assert "portalAttestationCount" in portal
    assert "placeholder attestation only" in portal
    assert "no hardware-backed trust implemented" in portal
