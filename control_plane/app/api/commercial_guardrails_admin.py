from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.commercial_guardrails import (
    build_commercial_guardrails_overview,
    get_commercial_guardrails_runtime_status,
    simulate_commercial_guardrails,
)

router = APIRouter(
    prefix="/admin/commercial-guardrails",
    tags=["admin", "commercial-guardrails"],
    dependencies=[Depends(require_admin)],
)


class CommercialGuardrailsSimulationInput(BaseModel):
    client_id: str = Field(min_length=1)
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=255)
    estimated_cost_brl: float = Field(ge=0)
    estimated_revenue_brl: float = Field(ge=0)


@router.get("/overview")
async def commercial_guardrails_overview(
    session: AsyncSession = Depends(get_db_session),
):
    return await build_commercial_guardrails_overview(session)


@router.post("/simulate")
async def commercial_guardrails_simulate(
    payload: CommercialGuardrailsSimulationInput,
    session: AsyncSession = Depends(get_db_session),
):
    return await simulate_commercial_guardrails(
        session,
        client_id=payload.client_id,
        provider=payload.provider,
        model=payload.model,
        estimated_cost_brl=payload.estimated_cost_brl,
        estimated_revenue_brl=payload.estimated_revenue_brl,
    )


@router.get("/runtime-status")
async def commercial_guardrails_runtime_status():
    return get_commercial_guardrails_runtime_status()
