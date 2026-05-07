import json
from datetime import date, datetime, timezone
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from app.api.client import _chat_with_fallback, _error_message_for_log, _backend_errors_for_log
from app.core.security import short_prefix
from app.core.time import utc_now
from app.utils.validation import validate_params
from app.api.deps import get_inference_proxy
from app.db.session import get_db_session, get_redis
from app.models.billing_invoice import BillingInvoice
from app.models.client import Client
from app.models.customer_payment import CustomerPayment
from app.schemas.inference import ChatCompletionRequest, PortalTestChatRequest, OnboardingEventRequest
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
from app.services.quota import month_start, ensure_quota, record_usage, QuotaExceeded
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.services.response_cache import build_chat_cache_key, lookup_exact_cache, store_exact_cache
from app.utils.request_summary import summarize_chat_request
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text

from app.models.billing_plan import BillingPlan
from app.models.pricing_rule import PricingRule
from app.models.api_key import ApiKey
from app.models.request_log import RequestLog
from app.models.model_registry import ModelRegistry
from app.schemas.public import PortalUpgradeRequest
from app.schemas.admin import ApiKeyCreate, ApiKeyCreated
from app.services.public_onboarding import list_public_plans
from app.core.security import generate_api_key, hash_secret, short_prefix

router = APIRouter(tags=["portal"])


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
        "metadata_json": client.metadata_json,
        "demo_mode": settings.demo_mode,
        "plan": {
            "code": effective_plan.code,
            "name": effective_plan.name,
            "rate_limit_per_minute": effective_plan.rate_limit_per_minute,
            "daily_token_quota": effective_plan.daily_token_quota,
            "weekly_token_quota": effective_plan.weekly_token_quota,
            "monthly_token_quota": effective_plan.monthly_token_quota,
            "max_output_tokens": effective_plan.max_output_tokens,
            "allow_streaming": effective_plan.allow_streaming,
            "monthly_price": float(effective_plan.monthly_price),
            "currency": effective_plan.currency,
            "rag_max_documents": effective_plan.rag_max_documents,
            "rag_max_storage_mb": effective_plan.rag_max_storage_mb,
            "rag_max_pages_per_month": effective_plan.rag_max_pages_per_month,
            "rag_max_queries_per_month": effective_plan.rag_max_queries_per_month,
        },
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
    
    return {
        "daily_usage": [
            {"day": str(r.day), "tokens": int(r.tokens or 0), "requests": int(r.requests or 0)}
            for r in daily_results
        ],
        "model_usage": [
            {"model": r.model, "requests": int(r.requests or 0), "tokens": int(r.tokens or 0)}
            for r in model_results
        ],
        "total_requests_this_month": total_requests
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
    
    allowed_models = []
    for m in all_models:
        if allowed and m.model_id not in allowed and (m.model_alias or "") not in allowed:
            continue
                
        allowed_models.append({
            "id": m.model_id,
            "alias": m.model_alias,
            "display_name": m.model_alias or m.model_id,
            "context_length": m.context_length,
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
            "max_output_tokens": effective_plan.max_output_tokens,
        },
        "usage": {
            "daily_used_tokens": daily_used,
            "weekly_used_tokens": weekly_used,
            "monthly_used_tokens": monthly_used,
        }
    }


@router.get("/usage")
async def portal_usage(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    effective_plan = resolve_effective_plan(client)
    counters = await get_current_usage_snapshot(session, client.id)
    daily_used = int(counters["daily"].used_tokens) if counters["daily"] else 0
    weekly_used = int(counters["weekly"].used_tokens) if counters["weekly"] else 0
    monthly_used = int(counters["monthly"].used_tokens) if counters["monthly"] else 0
    invoice_preview = build_invoice_preview(effective_plan=effective_plan, monthly_used_tokens=monthly_used)
    return {
        "client_id": str(client.id),
        "billing_status": client.billing_status,
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
        "invoice_preview": invoice_preview,
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

        result = await _chat_with_fallback(proxy, selected_model, body, False, False, client=client)
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
