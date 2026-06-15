# Owner: commercial-ops
from datetime import datetime

from app.core.config import get_settings
from app.models.commercial.commercial_global_traffic import (
    CommercialGlobalTrafficDecision,
    CommercialGlobalTrafficPolicy,
)
from app.services.auth import require_admin as get_admin_user
from app.services.routing.commercial_global_traffic_shifter import CommercialGlobalTrafficShifter
from app.services.runtime_dependencies import get_db_session as get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
cfg = get_settings()


class PolicyCreate(BaseModel):
    name: str
    source_cluster: str
    target_cluster: str
    percent: int
    mode: str = "dry_run"
    max_percent: int | None = None
    tenant_id: str | None = None
    provider: str | None = None
    model: str | None = None
    region: str | None = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    enabled: bool
    source_cluster_id: str
    target_cluster_id: str
    tenant_id: str | None
    provider: str | None
    model: str | None
    region: str | None
    mode: str
    traffic_percent: int
    max_traffic_percent: int
    status: str
    reason: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None
    rolled_back_at: datetime | None


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    policy_id: str | None
    correlation_id: str | None
    request_id: str | None
    client_id: str | None
    tenant_id: str | None
    selected_cluster_id: str
    original_cluster_id: str
    target_cluster_id: str | None
    decision: str
    bucket: int
    traffic_percent: int
    reason: str | None
    created_at: datetime


class SimulateRequest(BaseModel):
    tenant_id: str | None = None
    client_id: str | None = None
    provider: str | None = "openai"
    model: str | None = "gpt-4"
    correlation_id: str | None = None
    request_id: str | None = None


@router.get("/policies", response_model=list[PolicyResponse])
async def get_policies(db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)):
    res = await db.execute(select(CommercialGlobalTrafficPolicy))
    return res.scalars().all()


@router.post("/policies", response_model=PolicyResponse)
async def create_policy(
    policy_in: PolicyCreate, db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)
):
    shifter = CommercialGlobalTrafficShifter(db)
    # Sanitize max_percent and check limits
    max_percent = policy_in.max_percent or cfg.commercial_global_traffic_shifting_max_canary_percent
    if policy_in.percent > max_percent:
        raise HTTPException(status_code=400, detail="percent cannot exceed max_percent")

    policy = await shifter.create_policy(
        name=policy_in.name,
        source_cluster=policy_in.source_cluster,
        target_cluster=policy_in.target_cluster,
        percent=policy_in.percent,
        mode=policy_in.mode,
        max_percent=max_percent,
        tenant_id=policy_in.tenant_id,
        provider=policy_in.provider,
        model=policy_in.model,
        region=policy_in.region,
        created_by=admin.get("username", "admin") if isinstance(admin, dict) else "admin",
    )
    return policy


@router.post("/policies/{id}/pause", response_model=PolicyResponse)
async def pause_policy(id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)):
    shifter = CommercialGlobalTrafficShifter(db)
    policy = await shifter.pause_policy(id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found or not active")
    return policy


@router.post("/policies/{id}/rollback", response_model=PolicyResponse)
async def rollback_policy(
    id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)
):
    shifter = CommercialGlobalTrafficShifter(db)
    policy = await shifter.rollback_policy(id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.get("/policies/{id}/health")
async def policy_health(id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)):
    res = await db.execute(
        select(CommercialGlobalTrafficPolicy).where(CommercialGlobalTrafficPolicy.id == id)
    )
    policy = res.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    shifter = CommercialGlobalTrafficShifter(db)
    health = await shifter.check_cluster_health(policy.target_cluster_id)

    return {
        "policy_id": id,
        "target_cluster": policy.target_cluster_id,
        "is_healthy": health,
        "status": policy.status,
    }


@router.post("/simulate", response_model=DecisionResponse)
async def simulate_decision(
    sim_in: SimulateRequest, db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)
):
    shifter = CommercialGlobalTrafficShifter(db)
    payload = sim_in.dict()
    decision = await shifter.decide_cluster_for_request(payload)
    return decision


@router.get("/decisions", response_model=list[DecisionResponse])
async def get_decisions(db: AsyncSession = Depends(get_db), admin=Depends(get_admin_user)):
    res = await db.execute(
        select(CommercialGlobalTrafficDecision)
        .order_by(CommercialGlobalTrafficDecision.created_at.desc())
        .limit(100)
    )
    return res.scalars().all()
