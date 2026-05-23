# Owner: commercial-ops
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.commercial_revenue_alert_delivery import CommercialRevenueAlertDelivery
from app.models.commercial_revenue_escalation_policy import CommercialRevenueEscalationPolicy
from app.services.auth import require_admin
from app.services.notifications.revenue_escalations import (
    evaluate_escalation_policies,
    retry_alert_delivery,
    sanitize_alert_payload,
    summarize_deliveries,
)

router = APIRouter(
    tags=["admin", "billing", "revenue-escalations"],
    dependencies=[Depends(require_admin)],
)


class RevenueEscalationPolicyUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    severity_threshold: str = "high"
    trigger_types_json: list[str] = Field(default_factory=list)
    allowed_delivery_types_json: list[str] = Field(default_factory=lambda: ["webhook", "slack", "pagerduty", "email"])
    cooldown_minutes: int = Field(default=30, ge=0, le=10080)
    max_retries: int = Field(default=3, ge=0, le=10)
    escalation_order_json: list[str] = Field(default_factory=lambda: ["webhook", "slack", "pagerduty", "email"])
    metadata_json: dict[str, Any] | None = None


class RevenueEscalationTestRequest(BaseModel):
    source_type: str = "policy_action"
    severity: str = "critical"
    summary: str = "Manual revenue escalation test"
    recommendation: str = "Verify notification wiring and escalation runbooks."
    trigger_type: str = "manual_test"
    metadata_json: dict[str, Any] | None = None
    delivery_types: list[str] | None = None


@router.get("/deliveries")
async def list_deliveries(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialRevenueAlertDelivery).order_by(desc(CommercialRevenueAlertDelivery.created_at)).limit(limit)
    if status:
        stmt = stmt.where(CommercialRevenueAlertDelivery.status == status)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/policies")
async def list_policies(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(CommercialRevenueEscalationPolicy).order_by(desc(CommercialRevenueEscalationPolicy.created_at)))
    return result.scalars().all()


@router.post("/test")
async def send_test(payload: RevenueEscalationTestRequest, session: AsyncSession = Depends(get_db_session)):
    return await evaluate_escalation_policies(
        session,
        source_type=payload.source_type,
        source_id=f"test-{uuid.uuid4()}",
        severity=payload.severity,
        summary=payload.summary,
        recommendation=payload.recommendation,
        metadata=sanitize_alert_payload(payload.metadata_json or {}),
        trigger_type=payload.trigger_type,
        delivery_types=payload.delivery_types,
    )


@router.post("/retry/{delivery_id}")
async def retry_delivery(delivery_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    try:
        return await retry_alert_delivery(session, delivery_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "delivery_not_found" else 409 if detail == "retry_backoff_active" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post("/policies", status_code=201)
async def create_policy(payload: RevenueEscalationPolicyUpsert, session: AsyncSession = Depends(get_db_session)):
    policy = CommercialRevenueEscalationPolicy(
        **{
            **payload.model_dump(),
            "metadata_json": sanitize_alert_payload(payload.metadata_json or {}),
        }
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return policy


@router.patch("/policies/{policy_id}")
async def patch_policy(policy_id: uuid.UUID, payload: RevenueEscalationPolicyUpsert, session: AsyncSession = Depends(get_db_session)):
    policy = await session.get(CommercialRevenueEscalationPolicy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="policy_not_found")
    for key, value in payload.model_dump().items():
        setattr(policy, key, sanitize_alert_payload(value) if key == "metadata_json" else value)
    await session.commit()
    await session.refresh(policy)
    return policy


@router.get("/status")
async def status(session: AsyncSession = Depends(get_db_session)):
    return await summarize_deliveries(session)
