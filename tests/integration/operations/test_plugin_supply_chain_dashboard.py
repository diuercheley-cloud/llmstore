def test_plugin_supply_chain_dashboard_markers():
    admin = open("control_plane/app/static/admin/index.html", encoding="utf-8").read()
    portal = open("control_plane/app/static/portal/index.html", encoding="utf-8").read()
    assert "Plugin Supply-Chain Provenance &amp; SBOM Placeholder Framework" in admin
    assert "pluginSupplyChainProvenanceRecordCount" in admin
    assert "placeholder SBOM only" in admin
    assert "no real artifact signing" in admin
    assert "offline-first provenance only" in admin
    assert "Plugin Supply-Chain Provenance &amp; SBOM Placeholder Framework" in portal
    assert "portalPluginSupplyChainProvenanceRecordCount" in portal
    assert "placeholder SBOM only" in portal
