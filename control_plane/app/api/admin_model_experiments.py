import uuid
from typing import List, Optional

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.model_experiments import ModelExperiment
from app.services.auth import AdminRole, require_admin_role
from app.services.model_experiments.experiment_registry import ExperimentRegistry
from app.services.model_experiments.promotion_gate import PromotionGate
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/models/experiments", tags=["model_experiments"])
settings = get_settings()

class VariantCreate(BaseModel):
    name: str
    traffic_weight: float
    model_id: Optional[str] = None
    backend_id: Optional[uuid.UUID] = None
    is_control: bool = False

class ExperimentCreate(BaseModel):
    name: str
    experiment_type: str = "ab_test"
    target_route_id: Optional[uuid.UUID] = None
    target_tenant_id: Optional[str] = None
    variants: List[VariantCreate]

def _check_enabled():
    if not settings.model_experiments_enabled:
        raise HTTPException(status_code=403, detail="Model Experiments are disabled")

@router.post("")
async def create_experiment(
    payload: ExperimentCreate,
    session: AsyncSession = Depends(get_db_session),
    _ = Depends(require_admin_role(AdminRole.WRITE))
):
    _check_enabled()
    registry = ExperimentRegistry(session)
    experiment = await registry.create_experiment(
        payload.name, 
        payload.experiment_type, 
        payload.target_route_id, 
        payload.target_tenant_id
    )
    
    for v in payload.variants:
        await registry.add_variant(
            experiment.id, 
            v.name, 
            v.traffic_weight, 
            v.model_id, 
            v.backend_id, 
            v.is_control
        )
    
    await session.commit()
    return experiment

@router.get("")
async def list_experiments(
    session: AsyncSession = Depends(get_db_session),
    _ = Depends(require_admin_role(AdminRole.READ))
):
    _check_enabled()
    stmt = select(ModelExperiment).order_by(ModelExperiment.created_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())

@router.post("/{experiment_id}/promote")
async def promote_experiment(
    experiment_id: uuid.UUID,
    variant_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _ = Depends(require_admin_role(AdminRole.WRITE))
):
    _check_enabled()
    gate = PromotionGate(session)
    await gate.promote_variant(experiment_id, variant_id)
    await session.commit()
    return {"status": "promoted"}

@router.post("/{experiment_id}/rollback")
async def rollback_experiment(
    experiment_id: uuid.UUID,
    reason: str = "Manual rollback",
    session: AsyncSession = Depends(get_db_session),
    _ = Depends(require_admin_role(AdminRole.WRITE))
):
    _check_enabled()
    gate = PromotionGate(session)
    await gate.rollback(experiment_id, reason)
    await session.commit()
    return {"status": "rolled_back"}
