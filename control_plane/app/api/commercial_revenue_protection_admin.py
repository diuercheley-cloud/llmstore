# Owner: commercial-ops
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.commercial_revenue_protection_action import CommercialRevenueProtectionAction
from app.models.commercial_revenue_protection_policy import CommercialRevenueProtectionPolicy
from app.services.auth import require_admin
from app.services.billing.revenue_protection import (
    apply_action,
    evaluate_revenue_protection_policies,
    revert_action,
    summarize_protection_status,
)
from app.services.compliance.financial_controls import evaluate_control_policy
from app.services.routing.commercial_report_export import sanitize_report_payload

router = APIRouter(
    tags=["admin", "billing", "revenue-protection"],
    dependencies=[Depends(require_admin)],
)


class RevenueProtectionPolicyUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    trigger_type: str
    severity_threshold: str = "medium"
    action_type: str
    scope_type: str
    scope_identifier: str | None = None
    mode: str = "report_only"
    cooldown_minutes: int = Field(default=60, ge=1, le=10080)
    metadata_json: dict[str, Any] | None = None


class RevenueProtectionEvaluateRequest(BaseModel):
    anomaly_ids: list[uuid.UUID] = Field(default_factory=list)


@router.get("/policies")
async def list_policies(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(CommercialRevenueProtectionPolicy).order_by(desc(CommercialRevenueProtectionPolicy.created_at)))
    return result.scalars().all()


@router.post("/policies", status_code=201)
async def create_policy(payload: RevenueProtectionPolicyUpsert, session: AsyncSession = Depends(get_db_session)):
    data = payload.model_dump()
    data["metadata_json"] = sanitize_report_payload(payload.metadata_json or {})
    policy = CommercialRevenueProtectionPolicy(**data)
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return policy


@router.patch("/policies/{policy_id}")
async def patch_policy(policy_id: uuid.UUID, payload: RevenueProtectionPolicyUpsert, session: AsyncSession = Depends(get_db_session)):
    policy = await session.get(CommercialRevenueProtectionPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    for key, value in payload.model_dump().items():
        setattr(policy, key, sanitize_report_payload(value) if key == "metadata_json" else value)
    await session.commit()
    await session.refresh(policy)
    return policy


@router.post("/evaluate")
async def evaluate_policies(payload: RevenueProtectionEvaluateRequest, session: AsyncSession = Depends(get_db_session)):
    return await evaluate_revenue_protection_policies(session, anomaly_ids=payload.anomaly_ids or None)


@router.get("/actions")
async def list_actions(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialRevenueProtectionAction).order_by(desc(CommercialRevenueProtectionAction.created_at)).limit(limit)
    if status:
        stmt = stmt.where(CommercialRevenueProtectionAction.status == status)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/actions/{action_id}/apply")
async def apply_action_endpoint(
    action_id: uuid.UUID,
    actor: str = Query(default="admin"),
    session: AsyncSession = Depends(get_db_session),
):
    action = await session.get(CommercialRevenueProtectionAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    decision = await evaluate_control_policy(
        session,
        control_area="revenue_protection",
        action_type="enforce_action",
        target_type="CommercialRevenueProtectionAction",
        target_id=action_id,
        actor=actor,
        package_type="revenue_protection",
        summary=f"Revenue protection apply action {action_id}",
        before_state={"status": action.status, "action_type": action.action_type},
        after_state={"status": "applied", "mode": action.mode},
        payload={"action_id": str(action_id), "actor": actor},
        related_ids={"action_id": str(action_id), "policy_id": str(action.policy_id)},
    )
    if decision.should_block and decision.approval_chain is not None:
        await session.commit()
        return {"status": "pending_approval", "approval_chain_id": str(decision.approval_chain.id)}
    return await apply_action(session, action)


@router.post("/actions/{action_id}/revert")
async def revert_action_endpoint(action_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    action = await session.get(CommercialRevenueProtectionAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return await revert_action(session, action)


@router.get("/status")
async def get_status(session: AsyncSession = Depends(get_db_session)):
    return await summarize_protection_status(session)
