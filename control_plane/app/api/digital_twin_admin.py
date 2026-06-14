# Owner: agent-platform
import uuid
from typing import Any, Dict

from app.services.runtime_dependencies import get_db
from app.services.agents.digital_twins.twin_registry import TwinRegistry
from app.services.agents.digital_twins.twin_service import DigitalTwinService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/digital-twins", tags=["Digital Twin Connectors"])

@router.post("")
async def register_twin(
    config: Dict[str, Any],
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = TwinRegistry(db)
    return await service.register(tenant_id, config)

@router.get("/{twin_id}/state")
async def get_twin_state(
    twin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    try:
        return await service.read_twin(twin_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/{twin_id}/command")
async def send_twin_command(
    twin_id: uuid.UUID,
    command_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    try:
        return await service.send_command(
            twin_id, 
            command_data["command"], 
            command_data.get("parameters", {})
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
