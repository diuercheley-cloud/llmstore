from control_plane.app.services.config.plugins_config import PluginsConfig


def test_plugins_config_defaults():
    config = PluginsConfig()

    assert config.plugin_marketplace_enabled is False
    assert config.marketplace_governance_enabled is True
    assert config.marketplace_require_security_scan is True
    assert config.marketplace_require_approval is True
    assert config.plugin_sbom_policy_decision == "block"


def test_plugins_config_reads_environment(monkeypatch):
    monkeypatch.setenv("PLUGIN_MARKETPLACE_ENABLED", "true")
    monkeypatch.setenv("MARKETPLACE_REQUIRE_APPROVAL", "false")
    monkeypatch.setenv("PLUGIN_SBOM_POLICY_DECISION", "allow")

    config = PluginsConfig()

    assert config.plugin_marketplace_enabled is True
    assert config.marketplace_require_approval is False
    assert config.plugin_sbom_policy_decision == "allow"
