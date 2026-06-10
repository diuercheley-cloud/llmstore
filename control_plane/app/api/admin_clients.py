import json
import uuid
from datetime import date, datetime

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import get_db_session as get_db
from app.models.core.api_key import ApiKey
from app.models.billing.billing_invoice import BillingInvoice
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.core.client_feature_block import ClientFeatureBlock
from app.models.billing.customer_payment import CustomerPayment
from app.models.core.generation_job import GenerationJob
from app.models.core.quota_counter import QuotaCounter
from app.models.rag.rag_document import RAGDocument
from app.models.rag.rag_document_chunk import RAGDocumentChunk
from app.models.rag.rag_usage_event import RagUsageEvent
from app.models.core.request_log import RequestLog
from app.models.core.security_event import SecurityEvent
from app.models.core.tts_usage_event import TtsUsageEvent
from app.models.core.usage_record import UsageRecord
from app.models.core.user_quota_override import UserQuotaOverride
from app.schemas.admin import (
    ClientBillingPlanPatch,
    ClientCreate,
    ClientPatch,
    ClientPurgeRequest,
    ClientRead,
)
from app.schemas.quality import SystemPromptUpdate
from app.services.auth import require_admin
from app.services.billing import ensure_default_billing_plans
from app.services.security_monitor import (
    log_security_event,
    suspend_client_for_security,
    unsuspend_client_for_security,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
settings = get_settings()


@router.post("/clients", response_model=ClientRead, status_code=201)
async def create_client(payload: ClientCreate, session: AsyncSession = Depends(get_db)):
    if settings.deployment_mode == "managed_control_plane" and not payload.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required in managed_control_plane mode"
        )
    plans = await ensure_default_billing_plans(session)
    client_data = payload.model_dump()
    billing_plan_id = client_data.get("billing_plan_id") or plans["free"].id
    if await session.get(BillingPlan, billing_plan_id) is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    client_data["billing_plan_id"] = billing_plan_id
    for field in ["allowed_models", "ip_allowlist", "ip_blocklist"]:
        if field in client_data:
            val = client_data.pop(field)
            client_data[f"{field}_json"] = json.dumps(val) if val is not None else None
    client = Client(**client_data)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


@router.get("/clients", response_model=list[ClientRead])
async def list_clients(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Client).where(Client.deleted_at.is_(None)).order_by(Client.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/clients/{client_id}", status_code=204)
async def delete_client(client_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    client = await session.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(status_code=404, detail="client not found")
    paid_invoices = await session.execute(
        select(BillingInvoice).where(BillingInvoice.client_id == client_id, BillingInvoice.status == "paid")
    )
    if paid_invoices.first() is not None:
        raise HTTPException(status_code=409, detail="cannot delete client with paid invoices")
    client.deleted_at = utc_now()
    keys = await session.execute(select(ApiKey).where(ApiKey.client_id == client_id))
    for key in keys.scalars().all():
        key.revoked_at = utc_now()
    await session.commit()


@router.post("/clients/{client_id}/purge", status_code=204)
async def purge_client(
    client_id: uuid.UUID,
    payload: ClientPurgeRequest,
    session: AsyncSession = Depends(get_db),
):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    is_demo = client.name == "demo-client" or (client.metadata_json and "demo" in client.metadata_json)
    if is_demo and not payload.allow_demo_client:
        raise HTTPException(status_code=403, detail="cannot purge demo client without allow_demo_client=true")
    await log_security_event(
        session,
        event_type="client.delete.requested",
        severity="high",
        title=f"Client purge requested: {client.name}",
        client_id=client_id,
        details=payload.model_dump()
    )
    try:
        if payload.anonymize_instead:
            client.name = f"anon-{client_id.hex[:8]}"
            client.description = "Anonymized client"
            client.system_prompt = None
            client.metadata_json = None
            client.ip_allowlist_json = None
            client.ip_blocklist_json = None
            client.deleted_at = utc_now()
            client.is_blocked = True
            if not payload.delete_invoices:
                invoices = await session.execute(select(BillingInvoice).where(BillingInvoice.client_id == client_id))
                for inv in invoices.scalars().all():
                    inv.note = "PII Removed"
            await session.execute(
                ApiKey.__table__.update()
                .where(ApiKey.client_id == client_id)
                .values(revoked_at=utc_now(), is_active=False)
            )
            await log_security_event(
                session,
                event_type="client.anonymized",
                severity="high",
                title=f"Client anonymized: {client_id}",
                client_id=client_id,
            )
        else:
            if payload.delete_usage:
                await session.execute(delete(UsageRecord).where(UsageRecord.client_id == client_id))
                await session.execute(delete(RequestLog).where(RequestLog.client_id == client_id))
                await session.execute(delete(QuotaCounter).where(QuotaCounter.client_id == client_id))
                await session.execute(delete(UserQuotaOverride).where(UserQuotaOverride.user_id == client_id))
                await session.execute(delete(GenerationJob).where(GenerationJob.client_id == client_id))
            if payload.delete_rag_metadata:
                await session.execute(delete(RAGDocumentChunk).where(RAGDocumentChunk.client_id == client_id))
                await session.execute(delete(RAGDocument).where(RAGDocument.client_id == client_id))
                await session.execute(delete(RagUsageEvent).where(RagUsageEvent.client_id == client_id))
            if payload.delete_tts_metadata:
                await session.execute(delete(TtsUsageEvent).where(TtsUsageEvent.client_id == client_id))
            await session.execute(delete(ClientFeatureBlock).where(ClientFeatureBlock.client_id == client_id))
            await session.execute(delete(ApiKey).where(ApiKey.client_id == client_id))
            if payload.delete_invoices:
                await session.execute(delete(CustomerPayment).where(CustomerPayment.client_id == client_id))
                await session.execute(delete(BillingInvoice).where(BillingInvoice.client_id == client_id))
            client.name = f"deleted-{client_id.hex[:8]}"
            client.deleted_at = utc_now()
            client.is_blocked = True
            client.description = "Deleted client (records preserved)"
            client.system_prompt = None
            client.metadata_json = None
            client.ip_allowlist_json = None
            client.ip_blocklist_json = None
            if payload.delete_audit_events:
                await session.execute(delete(SecurityEvent).where(SecurityEvent.client_id == client_id))
            await log_security_event(
                session,
                event_type="client.deleted",
                severity="high",
                title=f"Client purged: {client_id}",
                client_id=client_id,
            )
        await session.commit()
    except Exception as e:
        await session.rollback()
        await log_security_event(
            session,
            event_type="client.delete.failed",
            severity="critical",
            title=f"Client purge failed: {client_id}",
            client_id=client_id,
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"Secure delete failed: {str(e)}")


@router.patch("/clients/{client_id}", response_model=ClientRead)
async def patch_client(client_id: uuid.UUID, payload: ClientPatch, session: AsyncSession = Depends(get_db)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    patch_data = payload.model_dump(exclude_unset=True)
    if "billing_plan_id" in patch_data and patch_data["billing_plan_id"] is not None:
        if await session.get(BillingPlan, patch_data["billing_plan_id"]) is None:
            raise HTTPException(status_code=404, detail="billing plan not found")
    if "allowed_models" in patch_data:
        patch_data["allowed_models_json"] = json.dumps(patch_data.pop("allowed_models")) if patch_data["allowed_models"] is not None else None
    if "ip_allowlist" in patch_data:
        patch_data["ip_allowlist_json"] = json.dumps(patch_data.pop("ip_allowlist")) if patch_data["ip_allowlist"] is not None else None
    if "ip_blocklist" in patch_data:
        patch_data["ip_blocklist_json"] = json.dumps(patch_data.pop("ip_blocklist")) if patch_data["ip_blocklist"] is not None else None
    for key, value in patch_data.items():
        setattr(client, key, value)
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.patch("/clients/{client_id}/billing-plan", response_model=ClientRead)
async def set_client_billing_plan(
    client_id: uuid.UUID,
    payload: ClientBillingPlanPatch,
    session: AsyncSession = Depends(get_db),
):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    plan = await session.get(BillingPlan, payload.billing_plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    client.billing_plan_id = plan.id
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/clients/{client_id}/block", response_model=ClientRead)
async def block_client(client_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.is_blocked = True
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/security/clients/{client_id}/suspend", response_model=ClientRead)
async def suspend_client_security(client_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    await suspend_client_for_security(session, client, reason="manual_admin_security_action")
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/security/clients/{client_id}/unsuspend", response_model=ClientRead)
async def unsuspend_client_security(client_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    await unsuspend_client_for_security(session, client)
    await session.commit()
    await session.refresh(client)
    return client


@router.post("/clients/{client_id}/unblock", response_model=ClientRead)
async def unblock_client(client_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.is_blocked = False
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.patch("/clients/{client_id}/system-prompt", response_model=ClientRead)
async def patch_client_system_prompt(
    client_id: uuid.UUID,
    payload: SystemPromptUpdate,
    session: AsyncSession = Depends(get_db),
):
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    client.system_prompt = payload.system_prompt
    client.updated_at = utc_now()
    await session.commit()
    await session.refresh(client)
    return client


@router.get("/clients/export-data")
async def export_client_data(
    client_id: uuid.UUID | None = Query(None),
    email: str | None = Query(None),
    redact: bool = Query(True),
    session: AsyncSession = Depends(get_db),
):
    if not client_id and not email:
        raise HTTPException(status_code=400, detail="client_id or email must be provided")
    client = None
    if client_id:
        client = await session.get(Client, client_id)
    if not client and email:
        stmt = select(Client).where(Client.metadata_json.contains(f'"email": "{email}"'))
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="client not found")
    keys = (await session.execute(select(ApiKey).where(ApiKey.client_id == client.id))).scalars().all()
    invoices = (await session.execute(select(BillingInvoice).where(BillingInvoice.client_id == client.id))).scalars().all()
    usage = (await session.execute(select(UsageRecord).where(UsageRecord.client_id == client.id))).scalars().all()
    rag_docs = (await session.execute(select(RAGDocument).where(RAGDocument.client_id == client.id))).scalars().all()
    security_events = (await session.execute(select(SecurityEvent).where(SecurityEvent.client_id == client.id))).scalars().all()
    tts_events = (await session.execute(select(TtsUsageEvent).where(TtsUsageEvent.client_id == client.id))).scalars().all()
    export_payload = {
        "export_version": "1.1",
        "generated_at": utc_now().isoformat(),
        "client": {
            "id": str(client.id),
            "name": client.name,
            "description": client.description,
            "is_blocked": client.is_blocked,
            "billing_status": client.billing_status,
            "billing_plan_id": str(client.billing_plan_id) if client.billing_plan_id else None,
            "rate_limit_per_minute": client.rate_limit_per_minute,
            "daily_token_quota": client.daily_token_quota,
            "monthly_token_quota": client.monthly_token_quota,
            "max_context_tokens": client.max_context_tokens,
            "max_output_tokens": client.max_output_tokens,
            "created_at": client.created_at.isoformat(),
            "metadata": json.loads(client.metadata_json) if client.metadata_json else {},
        },
        "plan": None,
        "api_keys": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat(),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            }
            for k in keys
        ],
        "usage": [
            {
                "period_start": u.period_start.isoformat(),
                "period_type": u.period_type,
                "request_count": u.request_count,
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
                "embeddings_requests": u.embeddings_requests,
                "embeddings_tokens": u.embeddings_tokens,
                "created_at": u.created_at.isoformat(),
            }
            for u in usage
        ],
        "invoices": [
            {
                "id": str(i.id),
                "status": i.status,
                "total_amount": float(i.total_amount),
                "currency": i.currency,
                "period_start": i.period_start.isoformat(),
                "period_end": i.period_end.isoformat(),
                "due_at": i.due_at.isoformat() if i.due_at else None,
                "paid_at": i.paid_at.isoformat() if i.paid_at else None,
                "created_at": i.created_at.isoformat(),
            }
            for i in invoices
        ],
        "rag": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "original_filename": d.original_filename,
                "status": d.status,
                "file_size_bytes": d.file_size_bytes,
                "created_at": d.created_at.isoformat(),
            }
            for d in rag_docs
        ],
        "tts": [
            {
                "id": str(t.id),
                "chars_input": t.chars_input,
                "audio_file_id": t.audio_file_id,
                "audio_size_bytes": t.audio_size_bytes,
                "created_at": t.created_at.isoformat(),
            }
            for t in tts_events
        ],
        "audit_events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "severity": e.severity,
                "title": e.title,
                "created_at": e.created_at.isoformat(),
            }
            for e in security_events
        ],
        "model_policies": {
            "allowed_models": json.loads(client.allowed_models_json) if client.allowed_models_json else None,
            "ip_allowlist": json.loads(client.ip_allowlist_json) if client.ip_allowlist_json else None,
            "ip_blocklist": json.loads(client.ip_blocklist_json) if client.ip_blocklist_json else None,
        },
        "redaction": {
            "applied": redact,
            "redacted_fields": ["api_key_full"] if redact else [],
        },
    }
    if client.billing_plan_id:
        plan = await session.get(BillingPlan, client.billing_plan_id)
        if plan:
            export_payload["plan"] = {
                "id": str(plan.id),
                "code": plan.code,
                "name": plan.name,
                "description": plan.description,
            }
    if redact:
        if "metadata" in export_payload["client"]:
            meta = export_payload["client"]["metadata"]
            if "email" in meta:
                email_val = meta["email"]
                if "@" in email_val:
                    parts = email_val.split("@")
                    meta["email"] = f"{parts[0][0]}***@{parts[1]}"
            if "full_name" in meta:
                meta["full_name"] = "REDACTED"
    return export_payload
