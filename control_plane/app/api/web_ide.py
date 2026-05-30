import uuid
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db.session import get_db_session
from app.services.auth import require_client
from app.models.client import Client
from app.core.config import get_settings
from app.services.web_ide.workspace_service import WorkspaceService
from app.services.web_ide.file_service import FileService
from app.services.web_ide.validation_service import ValidationService
from app.services.web_ide.sandbox_terminal import SandboxTerminal

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/v1/ide", tags=["web_ide"])

class FileWrite(BaseModel):
    path: str
    content: str

class CommandRun(BaseModel):
    command: str

def _check_enabled():
    if not settings.web_ide_enabled:
        raise HTTPException(status_code=403, detail="Web IDE is disabled")

@router.get("/workspace")
async def get_workspace(
    client: Client = Depends(require_client),
):
    _check_enabled()
    svc = WorkspaceService(client.id)
    path = await svc.ensure_workspace()
    return {"path": path, "tenant_id": client.id}

@router.get("/files")
async def list_files(
    path: str = "",
    client: Client = Depends(require_client),
):
    _check_enabled()
    ws_svc = WorkspaceService(client.id)
    file_svc = FileService(ws_svc.get_path())
    return await file_svc.list_files(path)

@router.get("/files/read")
async def read_file(
    path: str,
    client: Client = Depends(require_client),
):
    _check_enabled()
    ws_svc = WorkspaceService(client.id)
    file_svc = FileService(ws_svc.get_path())
    content = await file_svc.read_file(path)
    return {"content": content}

@router.post("/files/write")
async def write_file(
    payload: FileWrite,
    client: Client = Depends(require_client),
):
    _check_enabled()
    ws_svc = WorkspaceService(client.id)
    file_svc = FileService(ws_svc.get_path())
    await file_svc.write_file(payload.path, payload.content)
    return {"status": "ok"}

@router.post("/validate")
async def validate_file(
    path: str,
    client: Client = Depends(require_client),
):
    _check_enabled()
    ws_svc = WorkspaceService(client.id)
    file_svc = FileService(ws_svc.get_path())
    content = await file_svc.read_file(path)
    
    file_type = "yaml" if path.endswith(".yaml") or path.endswith(".yml") else "json"
    valid, message = ValidationService.validate_manifest(content, file_type)
    return {"valid": valid, "message": message}

@router.post("/run")
async def run_in_sandbox(
    payload: CommandRun,
    client: Client = Depends(require_client),
):
    _check_enabled()
    ws_svc = WorkspaceService(client.id)
    return await SandboxTerminal.run_command(payload.command, str(ws_svc.get_path()))
