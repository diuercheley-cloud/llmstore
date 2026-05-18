import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import HTMLResponse, JSONResponse

from app.api.client import _chat_with_fallback, _error_message_for_log, _backend_errors_for_log
from app.core.security import short_prefix
from app.core.time import utc_now
from app.utils.validation import validate_params
from app.api.deps import get_inference_proxy
from app.db.session import get_db_session, get_redis
from app.models.billing_invoice import BillingInvoice
from app.models.client import Client
from app.models.customer_payment import CustomerPayment
from app.schemas.inference import ChatCompletionRequest, PortalTestChatRequest, OnboardingEventRequest, PortalWalletRechargeRequest
from app.schemas.payments import WalletTopUpCreate
from app.services.audit import log_request
from app.services.auth import require_client
from app.services.billing import (
    build_invoice_preview,
    estimate_request_cost,
    get_current_usage_snapshot,
    refresh_billing_statuses,
    resolve_effective_plan,
    serialize_invoice,
)
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import resolve_requested_model, get_effective_allowed_models
from app.services.providers.registry import get_provider
from app.services.quota import month_start, ensure_quota, record_usage, QuotaExceeded
from app.services.tts_usage import get_tts_usage_and_limits
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.services.response_cache import build_chat_cache_key, lookup_exact_cache, store_exact_cache
from app.utils.request_summary import summarize_chat_request
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text

from app.models.billing_plan import BillingPlan
from app.models.pricing_rule import PricingRule
from app.models.ai_wallet import AiWallet, AiWalletTransaction
from app.models.api_key import ApiKey
from app.models.request_log import RequestLog
from app.models.request_financial import RequestFinancial
from app.models.model_registry import ModelRegistry
from app.services.models.model_provenance import summarize_model_provenance
from app.services.models.runtime_attestation import serialize_runtime_attestation
from app.services.models.signed_model_registry import get_model_trust_state
from app.models.sales_lead import SalesLead
from app.schemas.public import PortalUpgradeRequest
from app.schemas.admin import ApiKeyCreate, ApiKeyCreated
from app.services.public_onboarding import list_public_plans
from app.core.security import generate_api_key, hash_secret, short_prefix
from app.services.payment_topups import create_topup_intent, list_topup_intents, serialize_topup

from app.models.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.models.commercial_billing_dispute import CommercialBillingDispute
from app.models.commercial_audit_portal import CommercialPortalSavedReport
from app.models.commercial_rag_vault import (
    CommercialRAGDocument,
    CommercialRAGLegalHold,
    CommercialRAGPoisoningAlert,
    CommercialRAGRetrievalAudit,
    CommercialRAGVault,
)
from app.models.commercial_cryptographic_receipts import (
    CommercialInferenceReceipt,
    CommercialInferenceReceiptVerificationReport,
)
from app.models.commercial_model_supply_chain import CommercialModelIntegrityScan, CommercialRuntimeModelAttestation
from app.models.commercial_sovereign_governance import (
    CommercialAirgapSyncPackage,
    CommercialHardwareAttestationRecord,
    CommercialOfflineRevocationList,
)
from app.schemas.billing import BillingDisputeOpen, BillingDisputeRead
from app.services.billing.dispute_management import DisputeManagementService
from app.services.compliance.customer_audit_portal import (
    generate_customer_audit_report,
    list_customer_access_logs,
    list_customer_approval_chains,
    list_customer_attestations,
    list_customer_evidence_packages,
    list_customer_exceptions,
    list_customer_operational_controls,
    list_customer_operational_evidence,
    list_customer_operational_reviews,
    list_customer_saved_reports,
    log_portal_access,
    validate_portal_resource_access,
)
from app.services.compliance.portal_rbac import get_portal_capabilities, require_portal_permission

router = APIRouter(tags=["portal"])


class PortalAuditReportGeneratePayload(BaseModel):
    report_type: str = Field(pattern="^(audit|evidence|approval_chain|attestation|exception|financial_summary)$")
    period_start: date
    period_end: date
    export_format: str = Field(default="json", pattern="^(json|csv|html|pdf)$")
    filters_json: dict | None = None


def _portal_request_identity(request: Request) -> dict[str, str | None]:
    return {
        "actor_id": getattr(request.state, "portal_actor_id", None),
        "actor_name": getattr(request.state, "portal_actor_name", None),
        "actor_email": request.headers.get("X-Portal-Actor-Email"),
    }


def _portal_request_ip(request: Request) -> str | None:
    if getattr(request.state, "source_ip", None):
        return request.state.source_ip
    if request.client:
        return request.client.host
    return None


def _audit_action_from_filters(
    *,
    period_start: date | None = None,
    period_end: date | None = None,
    status: str | None = None,
    severity: str | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    action: str | None = None,
) -> str:
    if action:
        return "filter"
    if actor:
        return "search"
    if any([period_start, period_end, status, severity, control_area]):
        return "filter"
    return "view"


async def _log_portal_read(
    session: AsyncSession,
    request: Request,
    client: Client,
    *,
    resource_type: str,
    action: str,
    resource_id: str | None = None,
    metadata_json: dict | None = None,
) -> None:
    identity = _portal_request_identity(request)
    await log_portal_access(
        session,
        client_id=client.id,
        actor_id=identity["actor_id"],
        actor_email=identity["actor_email"],
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        ip_address=_portal_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata_json=metadata_json,
    )


def _start_of_day_utc() -> datetime:
    now = utc_now()
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def _portal_visible_wallet_transaction(tx: AiWalletTransaction) -> dict:
    return {
        "id": str(tx.id),
        "type": tx.type,
        "amount_brl": float(tx.amount_brl),
        "balance_after_brl": float(tx.balance_after_brl),
        "reference_type": tx.reference_type,
        "reference_id": tx.reference_id,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }


def _build_invoice_html(invoice: dict, client: Client) -> str:
    payments = invoice.get("payments") or []
    payment_rows = "".join(
        f"""
        <tr>
          <td>{payment['status']}</td>
          <td>{payment['amount']:.2f} {payment['currency']}</td>
          <td>{payment.get('payment_method') or '-'}</td>
          <td>{payment.get('paid_at') or '-'}</td>
        </tr>
        """
        for payment in payments
    ) or '<tr><td colspan="4">Nenhum pagamento registrado.</td></tr>'

    return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <title>Invoice {invoice['id']}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; color: #0f172a; }}
      h1, h2 {{ margin-bottom: 8px; }}
      .muted {{ color: #64748b; }}
      .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 24px 0; }}
      .card {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      th, td {{ border-bottom: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
      th {{ background: #f8fafc; }}
      code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Fatura</h1>
    <div class="muted">Cliente: {client.name}</div>
    <div class="muted">Invoice ID: <code>{invoice['id']}</code></div>
    <div class="grid">
      <div class="card">
        <h2>Status</h2>
        <div>{invoice['status']}</div>
        <div class="muted">Vencimento: {invoice.get('due_at') or '-'}</div>
        <div class="muted">Período: {invoice['period_start']} até {invoice['period_end']}</div>
      </div>
      <div class="card">
        <h2>Valores</h2>
        <div>Mensalidade: {invoice['monthly_price']:.2f} {invoice['currency']}</div>
        <div>Excedente: {invoice['overage_cost']:.2f} {invoice['currency']}</div>
        <div><strong>Total: {invoice['total_amount']:.2f} {invoice['currency']}</strong></div>
      </div>
    </div>
    <h2>Consumo</h2>
    <div>Tokens incluídos: {invoice['included_tokens']}</div>
    <div>Tokens usados: {invoice['used_tokens']}</div>
    <div>Tokens excedentes: {invoice['overage_tokens']}</div>
    <div>Instruções de pagamento: {invoice.get('payment_instructions') or 'pagamento manual/local'}</div>
    <h2>Pagamentos</h2>
    <table>
      <thead>
        <tr><th>Status</th><th>Valor</th><th>Método</th><th>Pago em</th></tr>
      </thead>
      <tbody>{payment_rows}</tbody>
    </table>
  </body>
</html>"""


async def _portal_usage_request_totals(session: AsyncSession, client_id: UUID) -> dict[str, int]:
    today_start = _start_of_day_utc()
    month_start_dt = datetime.combine(month_start(date.today()), datetime.min.time(), tzinfo=timezone.utc)
    today_stmt = select(
        func.count(RequestLog.id),
        func.coalesce(func.sum(RequestLog.prompt_tokens_estimated + RequestLog.completion_tokens_estimated), 0),
    ).where(RequestLog.client_id == client_id, RequestLog.created_at >= today_start)
    month_stmt = select(
        func.count(RequestLog.id),
        func.coalesce(func.sum(RequestLog.prompt_tokens_estimated + RequestLog.completion_tokens_estimated), 0),
    ).where(RequestLog.client_id == client_id, RequestLog.created_at >= month_start_dt)
    today_row = (await session.execute(today_stmt)).one()
    month_row = (await session.execute(month_stmt)).one()
    return {
        "requests_today": int(today_row[0] or 0),
        "tokens_today": int(today_row[1] or 0),
        "requests_month": int(month_row[0] or 0),
        "tokens_month": int(month_row[1] or 0),
    }


_PROVIDER_REGISTRY_IDS = {
    "openrouter": "openrouter",
    "openai": "openai",
    "anthropic": "anthropic",
    "deepseek": "deepseek",
    "openai_compatible": "lmstudio",
    "lmstudio": "lmstudio",
}


async def _provider_exposed_models(provider_name: str) -> set[str] | None:
    provider_id = _PROVIDER_REGISTRY_IDS.get(provider_name)
    if not provider_id:
        return None
    provider = get_provider(provider_id)
    if provider is None:
        return None
    try:
        models = await provider.list_models()
    except Exception:
        return None
    if not models:
        return None
    return {str(item).strip() for item in models if str(item).strip()}


async def _portal_usage_customer_pricing(
    session: AsyncSession,
    client_id: UUID,
    invoice_preview: dict,
) -> dict:
    today_start = _start_of_day_utc()
    month_start_dt = datetime.combine(month_start(date.today()), datetime.min.time(), tzinfo=timezone.utc)
    today_stmt = select(func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0)).where(
        RequestFinancial.client_id == client_id,
        RequestFinancial.created_at >= today_start,
    )
    month_stmt = select(func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0)).where(
        RequestFinancial.client_id == client_id,
        RequestFinancial.created_at >= month_start_dt,
    )
    today_total = float((await session.execute(today_stmt)).scalar() or 0.0)
    month_total = float((await session.execute(month_stmt)).scalar() or 0.0)
    has_financials = month_total > 0 or today_total > 0
    return {
        "visible": True,
        "currency": "BRL" if has_financials else invoice_preview["currency"],
        "today_amount": round(today_total, 4) if has_financials else None,
        "month_amount": round(month_total, 4) if has_financials else round(float(invoice_preview["total_estimated"]), 4),
        "source": "request_financials" if has_financials else "invoice_preview",
    }


async def _load_portal_invoice(
    session: AsyncSession,
    client_id: UUID,
    invoice_id: UUID,
) -> BillingInvoice | None:
    return (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.payments))
            .where(BillingInvoice.id == invoice_id, BillingInvoice.client_id == client_id)
        )
    ).scalar_one_or_none()


@router.get("/plans")
async def portal_list_plans(
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    # Returns all active plans for upgrade simulation
    return await list_public_plans(session)


@router.post("/upgrade")
async def portal_upgrade_plan(
    payload: PortalUpgradeRequest,
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    plan = (
        await session.execute(
            select(BillingPlan)
            .where(BillingPlan.code == payload.plan_code, BillingPlan.is_active.is_(True))
        )
    ).scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="billing plan not found")
        
    # Update client plan and quotas
    client.billing_plan_id = plan.id
    client.rate_limit_per_minute = plan.rate_limit_per_minute
    client.daily_token_quota = plan.daily_token_quota
    client.weekly_token_quota = plan.weekly_token_quota
    client.monthly_token_quota = plan.monthly_token_quota
    client.max_output_tokens = plan.max_output_tokens
    
    # Reset billing status to active if they were past_due/suspended (simulation)
    client.billing_status = "active"
    
    await session.commit()
    return {"status": "success", "new_plan": plan.name}


@router.post("/simulate-payment/{invoice_id}")
async def portal_simulate_payment(
    invoice_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    invoice = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.payments))
            .where(BillingInvoice.id == invoice_id, BillingInvoice.client_id == client.id)
        )
    ).scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="invoice not found")
        
    if invoice.status == "paid":
        return {"status": "already_paid"}
        
    current_time = utc_now()
    invoice.status = "paid"
    invoice.paid_at = current_time
    invoice.cancelled_at = None
    invoice.updated_at = current_time
    
    # Record payment
    # Check if there is already a pending/overdue payment to fulfill
    payment = next((item for item in invoice.payments if item.status in {"pending", "overdue"}), None)
    if payment is None:
        payment = CustomerPayment(
            invoice_id=invoice.id,
            client_id=client.id,
            amount=invoice.total_amount,
            currency=invoice.currency,
            payment_method="simulation_portal",
            payment_reference=f"sim_{short_prefix(str(invoice.id))}",
            status="paid",
            paid_at=current_time,
        )
        session.add(payment)
    else:
        payment.status = "paid"
        payment.paid_at = current_time
        payment.payment_method = "simulation_portal"
        payment.payment_reference = f"sim_{short_prefix(str(invoice.id))}"
        payment.updated_at = current_time
    
    # Force client status to active
    client.billing_status = "active"
    client.updated_at = current_time
    
    await session.commit()
    # Refresh other statuses if needed
    await refresh_billing_statuses(session)
    await session.commit()
    
    return {"status": "success", "message": "Payment simulated and account refreshed"}


@router.get("/me")
async def portal_me(
    request: Request,
    client: Client = Depends(require_client),
):
    from app.core.config import get_settings
    settings = get_settings()
    effective_plan = resolve_effective_plan(client)
    return {
        "id": str(client.id),
        "name": client.name,
        "description": client.description,
        "billing_status": client.billing_status,
        "is_blocked": client.is_blocked,
        "demo_mode": settings.demo_mode,
        "plan": {
            "code": effective_plan.code,
            "name": effective_plan.name,
            "rate_limit_per_minute": effective_plan.rate_limit_per_minute,
            "daily_token_quota": effective_plan.daily_token_quota,
            "weekly_token_quota": effective_plan.weekly_token_quota,
            "monthly_token_quota": effective_plan.monthly_token_quota,
            "requests_per_day": effective_plan.requests_per_day,
            "max_output_tokens": effective_plan.max_output_tokens,
            "max_context_tokens": effective_plan.max_context_tokens,
            "allow_streaming": effective_plan.allow_streaming,
            "monthly_price": float(effective_plan.monthly_price),
            "currency": effective_plan.currency,
            "rag_enabled": effective_plan.rag_enabled,
            "rag_max_documents": effective_plan.rag_max_documents,
            "rag_max_storage_mb": effective_plan.rag_max_storage_mb,
            "rag_max_pages_per_month": effective_plan.rag_max_pages_per_month,
            "rag_max_queries_per_month": effective_plan.rag_max_queries_per_month,
            "tts_enabled": effective_plan.tts_enabled,
            "tts_chars_per_day": effective_plan.tts_chars_per_day,
            "tts_chars_per_month": effective_plan.tts_chars_per_month,
            "embeddings_enabled": effective_plan.embeddings_enabled,
            "responses_enabled": effective_plan.responses_enabled,
            "export_enabled": effective_plan.export_enabled,
            "support_level": effective_plan.support_level,
        },
        "enterprise_audit_portal": get_portal_capabilities(client, request),
    }


@router.get("/api-keys")
async def portal_list_api_keys(
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    result = await session.execute(
        select(ApiKey).where(ApiKey.client_id == client.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "key_prefix": k.key_prefix,
            "masked_key": f"{k.key_prefix}...",
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
            "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "allowed_ips": json.loads(k.allowed_ips_json) if k.allowed_ips_json else None,
            "scopes": json.loads(k.scopes_json) if k.scopes_json else None,
        }
        for k in keys
    ]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def portal_create_api_key(
    payload: ApiKeyCreate,
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    if payload.client_id != client.id:
        raise HTTPException(status_code=403, detail="forbidden")
    
    plaintext = generate_api_key()
    api_key = ApiKey(
        client_id=client.id,
        name=payload.name,
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes_json=json.dumps(payload.scopes) if payload.scopes else None,
        expires_at=payload.expires_at,
        allowed_ips_json=json.dumps(payload.allowed_ips) if payload.allowed_ips else None,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    
    return ApiKeyCreated(
        id=api_key.id,
        client_id=api_key.client_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        api_key=plaintext,
        scopes=payload.scopes,
        expires_at=api_key.expires_at,
        allowed_ips=payload.allowed_ips,
        created_at=api_key.created_at,
    )


@router.delete("/api-keys/{api_key_id}")
async def portal_revoke_api_key(
    api_key_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    api_key = await session.get(ApiKey, api_key_id)
    if not api_key or api_key.client_id != client.id:
        raise HTTPException(status_code=404, detail="api key not found")
    
    if api_key.revoked_at is not None:
        return {"status": "already_revoked"}
    
    api_key.revoked_at = utc_now()
    api_key.is_active = False
    await session.commit()
    return {"status": "revoked"}


@router.get("/usage-stats")
async def portal_usage_stats(
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    from sqlalchemy import func
    from datetime import timedelta
    
    # Last 30 days daily usage
    thirty_days_ago = utc_now() - timedelta(days=30)
    
    daily_query = (
        select(
            func.date(RequestLog.created_at).label("day"),
            func.sum(RequestLog.prompt_tokens_estimated + RequestLog.completion_tokens_estimated).label("tokens"),
            func.count(RequestLog.id).label("requests")
        )
        .where(RequestLog.client_id == client.id, RequestLog.created_at >= thirty_days_ago)
        .group_by(func.date(RequestLog.created_at))
        .order_by(func.date(RequestLog.created_at))
    )
    daily_results = (await session.execute(daily_query)).all()
    
    # Model breakdown (this month)
    this_month_start = month_start(date.today())
    model_query = (
        select(
            RequestLog.model,
            func.count(RequestLog.id).label("requests"),
            func.sum(RequestLog.prompt_tokens_estimated + RequestLog.completion_tokens_estimated).label("tokens")
        )
        .where(RequestLog.client_id == client.id, RequestLog.created_at >= datetime.combine(this_month_start, datetime.min.time(), tzinfo=timezone.utc))
        .group_by(RequestLog.model)
        .order_by(desc("requests"))
    )
    model_results = (await session.execute(model_query)).all()
    
    # Current month total requests
    total_requests_query = select(func.count(RequestLog.id)).where(
        RequestLog.client_id == client.id, 
        RequestLog.created_at >= datetime.combine(this_month_start, datetime.min.time(), tzinfo=timezone.utc)
    )
    total_requests = (await session.execute(total_requests_query)).scalar() or 0
    
    # TTS usage
    tts_usage = await get_tts_usage_and_limits(session, client)
    
    return {
        "daily_usage": [
            {"day": str(r.day), "tokens": int(r.tokens or 0), "requests": int(r.requests or 0)}
            for r in daily_results
        ],
        "model_usage": [
            {"model": r.model, "requests": int(r.requests or 0), "tokens": int(r.tokens or 0)}
            for r in model_results
        ],
        "total_requests_this_month": total_requests,
        "tts_usage": tts_usage
    }


@router.get("/models")
async def portal_list_models(
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    # This should return models allowed for the client
    query = select(ModelRegistry).where(ModelRegistry.is_active.is_(True))
    all_models = (await session.execute(query)).scalars().all()

    allowed = get_effective_allowed_models(client)
    provider_model_catalogs: dict[str, set[str] | None] = {}

    allowed_models = []
    for m in all_models:
        if allowed and m.model_id not in allowed and (m.model_alias or "") not in allowed:
            continue
        if m.provider not in provider_model_catalogs:
            provider_model_catalogs[m.provider] = await _provider_exposed_models(m.provider)
        exposed_models = provider_model_catalogs[m.provider]
        if exposed_models is not None and m.model_id not in exposed_models:
            continue
        trust = await get_model_trust_state(session, m.model_alias or m.model_id, client=client)
        latest_scan = (
            await session.execute(
                select(CommercialModelIntegrityScan)
                .where(
                    (CommercialModelIntegrityScan.model_name == m.model_id)
                    | (CommercialModelIntegrityScan.model_name == (m.model_alias or ""))
                )
                .order_by(desc(CommercialModelIntegrityScan.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        latest_attestation = (
            await session.execute(
                select(CommercialRuntimeModelAttestation)
                .where(
                    (CommercialRuntimeModelAttestation.model_name == m.model_id)
                    | (CommercialRuntimeModelAttestation.model_alias == (m.model_alias or ""))
                )
                .order_by(desc(CommercialRuntimeModelAttestation.attested_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        provenance_summary = await summarize_model_provenance(
            session,
            uuid.UUID(trust["provenance_id"]) if trust.get("provenance_id") else None,
        ) if trust.get("provenance_id") else None
        if provenance_summary:
            provenance_summary.pop("source_uri", None)
        allowed_models.append({
            "id": m.model_id,
            "alias": m.model_alias,
            "display_name": m.model_alias or m.model_id,
            "context_length": m.context_length,
            "trust_state": trust["trust_state"],
            "trust_state_runtime": latest_scan.integrity_status if latest_scan else "unknown",
            "approved_at": trust.get("approved_at"),
            "revocation_status": trust["trust_state"] if trust["trust_state"] in {"revoked", "quarantined"} else None,
            "quarantine_status": bool(
                trust["trust_state"] == "quarantined" or (latest_scan and latest_scan.integrity_status == "quarantined")
            ),
            "integrity_summary": {
                "status": latest_scan.integrity_status if latest_scan else "unknown",
                "scan_type": latest_scan.scan_type if latest_scan else None,
                "scanned_at": latest_scan.created_at.isoformat() if latest_scan else None,
                "checksum_prefix": (latest_scan.observed_checksum or "")[:12] if latest_scan and latest_scan.observed_checksum else None,
            },
            "attestation_summary": serialize_runtime_attestation(latest_attestation) if latest_attestation else None,
            "provenance_summary": provenance_summary,
        })
        
    return allowed_models


@router.get("/account")
async def portal_account(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    effective_plan = resolve_effective_plan(client)
    counters = await get_current_usage_snapshot(session, client.id)
    daily_used = int(counters["daily"].used_tokens) if counters["daily"] else 0
    weekly_used = int(counters["weekly"].used_tokens) if counters["weekly"] else 0
    monthly_used = int(counters["monthly"].used_tokens) if counters["monthly"] else 0
    from app.models.commercial_inference_reproducibility import CommercialInferenceReproducibilityRecord

    repro_total = (
        await session.execute(
            select(func.count(CommercialInferenceReproducibilityRecord.id)).where(
                CommercialInferenceReproducibilityRecord.client_id == str(client.id)
            )
        )
    ).scalar() or 0
    repro_replayable = (
        await session.execute(
            select(func.count(CommercialInferenceReproducibilityRecord.id)).where(
                CommercialInferenceReproducibilityRecord.client_id == str(client.id),
                CommercialInferenceReproducibilityRecord.replay_supported.is_(True),
            )
        )
    ).scalar() or 0
    
    return {
        "client_id": str(client.id),
        "name": client.name,
        "billing_status": client.billing_status,
        "plan": {
            "code": effective_plan.code,
            "name": effective_plan.name,
            "rate_limit_per_minute": effective_plan.rate_limit_per_minute,
            "daily_token_quota": effective_plan.daily_token_quota,
            "weekly_token_quota": effective_plan.weekly_token_quota,
            "monthly_token_quota": effective_plan.monthly_token_quota,
            "requests_per_day": effective_plan.requests_per_day,
            "max_output_tokens": effective_plan.max_output_tokens,
            "max_context_tokens": effective_plan.max_context_tokens,
            "rag_enabled": effective_plan.rag_enabled,
            "tts_enabled": effective_plan.tts_enabled,
            "embeddings_enabled": effective_plan.embeddings_enabled,
            "responses_enabled": effective_plan.responses_enabled,
            "export_enabled": effective_plan.export_enabled,
            "support_level": effective_plan.support_level,
        },
        "usage": {
            "daily_used_tokens": daily_used,
            "weekly_used_tokens": weekly_used,
            "monthly_used_tokens": monthly_used,
        },
        "reproducibility": {
            "best_effort_only": True,
            "records": int(repro_total),
            "replayable": int(repro_replayable),
            "support_percent": round(((repro_replayable / repro_total) * 100.0) if repro_total else 0.0, 2),
        },
    }


@router.get("/inference/reproducibility")
async def portal_inference_reproducibility(
    limit: int = Query(default=50, ge=1, le=200),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    from app.models.commercial_inference_reproducibility import CommercialInferenceReproducibilityRecord

    rows = (
        await session.execute(
            select(CommercialInferenceReproducibilityRecord)
            .where(CommercialInferenceReproducibilityRecord.client_id == str(client.id))
            .order_by(desc(CommercialInferenceReproducibilityRecord.created_at))
            .limit(limit)
        )
    ).scalars().all()
    items = []
    for item in rows:
        items.append(
            {
                "id": str(item.id),
                "model_name": item.model_name,
                "model_alias": item.model_alias,
                "backend_name": item.backend_name,
                "replay_supported": item.replay_supported,
                "replay_status": item.replay_status,
                "replay_similarity": item.replay_similarity,
                "drift_status": "DRIFT" if item.replay_status == "drift_detected" else "STABLE",
                "runtime_provenance_summary": {
                    "runtime_engine": item.runtime_engine,
                    "runtime_engine_version": item.runtime_engine_version,
                    "tokenizer_name": item.tokenizer_name,
                    "template_hash": (item.chat_template_hash or "")[:12] or None,
                },
                "created_at": item.created_at.isoformat(),
                "replayed_at": item.replayed_at.isoformat() if item.replayed_at else None,
            }
        )
    return {
        "best_effort_only": True,
        "items": sanitize_report_payload(items),
    }


@router.get("/usage")
async def portal_usage(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    from app.services.tts_usage import get_tts_usage_and_limits
    
    effective_plan = resolve_effective_plan(client)
    counters = await get_current_usage_snapshot(session, client.id)
    daily_used = int(counters["daily"].used_tokens) if counters["daily"] else 0
    weekly_used = int(counters["weekly"].used_tokens) if counters["weekly"] else 0
    monthly_used = int(counters["monthly"].used_tokens) if counters["monthly"] else 0
    
    tts_info = await get_tts_usage_and_limits(session, client)
    monthly_tts_used = tts_info["usage"]["monthly_chars"]
    
    invoice_preview = build_invoice_preview(
        effective_plan=effective_plan, 
        monthly_used_tokens=monthly_used,
        monthly_used_tts_chars=monthly_tts_used
    )
    request_totals = await _portal_usage_request_totals(session, client.id)
    customer_pricing = await _portal_usage_customer_pricing(session, client.id, invoice_preview)
    return {
        "client_id": str(client.id),
        "billing_status": client.billing_status,
        "requests_today": request_totals["requests_today"],
        "requests_month": request_totals["requests_month"],
        "tokens_today": request_totals["tokens_today"],
        "tokens_month": request_totals["tokens_month"],
        "customer_pricing": customer_pricing,
        "quota_remaining": {
            "daily_tokens": max(effective_plan.daily_token_quota - daily_used, 0),
            "weekly_tokens": max(effective_plan.weekly_token_quota - weekly_used, 0),
            "monthly_tokens": max(effective_plan.monthly_token_quota - monthly_used, 0),
            "requests_per_day": max(effective_plan.requests_per_day - request_totals["requests_today"], 0)
            if effective_plan.requests_per_day
            else None,
        },
        "rate_limit": {
            "requests_per_minute": effective_plan.rate_limit_per_minute,
            "requests_per_day": effective_plan.requests_per_day,
        },
        "daily_usage": {
            "used_tokens": daily_used,
            "remaining_tokens": max(effective_plan.daily_token_quota - daily_used, 0),
            "quota": effective_plan.daily_token_quota,
        },
        "weekly_usage": {
            "used_tokens": weekly_used,
            "remaining_tokens": max(effective_plan.weekly_token_quota - weekly_used, 0),
            "quota": effective_plan.weekly_token_quota,
        },
        "monthly_usage": {
            "used_tokens": monthly_used,
            "remaining_tokens": max(effective_plan.monthly_token_quota - monthly_used, 0),
            "quota": effective_plan.monthly_token_quota,
        },
        "tts_usage": tts_info,
        "invoice_preview": invoice_preview,
    }


@router.get("/rag/vault")
async def portal_rag_vault_status(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    vault = (
        await session.execute(
            select(CommercialRAGVault).where(CommercialRAGVault.client_id == client.id)
        )
    ).scalar_one_or_none()
    if vault is None:
        return {"enabled": False, "vault_status": None}

    docs = (
        await session.execute(
            select(func.count(CommercialRAGDocument.id)).where(CommercialRAGDocument.vault_id == vault.id)
        )
    ).scalar() or 0
    signed_docs = (
        await session.execute(
            select(func.count(CommercialRAGDocument.id)).where(
                CommercialRAGDocument.vault_id == vault.id,
                CommercialRAGDocument.signed_manifest_hash.is_not(None),
            )
        )
    ).scalar() or 0
    holds = (
        await session.execute(
            select(func.count(CommercialRAGLegalHold.id)).where(
                CommercialRAGLegalHold.vault_id == vault.id,
                CommercialRAGLegalHold.active == True,
            )
        )
    ).scalar() or 0
    return {
        "enabled": True,
        "vault_status": {
            "id": str(vault.id),
            "vault_name": vault.vault_name,
            "vault_mode": vault.vault_mode,
            "confidential_retrieval_mode": vault.vault_mode in {"confidential", "sovereign", "airgap"},
            "encryption_required": vault.encryption_required,
            "documents": int(docs),
            "signed_documents": int(signed_docs),
            "active_legal_holds": int(holds),
        },
    }


@router.get("/rag/retrieval-history")
async def portal_rag_retrieval_history(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    vault = (
        await session.execute(
            select(CommercialRAGVault).where(CommercialRAGVault.client_id == client.id)
        )
    ).scalar_one_or_none()
    if vault is None:
        return {"items": []}
    rows = (
        await session.execute(
            select(CommercialRAGRetrievalAudit)
            .where(CommercialRAGRetrievalAudit.vault_id == vault.id)
            .order_by(desc(CommercialRAGRetrievalAudit.created_at))
            .limit(100)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(item.id),
                "request_hash": item.request_hash[:16],
                "retrieval_hash": item.retrieval_hash[:16],
                "retrieved_chunk_count": item.retrieved_chunk_count,
                "policy_result": item.policy_result,
                "model_id": item.model_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ]
    }


@router.get("/rag/legal-holds")
async def portal_rag_legal_holds(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    vault = (
        await session.execute(
            select(CommercialRAGVault).where(CommercialRAGVault.client_id == client.id)
        )
    ).scalar_one_or_none()
    if vault is None:
        return {"items": []}
    rows = (
        await session.execute(
            select(CommercialRAGLegalHold)
            .where(CommercialRAGLegalHold.vault_id == vault.id)
            .order_by(desc(CommercialRAGLegalHold.created_at))
            .limit(100)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(item.id),
                "document_id": str(item.document_id) if item.document_id else None,
                "hold_reason": item.hold_reason,
                "active": item.active,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ]
    }


@router.get("/rag/trust-status")
async def portal_rag_document_trust_status(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    vault = (
        await session.execute(
            select(CommercialRAGVault).where(CommercialRAGVault.client_id == client.id)
        )
    ).scalar_one_or_none()
    if vault is None:
        return {"items": []}
    rows = (
        await session.execute(
            select(CommercialRAGDocument)
            .where(CommercialRAGDocument.vault_id == vault.id)
            .order_by(desc(CommercialRAGDocument.created_at))
            .limit(100)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(item.id),
                "document_title": item.document_title,
                "classification": item.classification,
                "signed_document": bool(item.signed_manifest_hash),
                "legal_hold": item.legal_hold,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ]
    }


@router.get("/invoices")
async def portal_invoices(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    from app.core.config import get_settings
    settings = get_settings()
    await refresh_billing_statuses(session)
    await session.commit()
    invoices = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.payments))
            .where(BillingInvoice.client_id == client.id)
            .order_by(desc(BillingInvoice.created_at))
            .limit(50)
        )
    ).scalars().all()
    payments = (
        await session.execute(
            select(CustomerPayment)
            .where(CustomerPayment.client_id == client.id)
            .order_by(desc(CustomerPayment.created_at))
            .limit(50)
        )
    ).scalars().all()
    return {
        "client_id": str(client.id),
        "billing_status": client.billing_status,
        "local_billing_mode": settings.local_billing_mode,
        "local_billing_message": "pagamento manual/local" if settings.local_billing_mode == "manual" else None,
        "invoices": [serialize_invoice(invoice) for invoice in invoices],
        "payments": [
            {
                "id": str(payment.id),
                "invoice_id": str(payment.invoice_id),
                "status": payment.status,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "payment_reference": payment.payment_reference,
                "note": payment.note,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "cancelled_at": payment.cancelled_at.isoformat() if payment.cancelled_at else None,
                "created_at": payment.created_at.isoformat(),
                "updated_at": payment.updated_at.isoformat(),
            }
            for payment in payments
        ],
    }


@router.get("/invoices/{invoice_id}/download")
async def portal_invoice_download(
    invoice_id: UUID,
    format: str = "json",
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    invoice = await _load_portal_invoice(session, client.id, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")

    serialized = serialize_invoice(invoice)
    if format == "json":
        return JSONResponse(
            content=serialized,
            headers={"Content-Disposition": f'attachment; filename="invoice-{invoice_id}.json"'},
        )
    if format == "html":
        return HTMLResponse(
            content=_build_invoice_html(serialized, client),
            headers={"Content-Disposition": f'attachment; filename="invoice-{invoice_id}.html"'},
        )
    raise HTTPException(status_code=400, detail="unsupported invoice format")


@router.get("/wallet")
async def portal_wallet(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    from app.services.billing.wallet_service import get_balance, list_transactions, serialize_transaction
    from app.services.billing import estimate_request_cost, get_current_usage_snapshot, resolve_effective_plan
    balance = await get_balance(session, client.id)
    txs = await list_transactions(session, client.id, limit=20)
    effective_plan = resolve_effective_plan(client)
    counters = await get_current_usage_snapshot(session, client.id)
    monthly_used = int(counters["monthly"].used_tokens) if counters["monthly"] else 0
    monthly_quota = effective_plan.monthly_token_quota
    overage_price = float(effective_plan.overage_price_per_1k_tokens)
    if monthly_used > monthly_quota:
        overage_tokens = monthly_used - monthly_quota
        estimated_consumption_brl = (overage_tokens / 1000.0) * overage_price
    else:
        estimated_consumption_brl = 0.0
    low_balance_threshold_brl = max(float(effective_plan.monthly_price), 20.0)
    available_brl = float(balance["available_brl"])
    low_balance = available_brl <= low_balance_threshold_brl
    return {
        **balance,
        "consumption_estimate_brl": round(estimated_consumption_brl, 4),
        "monthly_used_tokens": monthly_used,
        "monthly_quota_tokens": monthly_quota,
        "low_balance_threshold_brl": round(low_balance_threshold_brl, 2),
        "low_balance": low_balance,
        "low_balance_message": (
            f"Saldo baixo. Solicite recarga antes de atingir {low_balance_threshold_brl:.2f} BRL disponíveis."
            if low_balance
            else None
        ),
        "pix_notice": "Recarga via PIX real ainda não está disponível nesta versão. "
                      "Créditos devem ser adicionados manualmente pelo administrador.",
        "transactions": [_portal_visible_wallet_transaction(tx) for tx in txs],
    }


@router.post("/wallet/recharge-request", status_code=201)
async def portal_wallet_recharge_request(
    payload: PortalWalletRechargeRequest,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    metadata = json.loads(client.metadata_json) if client.metadata_json else {}
    contact_name = metadata.get("contact_name") or client.name
    contact_email = metadata.get("contact_email") or f"portal+{short_prefix(str(client.id))}@local.invalid"
    lead = SalesLead(
        company_name=client.name,
        contact_name=contact_name,
        contact_email=contact_email,
        segment="existing_customer",
        source="portal_wallet_recharge",
        status="qualified",
        estimated_value=payload.amount_brl or 0.0,
        notes=(
            f"Recharge requested from client portal. client_id={client.id} "
            f"amount_brl={payload.amount_brl if payload.amount_brl is not None else 'not_informed'} "
            f"note={payload.note or '-'}"
        ),
        is_demo=False,
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return {
        "status": "created",
        "lead_id": str(lead.id),
        "message": "Solicitação registrada para o time interno.",
    }


@router.post("/wallet/topups", status_code=201)
async def portal_create_wallet_topup(
    payload: WalletTopUpCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    intent = await create_topup_intent(
        session,
        client=client,
        amount_brl=payload.amount_brl,
        idempotency_key=payload.idempotency_key,
    )
    await session.commit()
    await session.refresh(intent)
    return serialize_topup(intent, include_payment_data=True)


@router.get("/wallet/topups")
async def portal_list_wallet_topups(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    intents = await list_topup_intents(session, client_id=client.id)
    return [serialize_topup(intent) for intent in intents]


@router.get("/examples")
async def portal_examples(
    client: Client = Depends(require_client),
):
    from app.core.config import get_settings

    settings = get_settings()
    base_url = settings.public_base_url.rstrip("/") if settings.public_base_url else "http://localhost:8080"
    openai_base_url = f"{base_url}/v1"
    return {
        "client_id": str(client.id),
        "base_url": openai_base_url,
        "snippets": {
            "curl": (
                f"curl -X POST {openai_base_url}/chat/completions \\\n"
                '  -H "Content-Type: application/json" \\\n'
                '  -H "Authorization: Bearer __API_KEY__" \\\n'
                '  -d \'{"model":"default","messages":[{"role":"user","content":"Olá!"}]}\''
            ),
            "python": (
                "from openai import OpenAI\n\n"
                f'client = OpenAI(api_key="__API_KEY__", base_url="{openai_base_url}")\n'
                "resp = client.chat.completions.create(\n"
                '    model="default",\n'
                '    messages=[{"role": "user", "content": "Olá!"}],\n'
                ")\n"
                "print(resp.choices[0].message.content)\n"
            ),
            "node": (
                'import OpenAI from "openai";\n\n'
                f'const client = new OpenAI({{ apiKey: "__API_KEY__", baseURL: "{openai_base_url}" }});\n'
                "const resp = await client.chat.completions.create({\n"
                '  model: "default",\n'
                '  messages: [{ role: "user", content: "Olá!" }],\n'
                "});\n"
                "console.log(resp.choices[0].message.content);\n"
            ),
            "python_sdk": (
                "from kleberai import Client\n\n"
                f'client = Client(api_key="__API_KEY__", base_url="{base_url}")\n'
                'resp = client.chat("Olá!")\n'
                "print(resp['choices'][0]['message']['content'])\n"
            ),
            "node_sdk": (
                'import { Client } from "kleberai";\n\n'
                f'const client = new Client({{ apiKey: "__API_KEY__", baseUrl: "{base_url}" }});\n'
                'const resp = await client.chat("Olá!");\n'
                "console.log(resp.choices[0].message.content);\n"
            ),
        },
    }


@router.post("/onboarding/event")
async def record_onboarding_event(
    payload: OnboardingEventRequest,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    metadata = json.loads(client.metadata_json) if client.metadata_json else {}
    if payload.event == "portal_tutorial_closed":
        metadata["onboarding_finished"] = True
    client.metadata_json = json.dumps(metadata)
    await session.commit()
    return {"status": "ok"}


@router.get("/qos-billing")
async def portal_qos_billing(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns the client's QoS billing records.
    """
    stmt = (
        select(CommercialQoSBillingRecord)
        .where(CommercialQoSBillingRecord.client_id == client.id)
        .order_by(CommercialQoSBillingRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "qos_tier": r.qos_tier,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "compute_seconds": float(r.compute_seconds),
            "priority_slots_consumed": float(r.priority_slots_consumed),
            "billable_amount_brl": float(r.billable_amount_brl),
            "status": r.status,
            "wallet_transaction_id": str(r.wallet_transaction_id) if r.wallet_transaction_id else None,
            "invoice_id": str(r.invoice_id) if r.invoice_id else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.post("/test-chat")
async def portal_test_chat(
    payload: PortalTestChatRequest,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    chat_payload = ChatCompletionRequest(
        model=payload.model or "default",
        messages=[{"role": "user", "content": payload.prompt}],
        max_tokens=payload.max_tokens,
        stream=False,
        include_reasoning=False,
    )
    selected_model, _ = await resolve_requested_model(
        session,
        client=client,
        requested_model=chat_payload.model,
    )
    prompt_tokens = estimate_prompt_tokens(messages=[item.model_dump() for item in chat_payload.messages])
    if prompt_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit")
    max_tokens, temperature, top_p, effective_plan = validate_params(client, chat_payload)
    incoming_tokens = prompt_tokens + max_tokens
    try:
        await enforce_rate_limit(redis, client.id, effective_plan.rate_limit_per_minute)
        await ensure_quota(session, client.id, effective_plan.daily_token_quota, effective_plan.weekly_token_quota, effective_plan.monthly_token_quota, incoming_tokens)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    body = chat_payload.model_dump(exclude={"include_reasoning"})
    body["model"] = selected_model.model_id
    body["max_tokens"] = max_tokens
    body["temperature"] = temperature
    body["top_p"] = top_p
    cache_key, cache_fingerprint = build_chat_cache_key(
        model=selected_model.model_id,
        messages=[item.model_dump() for item in chat_payload.messages],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        include_reasoning=False,
    )
    usage_snapshot = await get_current_usage_snapshot(session, client.id)
    monthly_used_before = int(usage_snapshot["monthly"].used_tokens) if usage_snapshot["monthly"] else 0
    estimated_request_cost = float(
        estimate_request_cost(
            monthly_tokens_used_before=monthly_used_before,
            request_tokens=incoming_tokens,
            included_monthly_tokens=effective_plan.monthly_token_quota,
            overage_price_per_1k_tokens=effective_plan.overage_price_per_1k_tokens,
        )
    )
    request_summary = summarize_chat_request([item.model_dump() for item in chat_payload.messages], include_reasoning=False)
    started = perf_counter()
    try:
        cached = await lookup_exact_cache(
            session,
            endpoint="/portal/test-chat",
            model=selected_model.model_id,
            request_hash=cache_key,
            plan_code=effective_plan.code,
        )
        if cached.hit and cached.payload is not None:
            latency_ms = int((perf_counter() - started) * 1000)
            await record_usage(session, client.id, prompt_tokens, cached.completion_tokens)
            await log_request(
                session,
                client_id=client.id,
                model=selected_model.model_id,
                endpoint="/portal/test-chat",
                prompt_tokens=prompt_tokens,
                completion_tokens=cached.completion_tokens,
                latency_ms=latency_ms,
                status_code=200,
                is_stream=False,
                estimated_cost_usd=estimated_request_cost,
                backend_name="cache:exact",
                attempts=0,
                fallback_used=False,
                cache_hit=True,
                backend_errors=[],
                error_message=None,
                request_summary=request_summary,
                plan_code=effective_plan.code,
            )
            await session.commit()
            payload_json = cached.payload
            return {
                "model": selected_model.model_id,
                "cached": True,
                "response": payload_json,
                "text": (((payload_json.get("choices") or [{}])[0].get("message") or {}).get("content")) or "",
            }

        result = await _chat_with_fallback(proxy, selected_model, body, False, False, client=client, session=session)
        latency_ms = int((perf_counter() - started) * 1000)
        response_payload = json.loads(result.response.body.decode("utf-8"))
        completion_tokens = estimate_tokens_from_text(result.response.body.decode("utf-8"))
        await store_exact_cache(
            session,
            endpoint="/portal/test-chat",
            model=selected_model.model_id,
            request_hash=cache_key,
            request_fingerprint=cache_fingerprint,
            response_payload=response_payload,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        await record_usage(session, client.id, prompt_tokens, completion_tokens)
        await log_request(
            session,
            client_id=client.id,
            model=selected_model.model_id,
            endpoint="/portal/test-chat",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status_code=result.response.status_code,
            is_stream=False,
            estimated_cost_usd=estimated_request_cost,
            backend_name=result.backend_name,
            attempts=result.attempts,
            fallback_used=result.fallback_used,
            cache_hit=False,
            backend_errors=result.backend_errors,
            error_message=None,
            request_summary=request_summary,
            plan_code=effective_plan.code,
        )
        await session.commit()
        return {
            "model": selected_model.model_id,
            "cached": False,
            "response": response_payload,
            "text": ((((response_payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""),
        }
    except HTTPException as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        backend_errors = _backend_errors_for_log(exc.detail)
        await log_request(
            session,
            client_id=client.id,
            model=selected_model.model_id,
            endpoint="/portal/test-chat",
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            status_code=exc.status_code,
            is_stream=False,
            estimated_cost_usd=estimated_request_cost,
            backend_name=backend_errors[-1]["backend_name"] if backend_errors else None,
            attempts=max(len(backend_errors), 1),
            fallback_used=len(backend_errors) > 1,
            cache_hit=False,
            backend_errors=backend_errors,
            error_message=_error_message_for_log(exc.detail),
            request_summary=request_summary,
            plan_code=effective_plan.code,
        )
        await session.commit()
        raise


@router.post("/billing/disputes", status_code=201)
async def portal_open_dispute(
    payload: BillingDisputeOpen,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Allows a client to open a billing dispute.
    """
    dispute = await DisputeManagementService.open_dispute(
        session,
        client_id=client.id,
        dispute_type=payload.dispute_type,
        claimed_amount_brl=payload.claimed_amount_brl,
        disputed_reason=payload.disputed_reason,
        qos_billing_record_id=payload.qos_billing_record_id,
        invoice_id=payload.invoice_id,
        wallet_transaction_id=payload.wallet_transaction_id
    )
    return {
        "id": str(dispute.id),
        "status": dispute.status,
        "created_at": dispute.created_at.isoformat()
    }


@router.get("/billing/disputes")
async def portal_list_disputes(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Lists the client's billing disputes.
    """
    stmt = select(CommercialBillingDispute).where(
        CommercialBillingDispute.client_id == client.id
    ).order_by(desc(CommercialBillingDispute.created_at))
    
    result = await session.execute(stmt)
    disputes = result.scalars().all()
    
    return [
        {
            "id": str(d.id),
            "dispute_type": d.dispute_type,
            "status": d.status,
            "claimed_amount_brl": float(d.claimed_amount_brl),
            "disputed_reason": d.disputed_reason,
            "admin_notes": d.admin_notes,
            "resolution_notes": d.resolution_notes,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
            "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
        }
        for d in disputes
    ]


@router.get("/audit/approval-chains")
async def portal_audit_approval_chains(
    request: Request,
    period_start: date | None = None,
    period_end: date | None = None,
    status: str | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:approval_chain")
    items = await list_customer_approval_chains(
        session,
        client_id=client.id,
        period_start=period_start,
        period_end=period_end,
        status=status,
        control_area=control_area,
        actor=actor,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="approval_chain",
        action=_audit_action_from_filters(period_start=period_start, period_end=period_end, status=status, control_area=control_area, actor=actor),
        metadata_json={"count": len(items), "filters": {"period_start": period_start, "period_end": period_end, "status": status, "control_area": control_area, "actor": actor}},
    )
    await session.commit()
    return {"items": items}


@router.get("/audit/evidence-packages")
async def portal_audit_evidence_packages(
    request: Request,
    period_start: date | None = None,
    period_end: date | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:evidence_package")
    items = await list_customer_evidence_packages(
        session,
        client_id=client.id,
        period_start=period_start,
        period_end=period_end,
        control_area=control_area,
        actor=actor,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="evidence_package",
        action=_audit_action_from_filters(period_start=period_start, period_end=period_end, control_area=control_area, actor=actor),
        metadata_json={"count": len(items), "filters": {"period_start": period_start, "period_end": period_end, "control_area": control_area, "actor": actor}},
    )
    await session.commit()
    return {"items": items}


@router.get("/audit/attestations")
async def portal_audit_attestations(
    request: Request,
    period_start: date | None = None,
    period_end: date | None = None,
    status: str | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:attestation")
    items = await list_customer_attestations(
        session,
        client_id=client.id,
        period_start=period_start,
        period_end=period_end,
        status=status,
        control_area=control_area,
        actor=actor,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="attestation",
        action=_audit_action_from_filters(period_start=period_start, period_end=period_end, status=status, control_area=control_area, actor=actor),
        metadata_json={"count": len(items), "filters": {"period_start": period_start, "period_end": period_end, "status": status, "control_area": control_area, "actor": actor}},
    )
    await session.commit()
    return {"items": items}


@router.get("/audit/exceptions")
async def portal_audit_exceptions(
    request: Request,
    period_start: date | None = None,
    period_end: date | None = None,
    status: str | None = None,
    severity: str | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:exception")
    items = await list_customer_exceptions(
        session,
        client_id=client.id,
        period_start=period_start,
        period_end=period_end,
        status=status,
        severity=severity,
        control_area=control_area,
        actor=actor,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="exception",
        action=_audit_action_from_filters(period_start=period_start, period_end=period_end, status=status, severity=severity, control_area=control_area, actor=actor),
        metadata_json={"count": len(items), "filters": {"period_start": period_start, "period_end": period_end, "status": status, "severity": severity, "control_area": control_area, "actor": actor}},
    )
    await session.commit()
    return {"items": items}


@router.get("/audit/operational-controls")
async def portal_audit_operational_controls(
    request: Request,
    control_category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:operational_control")
    items = await list_customer_operational_controls(
        session,
        client_id=client.id,
        control_category=control_category,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="operational_control",
        action="filter" if control_category else "view",
        metadata_json={"count": len(items), "filters": {"control_category": control_category}},
    )
    await session.commit()
    return {"items": items}


@router.get("/audit/operational-evidence")
async def portal_audit_operational_evidence(
    request: Request,
    freshness_status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:operational_evidence")
    items = await list_customer_operational_evidence(
        session,
        client_id=client.id,
        freshness_status=freshness_status,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="operational_evidence",
        action="filter" if freshness_status else "view",
        metadata_json={"count": len(items), "filters": {"freshness_status": freshness_status}},
    )
    await session.commit()
    return {"items": items}


@router.get("/audit/operational-reviews")
async def portal_audit_operational_reviews(
    request: Request,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:operational_review")
    items = await list_customer_operational_reviews(
        session,
        client_id=client.id,
        status=status,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="operational_review",
        action="filter" if status else "view",
        metadata_json={"count": len(items), "filters": {"status": status}},
    )
    await session.commit()
    return {"items": items}


@router.get("/audit/reports")
async def portal_audit_reports(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:saved_report")
    items = await list_customer_saved_reports(session, client_id=client.id, limit=limit)
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="saved_report",
        action="view",
        metadata_json={"count": len(items)},
    )
    await session.commit()
    return {"items": items}


@router.post("/audit/reports/generate", status_code=201)
async def portal_generate_audit_report(
    payload: PortalAuditReportGeneratePayload,
    request: Request,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    permission = "export:financial_summary" if payload.report_type == "financial_summary" else "export:audit"
    require_portal_permission(client, request, permission=permission)
    identity = _portal_request_identity(request)
    report, report_payload = await generate_customer_audit_report(
        session,
        client=client,
        client_id=client.id,
        report_type=payload.report_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
        filters_json=payload.filters_json,
        export_format=payload.export_format,
        actor_id=identity["actor_id"],
        actor_email=identity["actor_email"],
        actor_name=identity["actor_name"],
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="saved_report",
        resource_id=str(report.id),
        action="export",
        metadata_json={"report_type": report.report_type, "export_format": report.export_format, "immutable_hash": report.immutable_hash},
    )
    await session.commit()
    return {
        "report": {
            "id": str(report.id),
            "report_type": report.report_type,
            "export_format": report.export_format,
            "immutable_hash": report.immutable_hash,
            "created_at": report.created_at.isoformat(),
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
        },
        "summary": report_payload.get("summary", {}),
    }


@router.get("/audit/reports/{report_id}/download")
async def portal_download_audit_report(
    report_id: UUID,
    request: Request,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    report = await session.get(CommercialPortalSavedReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="saved_report not found")
    validate_portal_resource_access(
        client_id=client.id,
        resource_client_id=report.client_id,
        resource_type="saved_report",
        resource_id=report.id,
    )
    permission = "download:financial_summary" if report.report_type == "financial_summary" else "download:audit"
    require_portal_permission(client, request, permission=permission)
    if not report.storage_ref:
        raise HTTPException(status_code=404, detail="report artifact not found")
    artifact = Path(report.storage_ref)
    if not artifact.exists():
        raise HTTPException(status_code=404, detail="report artifact not found")
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="saved_report",
        resource_id=str(report.id),
        action="download",
        metadata_json={"report_type": report.report_type, "export_format": report.export_format},
    )
    await session.commit()
    media_type = {
        "json": "application/json",
        "csv": "text/csv",
        "html": "text/html",
        "pdf": "application/pdf",
    }.get(report.export_format, "application/octet-stream")
    return Response(
        content=artifact.read_bytes(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="enterprise-audit-report-{report.id}.{report.export_format}"'},
    )


@router.get("/audit/access-logs")
async def portal_audit_access_logs(
    request: Request,
    period_start: date | None = None,
    period_end: date | None = None,
    actor: str | None = None,
    action: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    require_portal_permission(client, request, permission="view:access_log")
    items = await list_customer_access_logs(
        session,
        client_id=client.id,
        period_start=period_start,
        period_end=period_end,
        actor=actor,
        action=action,
        limit=limit,
    )
    await _log_portal_read(
        session,
        request,
        client,
        resource_type="access_log",
        action=_audit_action_from_filters(period_start=period_start, period_end=period_end, actor=actor, action=action),
        metadata_json={"count": len(items), "filters": {"period_start": period_start, "period_end": period_end, "actor": actor, "action": action}},
    )
    await session.commit()
    return {"items": items}


@router.get("/inference/receipts")
async def portal_inference_receipts(
    limit: int = Query(default=50, ge=1, le=200),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    rows = (
        await session.execute(
            select(CommercialInferenceReceipt)
            .where(CommercialInferenceReceipt.client_id == str(client.id))
            .order_by(desc(CommercialInferenceReceipt.created_at))
            .limit(limit)
        )
    ).scalars().all()
    items = []
    for item in rows:
        items.append({
            "id": str(item.id),
            "receipt_hash": item.receipt_hash[:16],
            "verification_status": item.verification_status,
            "signature_algorithm": item.signature_algorithm,
            "timestamp_mode": item.timestamp_mode,
            "signed_at": item.signed_at.isoformat(),
            "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            "model_name": item.model_name,
            "prompt_hash": item.prompt_hash[:16],
            "response_hash": item.response_hash[:16],
            "runtime_snapshot_hash": (item.runtime_snapshot_hash or "")[:16] or None,
            "routing_decision_hash": (item.routing_decision_hash or "")[:16] or None,
            "has_signature": bool(item.detached_signature),
            "tamper_reason": item.tamper_reason,
            "created_at": item.created_at.isoformat(),
        })
    return {
        "best_effort_only": True,
        "items": sanitize_report_payload(items),
    }


@router.get("/inference/receipts/{receipt_id}")
async def portal_get_receipt(
    receipt_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    item = await session.get(CommercialInferenceReceipt, receipt_id)
    if item is None or item.client_id != str(client.id):
        raise HTTPException(status_code=404, detail="receipt not found")
    return {
        "id": str(item.id),
        "receipt_hash": item.receipt_hash,
        "previous_receipt_hash": item.previous_receipt_hash,
        "verification_status": item.verification_status,
        "signature_algorithm": item.signature_algorithm,
        "timestamp_mode": item.timestamp_mode,
        "signed_at": item.signed_at.isoformat(),
        "verified_at": item.verified_at.isoformat() if item.verified_at else None,
        "has_signature": bool(item.detached_signature),
        "tamper_reason": item.tamper_reason,
        "prompt_hash": item.prompt_hash[:16],
        "response_hash": item.response_hash[:16],
        "request_payload_hash": (item.request_payload_hash or "")[:16] or None,
        "response_payload_hash": (item.response_payload_hash or "")[:16] or None,
        "runtime_snapshot_hash": (item.runtime_snapshot_hash or "")[:16] or None,
        "routing_decision_hash": (item.routing_decision_hash or "")[:16] or None,
        "model_name": item.model_name,
        "backend_name": item.backend_name,
        "provider": item.provider,
    }


@router.post("/inference/receipts/{receipt_id}/verify")
async def portal_verify_receipt(
    receipt_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    from app.services.inference.cryptographic_receipts import verify_receipt

    item = await session.get(CommercialInferenceReceipt, receipt_id)
    if item is None or item.client_id != str(client.id):
        raise HTTPException(status_code=404, detail="receipt not found")
    report = await verify_receipt(session, item)
    await session.commit()
    return {
        "id": str(report.id),
        "receipt_id": str(report.receipt_id),
        "verification_result": report.verification_result,
        "chain_valid": report.chain_valid,
        "signature_valid": report.signature_valid,
        "timestamp_valid": report.timestamp_valid,
        "report_hash": report.report_hash[:16],
        "created_at": report.created_at.isoformat(),
    }


@router.get("/governance-federation-summary")
async def portal_governance_federation_summary(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    from app.models.commercial_governance_federation import (
        CommercialGovernanceFederationPeer,
        CommercialFederatedPolicySync,
        CommercialFederatedAuditTrail,
    )
    from app.services.governance.governance_consistency import GovernanceConsistencyService

    sync_count = await session.execute(
        select(func.count(CommercialFederatedPolicySync.id))
        .where(CommercialFederatedPolicySync.status == "success")
    )
    policies_replicated = sync_count.scalar() or 0

    event_count = await session.execute(
        select(func.count(CommercialFederatedAuditTrail.id))
    )
    audit_events = event_count.scalar() or 0

    regions_result = await session.execute(
        select(CommercialGovernanceFederationPeer.region)
        .where(CommercialGovernanceFederationPeer.status == "active")
        .distinct()
    )
    regions = [row[0] for row in regions_result.all() if row[0]]

    cc = GovernanceConsistencyService()
    consistency = await cc.check_compliance_consistency(session)

    recent_result = await session.execute(
        select(CommercialFederatedAuditTrail)
        .order_by(CommercialFederatedAuditTrail.received_at.desc())
        .limit(10)
    )
    recent_events = [
        {
            "event_type": ev.event_type,
            "source_cluster_id": ev.source_cluster_id,
            "received_at": ev.received_at.isoformat(),
        }
        for ev in recent_result.scalars().all()
    ]

    packages_result = await session.execute(
        select(CommercialAirgapSyncPackage)
        .order_by(CommercialAirgapSyncPackage.created_at.desc())
        .limit(25)
    )
    packages = packages_result.scalars().all()
    visible_packages = [
        {
            "id": str(item.id),
            "package_type": item.package_type,
            "status": item.status,
            "source_cluster_id": item.source_cluster_id,
            "target_cluster_id": item.target_cluster_id,
            "created_at": item.created_at.isoformat(),
            "imported_at": item.imported_at.isoformat() if item.imported_at else None,
        }
        for item in packages
    ]

    crl_result = await session.execute(select(func.count(CommercialOfflineRevocationList.id)))
    crl_count = crl_result.scalar() or 0

    attestation_result = await session.execute(
        select(CommercialHardwareAttestationRecord.status, func.count(CommercialHardwareAttestationRecord.id))
        .group_by(CommercialHardwareAttestationRecord.status)
    )
    attestation_summary = {row[0]: int(row[1]) for row in attestation_result.all()}

    return {
        "policies_replicated": policies_replicated,
        "audit_events_federated": audit_events,
        "consistency_status": consistency.get("overall_status", "unknown"),
        "region_coverage": len(regions),
        "recent_events": recent_events,
        "airgap_packages": visible_packages,
        "airgap_package_count": len(visible_packages),
        "export_restrictions": {
            "sovereign_classification": "sovereign_restricted",
            "online_federation_blocked": True,
            "requires_encrypted_airgap": True,
            "requires_signed_manifest": True,
        },
        "offline_crl_count": int(crl_count),
        "attestation_summary": attestation_summary,
    }
