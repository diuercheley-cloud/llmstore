# Owner: platform-ops
import uuid
from typing import Any, List

from app.api.dependencies import get_db, require_admin
from app.schemas.admin import ModelRuntimeInstanceSchema, ModelRuntimeLoadRequest
from app.services.model_runtime_manager import ModelRuntimeManager
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/models/runtime", tags=["admin-models-runtime"])

@router.get("", response_model=List[ModelRuntimeInstanceSchema])
async def list_runtimes(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    manager = ModelRuntimeManager(db)
    return await manager.list_loaded_models()

@router.post("/load", response_model=ModelRuntimeInstanceSchema)
async def load_model(
    payload: ModelRuntimeLoadRequest,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    manager = ModelRuntimeManager(db)
    try:
        return await manager.load_model(
            model_id=payload.model_id,
            backend_id=payload.backend_id,
            model_path=payload.model_path,
            runtime_config=payload.runtime_config
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unload/{instance_id}")
async def unload_model(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    manager = ModelRuntimeManager(db)
    await manager.unload_model(instance_id)
    return {"status": "success"}

@router.post("/activate/{instance_id}")
async def activate_model(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    manager = ModelRuntimeManager(db)
    try:
        await manager.activate_model(instance_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rollback")
async def rollback_model(
    model_id: uuid.UUID,
    backend_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    manager = ModelRuntimeManager(db)
    try:
        await manager.rollback_active_model(model_id, backend_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{instance_id}/health")
async def get_runtime_health(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    manager = ModelRuntimeManager(db)
    return await manager.get_model_health(instance_id)
