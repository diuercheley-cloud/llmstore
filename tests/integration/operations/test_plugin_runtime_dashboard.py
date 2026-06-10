def test_plugin_runtime_dashboard_markers():
    admin = open("control_plane/app/static/admin/index.html", "r", encoding="utf-8").read()
    portal = open("control_plane/app/static/portal/index.html", "r", encoding="utf-8").read()
    assert "Formal Plugin ABI &amp; Extension Runtime" in admin
    assert "pluginAbiContractCount" in admin
    assert "no real plugin execution" in admin
    assert "placeholder certification only" in admin
    assert "deterministic load simulation only" in admin
    assert "Formal Plugin ABI &amp; Extension Runtime" in portal
    assert "portalPluginAbiContractCount" in portal
    assert "no real plugin execution" in portal
