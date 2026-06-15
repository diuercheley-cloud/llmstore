from app.services.agents.human_approval import has_sufficient_role, sanitize_value
from app.services.auth import AdminRole


def test_sanitize_value():
    data = {
        "prompt": "secret prompt",
        "api_key": "sk-123",
        "normal_field": "hello",
        "long_field": "a" * 600,
    }
    sanitized = sanitize_value(data)
    assert sanitized["prompt"] == "<redacted>"
    assert sanitized["api_key"] == "<redacted>"
    assert sanitized["normal_field"] == "hello"
    assert "truncated" in sanitized["long_field"]


def test_has_sufficient_role():
    assert has_sufficient_role(AdminRole.SUPER, "admin_write") is True
    assert has_sufficient_role(AdminRole.WRITE, "super_admin") is False
    assert has_sufficient_role(AdminRole.WRITE, "admin_write") is True
    assert has_sufficient_role(AdminRole.READ, "admin_read") is True
    assert has_sufficient_role(AdminRole.READ, "admin_write") is False
