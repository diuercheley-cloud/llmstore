# Owner: commercial-ops
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.commercial_cryptographic_receipts import (
    CommercialInferenceReceipt,
    CommercialInferenceReceiptLedgerEvent,
    CommercialInferenceReceiptVerificationReport,
)
from app.services.auth import require_admin
from app.services.inference.cryptographic_receipts import (
    build_receipt_chain,
    export_receipt,
    generate_inference_receipt,
    sign_receipt,
    summarize_receipt,
    validate_receipt_chain,
    verify_receipt,
)
from app.services.inference.receipt_verification import (
    detect_receipt_tampering,
    generate_verification_report,
)
from app.services.routing.commercial_report_export import sanitize_report_payload

router = APIRouter(
    tags=["admin", "cryptographic-receipts"],
    dependencies=[Depends(require_admin)],
)


class CreateReceiptPayload(BaseModel):
    reproducibility_record_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    client_id: str | None = None
    model_name: str | None = None
    backend_name: str | None = None
    provider: str | None = None
    prompt_hash: str = Field(min_length=1)
    response_hash: str = Field(min_length=1)
    request_payload_hash: str | None = None
    response_payload_hash: str | None = None
    runtime_snapshot_hash: str | None = None
    routing_decision_hash: str | None = None
    metadata_json: dict[str, Any] | None = None


class SignReceiptPayload(BaseModel):
    algorithm: str | None = None


def _serialize_receipt(item: CommercialInferenceReceipt) -> dict[str, Any]:
    return summarize_receipt(item)


def _serialize_ledger(item: CommercialInferenceReceiptLedgerEvent) -> dict[str, Any]:
    return sanitize_report_payload({
        "id": str(item.id),
        "receipt_id": str(item.receipt_id),
        "event_type": item.event_type,
        "summary": item.summary,
        "immutable_hash": (item.immutable_hash or "")[:16] or None,
        "created_at": item.created_at.isoformat(),
    })


def _serialize_report(item: CommercialInferenceReceiptVerificationReport) -> dict[str, Any]:
    return sanitize_report_payload({
        "id": str(item.id),
        "receipt_id": str(item.receipt_id),
        "verification_result": item.verification_result,
        "chain_valid": item.chain_valid,
        "signature_valid": item.signature_valid,
        "timestamp_valid": item.timestamp_valid,
        "runtime_match": item.runtime_match,
        "replay_match": item.replay_match,
        "drift_detected": item.drift_detected,
        "report_hash": (item.report_hash or "")[:16],
        "created_at": item.created_at.isoformat(),
    })


@router.get("/admin/inference/receipts")
async def list_receipts(
    limit: int = Query(default=100, ge=1, le=500),
    client_id: str | None = None,
    verification_status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialInferenceReceipt).order_by(desc(CommercialInferenceReceipt.created_at)).limit(limit)
    if client_id:
        stmt = stmt.where(CommercialInferenceReceipt.client_id == client_id)
    if verification_status:
        stmt = stmt.where(CommercialInferenceReceipt.verification_status == verification_status)
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_receipt(item) for item in rows]}


@router.get("/admin/inference/receipts/{receipt_id}")
async def get_receipt(receipt_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    item = await db.get(CommercialInferenceReceipt, receipt_id)
    if item is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    return _serialize_receipt(item)


@router.post("/admin/inference/receipts/{receipt_id}/verify")
async def verify_receipt_endpoint(
    receipt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    item = await db.get(CommercialInferenceReceipt, receipt_id)
    if item is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    report = await verify_receipt(db, item)
    await db.commit()
    return _serialize_report(report)


@router.post("/admin/inference/receipts/{receipt_id}/export")
async def export_receipt_endpoint(
    receipt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    item = await db.get(CommercialInferenceReceipt, receipt_id)
    if item is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    exported = await export_receipt(db, item, include_sensitive=False)
    await db.commit()
    return exported


@router.post("/admin/inference/receipts/validate-chain")
async def validate_chain_endpoint(
    receipt_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    item = await db.get(CommercialInferenceReceipt, receipt_id)
    if item is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    result = await validate_receipt_chain(db, item)
    await db.commit()
    return result


@router.get("/admin/inference/receipt-ledger")
async def list_receipt_ledger(
    limit: int = Query(default=100, ge=1, le=500),
    event_type: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialInferenceReceiptLedgerEvent).order_by(desc(CommercialInferenceReceiptLedgerEvent.created_at)).limit(limit)
    if event_type:
        stmt = stmt.where(CommercialInferenceReceiptLedgerEvent.event_type == event_type)
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_ledger(item) for item in rows]}


@router.get("/admin/inference/receipt-verification-reports")
async def list_verification_reports(
    limit: int = Query(default=100, ge=1, le=500),
    verification_result: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(CommercialInferenceReceiptVerificationReport).order_by(desc(CommercialInferenceReceiptVerificationReport.created_at)).limit(limit)
    if verification_result:
        stmt = stmt.where(CommercialInferenceReceiptVerificationReport.verification_result == verification_result)
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_report(item) for item in rows]}


@router.post("/admin/receipts/{id}/verify")
async def verify_receipt_endpoint_new(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    item = await db.get(CommercialInferenceReceipt, id)
    if item is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    report = await verify_receipt(db, item)
    await db.commit()
    return _serialize_report(report)


@router.get("/admin/receipts/public-key")
async def get_public_key_endpoint():
    from app.services.inference.cryptographic_receipts import get_public_key_pem, get_key_id
    try:
        return {"public_key": get_public_key_pem(), "key_id": get_key_id()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/receipts/{id}")
async def get_receipt_endpoint_new(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    item = await db.get(CommercialInferenceReceipt, id)
    if item is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    return _serialize_receipt(item)
