import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.web_ide.workspace_service import WorkspaceService
from app.services.web_ide.file_service import FileService
from app.services.web_ide.validation_service import ValidationService
from app.services.web_ide.sandbox_terminal import SandboxTerminal

@pytest.fixture
def temp_workspace_dir(tmp_path):
    return tmp_path / "workspaces"

@pytest.mark.asyncio
async def test_workspace_creation(temp_workspace_dir):
    mock_settings = MagicMock()
    mock_settings.web_ide_workspaces_dir = str(temp_workspace_dir)
    with patch("app.services.web_ide.workspace_service.settings", mock_settings):
        tenant_id = "tenant-123"
        svc = WorkspaceService(tenant_id)
        path = await svc.ensure_workspace()
        
        assert os.path.exists(path)
        assert os.path.exists(os.path.join(path, "agents"))
        assert os.path.exists(os.path.join(path, "agents", "sample_agent.yaml"))

@pytest.mark.asyncio
async def test_file_crud(temp_workspace_dir):
    ws_path = temp_workspace_dir / "tenant-1"
    os.makedirs(ws_path, exist_ok=True)
    
    svc = FileService(ws_path)
    filename = "test.txt"
    content = "hello world"
    
    await svc.write_file(filename, content)
    read_content = await svc.read_file(filename)
    assert read_content == content
    
    files = await svc.list_files()
    assert any(f["name"] == filename for f in files)
    
    await svc.delete_file(filename)
    assert not os.path.exists(ws_path / filename)

@pytest.mark.asyncio
async def test_manifest_validation():
    valid_yaml = "name: Test Agent\nversion: 1.0.0"
    invalid_yaml = "name: Test Agent" # Missing version
    
    valid, _ = ValidationService.validate_manifest(valid_yaml)
    assert valid is True
    
    valid, msg = ValidationService.validate_manifest(invalid_yaml)
    assert valid is False
    assert "version" in msg

@pytest.mark.asyncio
async def test_sandbox_restricted_commands(temp_workspace_dir):
    ws_path = str(temp_workspace_dir)
    os.makedirs(ws_path, exist_ok=True)
    
    # Allowed command
    res = await SandboxTerminal.run_command("ls", ws_path)
    assert res["exit_code"] == 0
    
    # Blocked command
    res = await SandboxTerminal.run_command("rm -rf /", ws_path)
    assert res["exit_code"] == 1
    assert "not allowed" in res["stderr"]

@pytest.mark.asyncio
async def test_tenant_isolation(temp_workspace_dir):
    # This is implicitly tested by workspace_service using tenant_id in path
    # But let's verify FileService traversal protection
    ws_path = temp_workspace_dir / "tenant-1"
    os.makedirs(ws_path, exist_ok=True)
    
    svc = FileService(ws_path)
    
    with pytest.raises(Exception):
        # Trying to go up to host root or other tenant
        await svc.list_files("../tenant-2")
