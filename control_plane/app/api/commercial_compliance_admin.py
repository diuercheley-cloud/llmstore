# Owner: commercial-ops
from __future__ import annotations

import uuid
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from app.db.session import get_db_session
from app.models.commercial_compliance import (
    CommercialApprovalChain,
    CommercialControlAttestation,
    CommercialControlException,
    CommercialControlPolicy,
    CommercialEvidencePackage,
    CommercialOperationalControl,
    CommercialOperationalEvidence,
    CommercialOperationalReview,
)
from app.services.auth import require_admin
from app.services.compliance.financial_controls import (
    ControlViolationError,
    accept_exception,
    approve_action,
    build_audit_report,
    create_attestation,
    list_controls_needing_review,
    open_exception,
    record_control_event,
    reject_action,
    remediate_exception,
    render_audit_report_csv,
    render_audit_report_html,
    summarize_controls,
)
from app.services.compliance.operational_controls import (
    add_operational_evidence,
    assign_review_reviewer,
    complete_review,
    create_control,
    detect_overdue_reviews,
    detect_stale_evidence,
    evaluate_control_effectiveness,
    summarize_operational_controls,
    update_control,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/compliance",
    tags=["admin", "compliance"],
    dependencies=[Depends(require_admin)],
)


class ControlPolicyPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    control_area: str
    action_type: str
    requires_approval: bool = False
    required_approver_count: int = Field(default=1, ge=1, le=10)
    segregation_required: bool = True
    evidence_required: bool = True
    review_frequency: str = "quarterly"
    metadata_json: dict[str, Any] | None = None


class ApprovalDecisionPayload(BaseModel):
    actor: str = Field(min_length=1, max_length=128)
    notes: str | None = None
    reason: str | None = None


class AttestationPayload(BaseModel):
    client_id: uuid.UUID | None = None
    control_policy_id: uuid.UUID
    attestation_period_start: date
    attestation_period_end: date
    attested_by: str = Field(min_length=1, max_length=128)
    status: str = "pending"
    notes: str | None = None
    evidence_package_id: uuid.UUID | None = None


class ExceptionPayload(BaseModel):
    client_id: uuid.UUID | None = None
    control_policy_id: uuid.UUID | None = None
    exception_type: str
    severity: str = "medium"
    description: str
    remediation_plan: str | None = None
    owner: str | None = None
    due_at: datetime | None = None


class ExceptionDecisionPayload(BaseModel):
    actor: str = Field(min_length=1, max_length=128)
    remediation_plan: str | None = None


class OperationalControlPayload(BaseModel):
    control_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    category: str
    description: str | None = None
    owner_id: uuid.UUID | None = None
    owner_email: str | None = None
    review_frequency: str = "quarterly"
    evidence_sla_days: int | None = Field(default=None, ge=1, le=3650)
    enabled: bool = True
    metadata_json: dict[str, Any] | None = None


class OperationalControlPatchPayload(BaseModel):
    control_code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    description: str | None = None
    owner_id: uuid.UUID | None = None
    owner_email: str | None = None
    review_frequency: str | None = None
    evidence_sla_days: int | None = Field(default=None, ge=1, le=3650)
    enabled: bool | None = None
    metadata_json: dict[str, Any] | None = None


class OperationalEvidencePayload(BaseModel):
    control_id: uuid.UUID
    evidence_type: str
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    evidence_json: dict[str, Any] | None = None
    collected_at: datetime | None = None
    expires_at: datetime | None = None


class OperationalReviewCompletePayload(BaseModel):
    reviewed_by: str | None = Field(default=None, min_length=1, max_length=255)
    findings: str | None = None
    recommendations: str | None = None
    evidence_package_id: uuid.UUID | None = None
    reviewer_assignment: str | None = Field(default=None, min_length=1, max_length=255)
    create_policy_attestation: bool = False


class OperationalExceptionLinkPayload(BaseModel):
    control_id: uuid.UUID
    exception_id: uuid.UUID
    linkage_reason: str | None = None
    remediation_status: str = "planned"


@router.get("/controls")
async def get_controls(
    due_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialControlPolicy).order_by(desc(CommercialControlPolicy.created_at))
    controls = list((await db.execute(stmt)).scalars().all())
    reviews = await list_controls_needing_review(db)
    if due_only:
        reviews = [item for item in reviews if item["due"]]
    return {
        "summary": await summarize_controls(db),
        "controls": controls,
        "reviews": reviews,
    }


@router.post("/controls", status_code=201)
async def post_control(payload: ControlPolicyPayload, db: AsyncSession = Depends(get_db_session)):
    item = CommercialControlPolicy(**sanitize_report_payload(payload.model_dump()))
    db.add(item)
    await record_control_event(db, action="compliance_control_created", status="created", payload=payload.model_dump(), result={"control_policy_id": str(item.id)})
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/approval-chains")
async def get_approval_chains(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialApprovalChain).order_by(desc(CommercialApprovalChain.created_at)).limit(limit)
    if status:
        stmt = stmt.where(CommercialApprovalChain.status == status)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/approval-chains/{chain_id}/approve")
async def post_approval_chain_approve(
    chain_id: uuid.UUID,
    payload: ApprovalDecisionPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        chain = await approve_action(db, chain_id=chain_id, approver=payload.actor, notes=payload.notes)
        await record_control_event(db, action="compliance_approval_approved", status=chain.status, payload={"chain_id": str(chain_id), "actor": payload.actor}, result={"status": chain.status})
        await db.commit()
        await db.refresh(chain)
        return chain
    except ControlViolationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/approval-chains/{chain_id}/reject")
async def post_approval_chain_reject(
    chain_id: uuid.UUID,
    payload: ApprovalDecisionPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        chain = await reject_action(db, chain_id=chain_id, approver=payload.actor, reason=payload.reason or payload.notes or "rejected")
        await record_control_event(db, action="compliance_approval_rejected", status=chain.status, payload={"chain_id": str(chain_id), "actor": payload.actor}, result={"status": chain.status})
        await db.commit()
        await db.refresh(chain)
        return chain
    except ControlViolationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/evidence-packages")
async def get_evidence_packages(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialEvidencePackage).order_by(desc(CommercialEvidencePackage.created_at)).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/attestations")
async def get_attestations(
    status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialControlAttestation).order_by(desc(CommercialControlAttestation.created_at))
    if status:
        stmt = stmt.where(CommercialControlAttestation.status == status)
    return {
        "items": list((await db.execute(stmt)).scalars().all()),
        "reviews": await list_controls_needing_review(db),
    }


@router.post("/attestations", status_code=201)
async def post_attestation(payload: AttestationPayload, db: AsyncSession = Depends(get_db_session)):
    item = await create_attestation(db, **payload.model_dump())
    await record_control_event(db, action="compliance_attestation_created", status=item.status, payload=payload.model_dump(mode="json"), result={"attestation_id": str(item.id)})
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/exceptions")
async def get_exceptions(
    status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialControlException).order_by(desc(CommercialControlException.created_at))
    if status:
        stmt = stmt.where(CommercialControlException.status == status)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/exceptions", status_code=201)
async def post_exception(payload: ExceptionPayload, db: AsyncSession = Depends(get_db_session)):
    item = await open_exception(db, **payload.model_dump())
    await record_control_event(db, action="compliance_exception_opened", status=item.status, payload=payload.model_dump(mode="json"), result={"exception_id": str(item.id)})
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/exceptions/{exception_id}/accept")
async def post_exception_accept(
    exception_id: uuid.UUID,
    payload: ExceptionDecisionPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        item = await accept_exception(db, exception_id=exception_id, actor=payload.actor, remediation_plan=payload.remediation_plan)
        await record_control_event(db, action="compliance_exception_accepted", status=item.status, payload={"exception_id": str(exception_id), "actor": payload.actor}, result={"status": item.status})
        await db.commit()
        await db.refresh(item)
        return item
    except ControlViolationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/exceptions/{exception_id}/remediate")
async def post_exception_remediate(
    exception_id: uuid.UUID,
    payload: ExceptionDecisionPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        item = await remediate_exception(db, exception_id=exception_id, actor=payload.actor, remediation_plan=payload.remediation_plan)
        await record_control_event(db, action="compliance_exception_remediated", status=item.status, payload={"exception_id": str(exception_id), "actor": payload.actor}, result={"status": item.status})
        await db.commit()
        await db.refresh(item)
        return item
    except ControlViolationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit-report")
async def get_audit_report(
    format: str = Query(default="json", pattern="^(json|csv|html)$"),
    db: AsyncSession = Depends(get_db_session),
):
    report = await build_audit_report(db)
    if format == "json":
        return JSONResponse(report)
    if format == "csv":
        return Response(render_audit_report_csv(report), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=compliance_audit_report.csv"})
    return HTMLResponse(render_audit_report_html(report))


@router.get("/operational-controls")
async def get_operational_controls(db: AsyncSession = Depends(get_db_session)):
    return await summarize_operational_controls(db)


@router.post("/operational-controls", status_code=201)
async def post_operational_control(payload: OperationalControlPayload, db: AsyncSession = Depends(get_db_session)):
    item = await create_control(db, **payload.model_dump())
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/operational-controls/{id}")
async def patch_operational_control(
    id: uuid.UUID,
    payload: OperationalControlPatchPayload,
    db: AsyncSession = Depends(get_db_session),
):
    item = await update_control(db, id, **payload.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/operational-controls/reviews")
async def get_operational_reviews(
    status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    reviews = list((await db.execute(select(CommercialOperationalReview).order_by(desc(CommercialOperationalReview.created_at)))).scalars().all())
    if status:
        reviews = [item for item in reviews if item.status == status]
    return {
        "items": reviews,
        "overdue": await detect_overdue_reviews(db),
    }


@router.post("/operational-controls/reviews/{id}/complete")
async def post_operational_review_complete(
    id: uuid.UUID,
    payload: OperationalReviewCompletePayload,
    db: AsyncSession = Depends(get_db_session),
):
    if payload.reviewer_assignment:
        await assign_review_reviewer(db, review_id=id, reviewed_by=payload.reviewer_assignment)
    review = await complete_review(
        db,
        review_id=id,
        reviewed_by=payload.reviewed_by or payload.reviewer_assignment,
        findings=payload.findings,
        recommendations=payload.recommendations,
        evidence_package_id=payload.evidence_package_id,
        create_policy_attestation=payload.create_policy_attestation,
    )
    await db.commit()
    await db.refresh(review)
    return review


@router.get("/operational-controls/evidence")
async def get_operational_evidence(
    freshness_status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    items = list((await db.execute(select(CommercialOperationalEvidence).order_by(desc(CommercialOperationalEvidence.created_at)))).scalars().all())
    if freshness_status:
        items = [item for item in items if item.freshness_status == freshness_status]
    return {
        "items": items,
        "stale": await detect_stale_evidence(db),
    }


@router.post("/operational-controls/evidence", status_code=201)
async def post_operational_evidence(payload: OperationalEvidencePayload, db: AsyncSession = Depends(get_db_session)):
    item = await add_operational_evidence(db, **payload.model_dump())
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/operational-controls/overdue")
async def get_operational_overdue(db: AsyncSession = Depends(get_db_session)):
    stale = await detect_stale_evidence(db)
    overdue_reviews = await detect_overdue_reviews(db)
    ineffective_controls = []
    controls = list((await db.execute(select(CommercialOperationalControl).where(CommercialOperationalControl.enabled.is_(True)))).scalars().all())
    for control in controls:
        control = await evaluate_control_effectiveness(db, control.id)
        if control.effectiveness_status == "ineffective":
            ineffective_controls.append(control)
    await db.commit()
    return {
        "stale_evidence": stale,
        "overdue_reviews": overdue_reviews,
        "ineffective_controls": ineffective_controls,
    }


@router.get("/operational-controls/effectiveness")
async def get_operational_effectiveness(db: AsyncSession = Depends(get_db_session)):
    controls = list((await db.execute(select(CommercialOperationalControl).order_by(CommercialOperationalControl.control_code.asc()))).scalars().all())
    items = []
    for control in controls:
        updated = await evaluate_control_effectiveness(db, control.id)
        items.append(updated)
    await db.commit()
    return items


from app.services.compliance.audit_pack import AuditPackService


@router.post("/audit-pack/generate")
async def post_generate_audit_pack(
    standard: str = Query(default="soc2", pattern="^(soc2|iso27001)$"),
    db: AsyncSession = Depends(get_db_session),
):
    svc = AuditPackService(db)
    return await svc.generate_pack(standard)


@router.get("/audit-pack/{id}")
async def get_audit_pack(
    id: uuid.UUID,
    standard: str = Query(default="soc2", pattern="^(soc2|iso27001)$"),
):
    base_path = Path("compliance/audit-packs") / standard / str(id)
    if not base_path.exists():
        raise HTTPException(status_code=404, detail="Audit pack not found")
        
    # Return manifest and list of evidence files
    manifest_path = base_path / "manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    files = [f.name for f in base_path.iterdir() if f.is_file()]
    return {"manifest": manifest, "files": files}
