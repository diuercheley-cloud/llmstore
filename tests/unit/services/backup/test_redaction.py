from app.services.backup.redaction import ConfigRedactor


def test_config_redactor_dict():
    redactor = ConfigRedactor()
    d = {"DB_PASSWORD": "secret_pass", "PORT": 8080, "nested": {"API_KEY": "some_key"}}
    redacted = redactor.redact_dict(d)
    assert redacted["DB_PASSWORD"] == "REDACTED"
    assert redacted["PORT"] == 8080
    assert redacted["nested"]["API_KEY"] == "REDACTED"
    assert "DB_PASSWORD" in redactor.get_redacted_keys()


def test_config_redactor_env():
    redactor = ConfigRedactor()
    content = "PORT=8080\nJWT_SECRET=supersecret\nDEBUG=true"
    redacted = redactor.redact_env_content(content)
    assert "PORT=8080" in redacted
    assert "JWT_SECRET=REDACTED" in redacted
    assert "DEBUG=true" in redacted
