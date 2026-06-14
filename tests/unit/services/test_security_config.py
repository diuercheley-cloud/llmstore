from control_plane.app.services.config.security_config import SecurityConfig


def test_security_config_reads_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "admin-token")
    monkeypatch.setenv("JWT_SECRET", "jwt-secret")

    config = SecurityConfig()

    assert config.admin_token == "admin-token"
    assert config.jwt_secret == "jwt-secret"
    assert config.rbac_admin_enabled is True
    assert config.admin_tests_rate_limit_enabled is True


def test_security_config_defaults_for_optional_values(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "admin-token")
    monkeypatch.setenv("JWT_SECRET", "jwt-secret")

    config = SecurityConfig()

    assert config.admin_read_token is None
    assert config.admin_write_token is None
    assert config.admin_super_token is None
    assert config.oauth_enabled is False
    assert config.enterprise_sso_enabled is False
    assert config.pki_enabled is False
