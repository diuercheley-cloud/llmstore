import pytest
from app.core.config import get_settings
from app.services.auth import AdminRole, _role_from_permissions, get_admin_role


def test_admin_role_ordering():
    assert AdminRole.READ < AdminRole.WRITE
    assert AdminRole.WRITE < AdminRole.SUPER
    assert AdminRole.READ < AdminRole.SUPER

def test_get_admin_role_mapping(monkeypatch):
    monkeypatch.setenv("ADMIN_SUPER_TOKEN", "super")
    monkeypatch.setenv("ADMIN_WRITE_TOKEN", "write")
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read")
    get_settings.cache_clear()
    
    assert get_admin_role("super") == AdminRole.SUPER
    assert get_admin_role("write") == AdminRole.WRITE
    assert get_admin_role("read") == AdminRole.READ
    assert get_admin_role("invalid") is None

def test_role_from_permissions():
    assert _role_from_permissions({"superadmin:all"}) == AdminRole.SUPER
    assert _role_from_permissions({"clients:write"}) == AdminRole.WRITE
    assert _role_from_permissions({"clients:read"}) == AdminRole.READ
