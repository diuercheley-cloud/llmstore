import pytest
from app.core.config import Settings
from app.services.auth import AdminRole, _role_from_permissions, get_admin_role


def test_admin_role_ordering():
    assert AdminRole.READ < AdminRole.WRITE
    assert AdminRole.WRITE < AdminRole.SUPER
    assert AdminRole.READ < AdminRole.SUPER

def test_get_admin_role_mapping():
    settings = Settings(
        admin_super_token="super",
        admin_write_token="write",
        admin_read_token="read"
    )
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.services.auth.get_settings", lambda: settings)
        assert get_admin_role("super") == AdminRole.SUPER
        assert get_admin_role("write") == AdminRole.WRITE
        assert get_admin_role("read") == AdminRole.READ
        assert get_admin_role("invalid") is None

def test_role_from_permissions():
    assert _role_from_permissions({"superadmin:all"}) == AdminRole.SUPER
    assert _role_from_permissions({"clients:write"}) == AdminRole.WRITE
    assert _role_from_permissions({"clients:read"}) == AdminRole.READ
