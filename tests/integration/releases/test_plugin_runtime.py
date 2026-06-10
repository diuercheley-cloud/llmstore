import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "control_plane"))

from app.models.plugins.marketplace import PluginInstall, PluginPermissionGrant, PluginVersion
from app.services.plugins.plugin_runtime import PluginRuntimeService


@pytest.mark.asyncio
async def test_plugin_no_manifest_fails():
    db = AsyncMock()
    install = PluginInstall(id=uuid.uuid4(), current_version_id=uuid.uuid4())
    version = PluginVersion(id=install.current_version_id, manifest_json={}, checksum_sha256="a"*64)
    
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: install),
        MagicMock(scalar_one_or_none=lambda: version)
    ]
    
    svc = PluginRuntimeService(db)
    with pytest.raises(ValueError, match="manifest is missing"):
        await svc.verify_plugin(install.id)

@pytest.mark.asyncio
async def test_plugin_no_signature_fails_when_enforced():
    db = AsyncMock()
    install = PluginInstall(id=uuid.uuid4(), current_version_id=uuid.uuid4())
    version = PluginVersion(
        id=install.current_version_id,
        manifest_json={"name": "test", "version": "1.0.0"}, # no signature
        checksum_sha256="a"*64
    )
    
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: install),
        MagicMock(scalar_one_or_none=lambda: version)
    ]
    
    with patch("app.services.plugins.plugin_runtime.get_settings") as mock_settings:
        mock_settings.return_value.plugin_signature_enforced = True
        svc = PluginRuntimeService(db)
        with pytest.raises(ValueError, match="signature is missing"):
            await svc.verify_plugin(install.id)

@pytest.mark.asyncio
async def test_plugin_wildcard_commands_forbidden_in_production():
    db = AsyncMock()
    install = PluginInstall(id=uuid.uuid4(), current_version_id=uuid.uuid4())
    version = PluginVersion(
        id=install.current_version_id,
        manifest_json={"name": "test", "version": "1.0.0", "allowed_commands": ["*"], "permissions": ["network"]},
        checksum_sha256="a"*64
    )
    
    grant = PluginPermissionGrant(plugin_id=install.id, tenant_id="tenant-a", permission_name="network", is_granted=True)
    
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: install),
        MagicMock(scalar_one_or_none=lambda: version),
        MagicMock(scalar_one_or_none=lambda: grant) # permission grant check
    ]
    
    with patch("app.services.plugins.plugin_runtime.get_settings") as mock_settings:
        mock_settings.return_value.plugin_runtime_enabled = True
        mock_settings.return_value.deployment_mode = "production"
        svc = PluginRuntimeService(db)
        with pytest.raises(ValueError, match="allowed_commands.*is forbidden in production"):
            await svc.run_plugin(install.id, "print('hello')", {}, "tenant-a")

@pytest.mark.asyncio
async def test_plugin_tenant_isolation_enforced():
    db = AsyncMock()
    install = PluginInstall(id=uuid.uuid4(), current_version_id=uuid.uuid4())
    version = PluginVersion(
        id=install.current_version_id,
        manifest_json={"name": "test", "version": "1.0.0", "allowed_commands": ["echo"], "permissions": ["network"]},
        checksum_sha256="a"*64
    )
    
    # Mock permission grant check returning None (tenant has no permission)
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: install),
        MagicMock(scalar_one_or_none=lambda: version),
        MagicMock(scalar_one_or_none=lambda: None) # Grant is missing/False
    ]
    
    with patch("app.services.plugins.plugin_runtime.get_settings") as mock_settings:
        mock_settings.return_value.plugin_runtime_enabled = True
        mock_settings.return_value.deployment_mode = "production"
        svc = PluginRuntimeService(db)
        # Should raise permission grant error
        with pytest.raises(ValueError, match="does not have explicit permission grant"):
            await svc.run_plugin(install.id, "print('hello')", {}, "tenant-b")
