# Owner: platform-ops
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.db.session import get_db_session
from app.services.chaos_engineering import ChaosEngineeringService
from pydantic import BaseModel

router = APIRouter(prefix="/admin/chaos", tags=["chaos"])

class ChaosRunCreate(BaseModel):
    experiment_id: str

@router.get("/experiments")
async def list_experiments(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    return await service.list_experiments()

@router.post("/runs")
async def create_run(
    data: ChaosRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    run = await service.create_run(data.experiment_id, operator_id=admin.id)
    background_tasks.add_task(service.start_run, run.id)
    return run

@router.get("/runs/{id}/report")
async def get_report(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    report = await service.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this run")
    return report

@router.post("/runs/{id}/abort")
async def abort_run(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    await service.abort_run(id)
    return {"status": "abort_requested"}
