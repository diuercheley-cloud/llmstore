import json
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
from app.services.model_policy import resolve_requested_model
from app.services.quota import QuotaExceeded, ensure_quota, record_usage
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.services.response_cache import build_chat_cache_key, lookup_exact_cache, store_exact_cache
from app.utils.request_summary import summarize_chat_request
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text

from app.models.billing_plan import BillingPlan
from app.models.pricing_rule import PricingRule
from app.schemas.public import PortalUpgradeRequest
from app.services.public_onboarding import list_public_plans

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
    effective_plan = resolve_effective_plan(client)
    return {
        "id": str(client.id),
        "name": client.name,
        "description": client.description,
        "billing_status": client.billing_status,
        "is_blocked": client.is_blocked,
        "metadata_json": client.metadata_json,
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
        },
    }


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
            )
            await session.commit()
            payload_json = cached.payload
            return {
                "model": selected_model.model_id,
                "cached": True,
                "response": payload_json,
                "text": (((payload_json.get("choices") or [{}])[0].get("message") or {}).get("content")) or "",
            }

        result = await _chat_with_fallback(proxy, selected_model, body, False, False)
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
        )
        await session.commit()
        raise
