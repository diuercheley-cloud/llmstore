# Owner: platform-ops
import json
import os
import subprocess
import uuid
from typing import List, Optional

from app.services.runtime_dependencies import get_db_session
from app.models.core.client import Client
from app.models.commercial.sales_lead import SalesLead, SalesLeadNote
from app.schemas.sales import (
    LeadAdvanceStage,
    QuotePreviewRequest,
    QuotePreviewResponse,
    SalesLeadCreate,
    SalesLeadNoteCreate,
    SalesLeadUpdate,
)
from app.schemas.sales import SalesLead as SalesLeadSchema
from app.services.auth import AdminRole, require_admin_role
from app.services.billing.core import resolve_effective_plan_for_session
from app.core.time import utc_now
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin/sales", tags=["sales"])

@router.get("/leads", response_model=List[SalesLeadSchema])
async def list_leads(
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.READ))
):
    query = select(SalesLead).options(selectinload(SalesLead.timeline_notes)).order_by(desc(SalesLead.created_at))
    if status:
        query = query.where(SalesLead.status == status)
    
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/leads", response_model=SalesLeadSchema, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: SalesLeadCreate,
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.WRITE))
):
    lead = SalesLead(**lead_in.model_dump())
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    
    # Load timeline_notes for response model
    result = await session.execute(
        select(SalesLead).options(selectinload(SalesLead.timeline_notes)).where(SalesLead.id == lead.id)
    )
    return result.scalar_one()

@router.get("/leads/{id}", response_model=SalesLeadSchema)
async def get_lead(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.READ))
):
    result = await session.execute(
        select(SalesLead).options(selectinload(SalesLead.timeline_notes)).where(SalesLead.id == id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.patch("/leads/{id}", response_model=SalesLeadSchema)
async def update_lead(
    id: uuid.UUID,
    lead_in: SalesLeadUpdate,
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.WRITE))
):
    result = await session.execute(select(SalesLead).where(SalesLead.id == id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    await session.commit()
    await session.refresh(lead)
    
    result = await session.execute(
        select(SalesLead).options(selectinload(SalesLead.timeline_notes)).where(SalesLead.id == id)
    )
    return result.scalar_one()

@router.delete("/leads/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.WRITE))
):
    result = await session.execute(select(SalesLead).where(SalesLead.id == id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    await session.delete(lead)
    await session.commit()
    return None

@router.post("/leads/{id}/notes", response_model=SalesLeadSchema)
async def add_lead_note(
    id: uuid.UUID,
    note_in: SalesLeadNoteCreate,
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.WRITE))
):
    result = await session.execute(select(SalesLead).where(SalesLead.id == id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    note = SalesLeadNote(lead_id=id, content=note_in.content)
    session.add(note)
    await session.commit()
    
    result = await session.execute(
        select(SalesLead).options(selectinload(SalesLead.timeline_notes)).where(SalesLead.id == id)
    )
    return result.scalar_one()

@router.post("/leads/{id}/advance-stage", response_model=SalesLeadSchema)
async def advance_lead_stage(
    id: uuid.UUID,
    advance_in: LeadAdvanceStage,
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.WRITE))
):
    result = await session.execute(select(SalesLead).where(SalesLead.id == id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    old_status = lead.status
    lead.status = advance_in.new_status
    
    note_content = f"Estágio alterado de {old_status} para {advance_in.new_status}."
    if advance_in.note:
        note_content += f" Observação: {advance_in.note}"
    
    note = SalesLeadNote(lead_id=id, content=note_content)
    session.add(note)
    
    await session.commit()
    
    result = await session.execute(
        select(SalesLead).options(selectinload(SalesLead.timeline_notes)).where(SalesLead.id == id)
    )
    return result.scalar_one()

@router.post("/quote-preview", response_model=QuotePreviewResponse)
async def quote_preview(
    request: QuotePreviewRequest,
    _role: AdminRole = Depends(require_admin_role(AdminRole.READ))
):
    # Use absolute path for robustness
    script_path = "/home/kleber/llm-inference-stack/scripts/generate-local-quote.sh"
    cmd = [
        script_path,
        "--company-name", request.company_name,
        "--plan", request.plan,
        "--users", str(request.users),
        "--models", str(request.models),
        "--responses", str(request.responses),
        "--support-hours", str(request.support_hours),
        "--custom-integration-hours", str(request.custom_integration_hours),
        "--discount-percent", str(request.discount_percent)
    ]
    if request.rag: cmd.append("--rag")
    if request.tts: cmd.append("--tts")
    if request.embeddings: cmd.append("--embeddings")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        json_path = None
        for line in result.stdout.splitlines():
            if line.startswith("JSON: "):
                json_path = line.replace("JSON: ", "").strip()
                break
        
        if not json_path or not os.path.exists(json_path):
            raise HTTPException(status_code=500, detail="Quote JSON file not found in script output")
            
        with open(json_path, 'r') as f:
            return json.load(f)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error generating quote: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly-report-preview")
async def monthly_report_preview(
    client_id: uuid.UUID = Query(...),
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    include_technical_details: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
    _role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    from datetime import date

    from app.models.billing.billing_invoice import BillingInvoice
    from app.models.billing.billing_plan import BillingPlan
    from app.models.core.quota_counter import QuotaCounter
    from app.models.core.request_log import RequestLog
    from app.models.core.usage_record import UsageRecord
    from app.services.rag_usage import get_rag_usage_and_limits

    # Parse month
    year, m = month.split("-")
    period_start = date(int(year), int(m), 1)
    if m == "12":
        period_end = date(int(year) + 1, 1, 1)
    else:
        period_end = date(int(year), int(m) + 1, 1)

    # Get client info
    result = await session.execute(
        select(Client)
        .options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules))
        .where(Client.id == client_id)
    )
    client = result.unique().scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Resolve plan
    effective_plan = await resolve_effective_plan_for_session(session, client)
    plan_code = effective_plan.code or "unknown"
    plan_name = effective_plan.name or plan_code

    # Get usage counters for the month
    result = await session.execute(
        select(QuotaCounter).where(
            QuotaCounter.client_id == client_id,
            QuotaCounter.period_type == "monthly",
            QuotaCounter.period_start == period_start,
        )
    )
    monthly_counter = result.scalar_one_or_none()

    result = await session.execute(
        select(UsageRecord).where(
            UsageRecord.client_id == client_id,
            UsageRecord.period_type == "monthly",
            UsageRecord.period_start == period_start,
        )
    )
    monthly_usage = result.scalar_one_or_none()

    # Chat tokens from RequestLog
    result = await session.execute(
        select(
            func.count(RequestLog.id).label("requests"),
            func.coalesce(func.sum(RequestLog.prompt_tokens_estimated), 0).label("prompt_tokens"),
            func.coalesce(func.sum(RequestLog.completion_tokens_estimated), 0).label("completion_tokens"),
            func.coalesce(func.avg(RequestLog.latency_ms), 0).label("avg_latency"),
            func.count(RequestLog.id).filter(RequestLog.http_status >= 400).label("errors"),
            func.count(RequestLog.id).filter(RequestLog.http_status >= 500).label("server_errors"),
        ).where(
            RequestLog.client_id == client_id,
            RequestLog.created_at >= period_start,
            RequestLog.created_at < period_end,
        )
    )
    row = result.mappings().first() or {}
    requests = int(row.get("requests", 0) or 0)
    prompt_tokens = int(row.get("prompt_tokens", 0) or 0)
    completion_tokens = int(row.get("completion_tokens", 0) or 0)
    total_tokens = prompt_tokens + completion_tokens
    avg_latency = round(float(row.get("avg_latency", 0) or 0), 2)
    errors = int(row.get("errors", 0) or 0)
    server_errors = int(row.get("server_errors", 0) or 0)

    # Count by endpoint
    result = await session.execute(
        select(
            RequestLog.endpoint,
            func.count(RequestLog.id).label("count"),
        ).where(
            RequestLog.client_id == client_id,
            RequestLog.created_at >= period_start,
            RequestLog.created_at < period_end,
        ).group_by(RequestLog.endpoint)
    )
    endpoint_counts = {r.endpoint: r.count for r in result.all()}

    # Rate limit / quota events
    result = await session.execute(
        select(func.count(RequestLog.id)).where(
            RequestLog.client_id == client_id,
            RequestLog.created_at >= period_start,
            RequestLog.created_at < period_end,
            RequestLog.http_status == 429,
        )
    )
    rate_limit_events = result.scalar() or 0

    # Embeddings usage
    embeddings_requests = monthly_usage.embeddings_requests if monthly_usage else 0
    embeddings_tokens = monthly_usage.embeddings_tokens if monthly_usage else 0
    if monthly_counter:
        embeddings_requests = max(embeddings_requests, monthly_counter.used_embeddings_requests)
        embeddings_tokens = max(embeddings_tokens, monthly_counter.used_embeddings_tokens)

    # TTS usage
    tts_chars = monthly_counter.used_tts_chars if monthly_counter else 0

    # RAG usage
    rag_usage = await get_rag_usage_and_limits(session, client)
    rag_queries = rag_usage.get("queries_month", 0) if isinstance(rag_usage, dict) else 0
    rag_docs = rag_usage.get("doc_count", 0) if isinstance(rag_usage, dict) else 0

    # Invoices for the period
    result = await session.execute(
        select(BillingInvoice).where(
            BillingInvoice.client_id == client_id,
            BillingInvoice.period_start >= period_start,
            BillingInvoice.period_start < period_end,
        ).order_by(BillingInvoice.created_at.desc())
    )
    invoices = result.scalars().all()
    invoice_list = []
    total_billed = 0.0
    total_paid = 0.0
    total_pending = 0.0
    for inv in invoices:
        amount = float(inv.total_amount)
        total_billed += amount
        if inv.status == "paid":
            total_paid += amount
        elif inv.status in ("pending", "overdue"):
            total_pending += amount
        invoice_list.append({
            "id": str(inv.id),
            "status": inv.status,
            "total_amount": amount,
            "currency": inv.currency or "USD",
            "period_start": inv.period_start.isoformat() if inv.period_start else None,
            "period_end": inv.period_end.isoformat() if inv.period_end else None,
            "due_at": inv.due_at.isoformat() if inv.due_at else None,
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        })

    # Limits
    limits = {
        "monthly_token_quota": effective_plan.monthly_token_quota,
        "daily_token_quota": effective_plan.daily_token_quota,
        "rate_limit_per_minute": effective_plan.rate_limit_per_minute,
        "tts_chars_per_month": effective_plan.tts_chars_per_month,
        "embeddings_monthly_requests_limit": effective_plan.embeddings_monthly_requests_limit,
        "embeddings_monthly_tokens_limit": effective_plan.embeddings_monthly_tokens_limit,
    }

    # Recommendations
    recommendations = []
    usage_pct = (total_tokens / effective_plan.monthly_token_quota * 100) if effective_plan.monthly_token_quota > 0 else 0
    if usage_pct < 20:
        recommendations.append({
            "type": "downgrade",
            "reason": f"Utilização de apenas {usage_pct:.0f}% da cota mensal. Considere revisar o plano para reduzir custos.",
        })
    elif usage_pct > 80:
        recommendations.append({
            "type": "upgrade",
            "reason": f"Utilização de {usage_pct:.0f}% da cota mensal. Considere upgrade de plano para evitar sobrecarga.",
        })
    if errors > requests * 0.05:
        recommendations.append({
            "type": "review",
            "reason": f"Taxa de erro elevada ({errors}/{requests}). Verifique logs e configuração.",
        })
    if rate_limit_events > 0:
        recommendations.append({
            "type": "rate_limit",
            "reason": f"{rate_limit_events} eventos de rate limit. Considere aumentar o limite ou otimizar chamadas.",
        })
    if not recommendations:
        recommendations.append({
            "type": "ok",
            "reason": "Nenhuma ação recomendada no momento.",
        })

    # Build report
    report = {
        "generated_at": utc_now().isoformat(),
        "client": {
            "id": str(client.id),
            "name": client.name,
            "plan_code": plan_code,
            "plan_name": plan_name,
            "billing_status": client.billing_status,
        },
        "period": {
            "month": month,
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "limits": limits,
        "usage": {
            "chat": {
                "requests": requests,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "tokens_pct": round(usage_pct, 1),
            },
            "responses": endpoint_counts.get("/v1/responses", 0),
            "embeddings": {
                "requests": embeddings_requests,
                "tokens": embeddings_tokens,
            },
            "rag": {
                "queries": rag_queries,
                "documents": rag_docs,
            },
            "tts": {
                "chars": tts_chars,
            },
            "requests": {
                "total": requests,
                "by_endpoint": endpoint_counts,
            },
            "errors": {
                "total": errors,
                "server_errors": server_errors,
                "rate_limit_events": rate_limit_events,
            },
            "performance": {
                "avg_latency_ms": avg_latency,
            },
        },
        "billing": {
            "invoices": invoice_list,
            "totals": {
                "billed": round(total_billed, 2),
                "paid": round(total_paid, 2),
                "pending": round(total_pending, 2),
            },
            "payment_status": client.billing_status,
        },
        "recommendations": recommendations,
        "disclaimer": "This report is generated for reference only. PSP/PIX real payment processing is NOT available in local mode. Consult legal before any financial decision.",
    }

    if include_technical_details:
        report["technical_details"] = {
            "plan_details": {
                "code": plan_code,
                "name": plan_name,
                "max_context_tokens": effective_plan.max_context_tokens,
                "max_output_tokens": effective_plan.max_output_tokens,
                "allow_streaming": effective_plan.allow_streaming,
                "features": {
                    "rag_enabled": effective_plan.rag_enabled,
                    "tts_enabled": effective_plan.tts_enabled,
                    "embeddings_enabled": effective_plan.embeddings_enabled,
                    "responses_enabled": effective_plan.responses_enabled,
                },
            },
            "quotas": {
                "daily_used": int(monthly_usage.request_count) if monthly_usage else 0,
                "daily_limit": effective_plan.daily_token_quota,
                "monthly_used": total_tokens,
                "monthly_limit": effective_plan.monthly_token_quota,
            },
        }

    return report
