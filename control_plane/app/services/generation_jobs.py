from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.metrics import ASYNC_JOB_COUNTER, ASYNC_QUEUE_DEPTH
from app.core.time import utc_now
from app.db.session import redis_client
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.models.generation_job import GenerationJob
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.schemas.inference import ChatCompletionRequest
from app.services.audit import log_request
from app.services.backend_slot_manager import BackendSlotManager
from app.services.billing import (
    estimate_request_cost,
    get_current_usage_snapshot,
)
from app.services.billing.core import resolve_effective_plan_for_session
from app.services.context_manager import get_context_manager
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import plan_routing_order, resolve_requested_model
from app.services.quota import QuotaExceeded, ensure_quota, record_usage
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.services.response_cache import build_chat_cache_key, lookup_exact_cache, store_exact_cache
from app.services.security_monitor import (
    maybe_record_plan_usage_anomaly,
    maybe_record_repeated_large_prompt,
    maybe_record_request_error_burst,
    prompt_fingerprint,
)
from app.utils.request_summary import summarize_chat_request
from app.utils.token_estimator import estimate_tokens_from_text
from app.utils.validation import normalize_messages, validate_params_for_session
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


@dataclass
class PreparedAsyncChatJob:
    selected_model_id: str
    selected_model_db_id: uuid.UUID
    requested_model: str
    request_body: dict
    prompt_tokens: int
    max_tokens: int
    estimated_request_cost: float
    request_summary: str
    token_count_method: str | None = None
    tokens_estimated: bool = True


def _parse_json(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def serialize_job(job: GenerationJob) -> dict:
    return {
        "id": str(job.id),
        "client_id": str(job.client_id),
        "model_registry_id": str(job.model_registry_id) if job.model_registry_id else None,
        "inference_backend_id": str(job.inference_backend_id) if job.inference_backend_id else None,
        "endpoint": job.endpoint,
        "requested_model": job.requested_model,
        "resolved_model": job.resolved_model,
        "status": job.status,
        "include_reasoning": job.include_reasoning,
        "backend_name": job.backend_name,
        "attempts": job.attempts,
        "fallback_used": job.fallback_used,
        "prompt_tokens_estimated": job.prompt_tokens_estimated,
        "completion_tokens_estimated": job.completion_tokens_estimated,
        "estimated_cost_usd": float(job.estimated_cost_usd or 0),
        "max_tokens_requested": job.max_tokens_requested,
        "response": _parse_json(job.response_json),
        "error": job.error_message,
        "backend_errors": _parse_json(job.backend_errors_json) or [],
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "cancelled_at": job.cancelled_at.isoformat() if job.cancelled_at else None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


async def prepare_async_chat_job(
    session: AsyncSession,
    redis: Redis,
    client: Client,
    payload: ChatCompletionRequest,
) -> PreparedAsyncChatJob:
    if payload.stream:
        raise HTTPException(status_code=422, detail="stream is not supported for async jobs")
    selected_model, requested_model = await resolve_requested_model(
        session,
        client=client,
        requested_model=payload.model,
    )
    # Normalize messages (handling content parts)
    messages = normalize_messages([item.model_dump() for item in payload.messages])
    
    # Apply Client System Prompt if available
    if client.system_prompt:
        system_msg_idx = next((i for i, m in enumerate(messages) if m["role"] == "system"), None)
        if system_msg_idx is not None:
            messages[system_msg_idx]["content"] = f"{client.system_prompt}\n\n{messages[system_msg_idx]['content']}"
        else:
            messages.insert(0, {"role": "system", "content": client.system_prompt})

    # Manage Context
    from app.services.tokenizer_service import get_tokenizer_service
    tokenizer = get_tokenizer_service()
    cm = get_context_manager()
    messages, max_tokens_capped, context_metrics = await cm.manage(
        messages=messages,
        requested_max_tokens=payload.max_tokens,
        model_id=selected_model.model_id,
        tokenizer=tokenizer,
    )

    prompt_tokens = context_metrics["final_tokens_estimate"]
    token_count_method = context_metrics.get("token_count_method", "estimated")
    tokens_estimated = context_metrics.get("tokens_estimated", True)
    if prompt_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit after management")

    import logging
    logging.getLogger(__name__).info(
        "Async inference context optimized",
        extra={"extra_data": context_metrics}
    )

    max_tokens, temperature, top_p, effective_plan = await validate_params_for_session(session, client, payload)
    max_tokens = max_tokens_capped
    
    incoming_tokens = prompt_tokens + max_tokens
    try:
        await enforce_rate_limit(redis, client.id, effective_plan.rate_limit_per_minute)
        await ensure_quota(
            session,
            client.id,
            effective_plan.daily_token_quota,
            effective_plan.weekly_token_quota,
            effective_plan.monthly_token_quota,
            incoming_tokens,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    body = payload.model_dump(exclude={"include_reasoning"})
    body["messages"] = messages
    body["model"] = selected_model.model_id
    body["max_tokens"] = max_tokens
    body["temperature"] = temperature
    body["top_p"] = top_p
    usage_snapshot = await get_current_usage_snapshot(session, client.id)
    daily_used_before = int(usage_snapshot["daily"].used_tokens) if usage_snapshot["daily"] else 0
    weekly_used_before = int(usage_snapshot["weekly"].used_tokens) if usage_snapshot["weekly"] else 0
    monthly_used_before = int(usage_snapshot["monthly"].used_tokens) if usage_snapshot["monthly"] else 0
    estimated_request_cost = float(
        estimate_request_cost(
            monthly_tokens_used_before=monthly_used_before,
            request_tokens=incoming_tokens,
            included_monthly_tokens=effective_plan.monthly_token_quota,
            overage_price_per_1k_tokens=effective_plan.overage_price_per_1k_tokens,
        )
    )
    request_summary = summarize_chat_request(
        messages,
        include_reasoning=payload.include_reasoning,
    )
    await maybe_record_repeated_large_prompt(
        session,
        redis,
        client=client,
        prompt_tokens=prompt_tokens,
        prompt_key=prompt_fingerprint(json.dumps(messages, sort_keys=True, ensure_ascii=True)),
        endpoint="/v1/chat/completions/async",
    )
    await maybe_record_plan_usage_anomaly(
        session,
        client=client,
        daily_limit=effective_plan.daily_token_quota,
        weekly_limit=effective_plan.weekly_token_quota,
        monthly_limit=effective_plan.monthly_token_quota,
        incoming_tokens=incoming_tokens,
        daily_used_before=daily_used_before,
        weekly_used_before=weekly_used_before,
        monthly_used_before=monthly_used_before,
    )
    return PreparedAsyncChatJob(
        selected_model_id=selected_model.model_id,
        selected_model_db_id=selected_model.id,
        requested_model=requested_model,
        request_body={**body, "include_reasoning": payload.include_reasoning},
        prompt_tokens=prompt_tokens,
        max_tokens=max_tokens,
        estimated_request_cost=estimated_request_cost,
        request_summary=request_summary,
        token_count_method=token_count_method,
        tokens_estimated=tokens_estimated,
    )


async def create_chat_generation_job(
    session: AsyncSession,
    redis: Redis,
    client: Client,
    payload: ChatCompletionRequest,
) -> GenerationJob:
    prepared = await prepare_async_chat_job(session, redis=redis, client=client, payload=payload)
    from app.services.routing.commercial_qos import CommercialQoSService
    from app.services.routing.qos_rate_limiter import QoSRateLimiter
    
    qos_tier = await CommercialQoSService.resolve_qos_tier(session, client.id, None)
    
    # QoS Phase 24: Rate Limiting
    rl = QoSRateLimiter(redis)
    is_allowed, rl_status, rl_reason = await rl.check_rate_limit(
        client.id, qos_tier.name, prepared.selected_model_id
    )
    
    if not is_allowed:
        raise HTTPException(status_code=429, detail=rl_reason)

    now = utc_now()
    
    # Calculate effective priority for Sorted Set
    priority_weight = qos_tier.queue_priority
    created_at_ms = int(now.timestamp() * 1000)
    effective_priority = -(priority_weight * 1_000_000) + created_at_ms

    job = GenerationJob(
        client_id=client.id,
        model_registry_id=prepared.selected_model_db_id,
        endpoint="/v1/chat/completions/async",
        requested_model=prepared.requested_model,
        resolved_model=prepared.selected_model_id,
        status="queued",
        is_stream=False,
        include_reasoning=payload.include_reasoning,
        request_json=json.dumps(prepared.request_body),
        prompt_tokens_estimated=prepared.prompt_tokens,
        token_count_method=prepared.token_count_method,
        tokens_estimated=prepared.tokens_estimated,
        estimated_cost_usd=prepared.estimated_request_cost,
        max_tokens_requested=prepared.max_tokens,
        priority=qos_tier.queue_priority,
        # New Phase 24 fields
        qos_tier=qos_tier.name,
        effective_priority=effective_priority,
        rate_limit_status=rl_status,
        rate_limit_reason=rl_reason,
        queued_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    await session.flush()
    return job


async def enqueue_generation_job(redis: Redis, job_id: uuid.UUID, priority: int = 100, effective_priority: float = 0) -> None:
    settings = get_settings()
    
    # 1. Legacy Enqueue (Always if not active, or if shadow)
    if not settings.commercial_qos_priority_queue_enabled or settings.commercial_qos_priority_queue_mode != "active":
        queue_depth = await redis.rpush(settings.async_job_queue_name, str(job_id))
        ASYNC_QUEUE_DEPTH.set(int(queue_depth))
    
    # 2. QoS Priority Queue (if enabled or shadow)
    if settings.commercial_qos_priority_queue_enabled:
        from app.services.routing.qos_priority_queue import QoSPriorityQueue
        pq = QoSPriorityQueue(redis)
        # Use provided effective_priority if available, otherwise calculate
        if effective_priority == 0:
            now_ms = int(time.time() * 1000)
            effective_priority = -(priority * 1_000_000) + now_ms
            
        await pq.enqueue(job_id, priority, int(time.time() * 1000)) # Simple enqueue for now
        # Re-using the calculated score if we want exact same score
        await redis.zadd(QoSPriorityQueue.QUEUE_KEY, {str(job_id): effective_priority})
        
    ASYNC_JOB_COUNTER.labels(status="queued").inc()


async def get_job_for_client(session: AsyncSession, client_id: uuid.UUID, job_id: uuid.UUID) -> GenerationJob | None:
    result = await session.execute(
        select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.client_id == client_id)
    )
    return result.scalar_one_or_none()


async def cancel_job(session: AsyncSession, client_id: uuid.UUID, job_id: uuid.UUID) -> GenerationJob:
    job = await get_job_for_client(session, client_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "queued":
        raise HTTPException(status_code=409, detail="job can only be cancelled while queued")
    now = utc_now()
    job.status = "cancelled"
    job.cancelled_at = now
    job.updated_at = now
    ASYNC_JOB_COUNTER.labels(status="cancelled").inc()
    await session.flush()
    return job


async def get_admin_job_snapshot(session: AsyncSession, redis: Redis) -> dict:
    summary_row = (
        await session.execute(
            select(
                func.count(GenerationJob.id).label("total"),
                func.count().filter(GenerationJob.status == "queued").label("queued"),
                func.count().filter(GenerationJob.status == "running").label("running"),
                func.count().filter(GenerationJob.status == "completed").label("completed"),
                func.count().filter(GenerationJob.status == "failed").label("failed"),
                func.count().filter(GenerationJob.status == "cancelled").label("cancelled"),
            )
        )
    ).mappings().one()
    jobs = (
        await session.execute(select(GenerationJob).order_by(desc(GenerationJob.created_at)).limit(200))
    ).scalars().all()
    queue_depth = int(await redis.llen(get_settings().async_job_queue_name))
    ASYNC_QUEUE_DEPTH.set(queue_depth)
    return {
        "summary": {
            "total": int(summary_row["total"] or 0),
            "queued": int(summary_row["queued"] or 0),
            "running": int(summary_row["running"] or 0),
            "completed": int(summary_row["completed"] or 0),
            "failed": int(summary_row["failed"] or 0),
            "cancelled": int(summary_row["cancelled"] or 0),
            "queue_depth_redis": queue_depth,
        },
        "jobs": [serialize_job(job) for job in jobs],
    }


async def process_generation_job(
    session: AsyncSession,
    job_id: uuid.UUID,
    proxy: InferenceProxy,
    slot_manager: BackendSlotManager,
) -> str:
    result = await session.execute(
        select(GenerationJob)
        .options(
            selectinload(GenerationJob.client).selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules),
            selectinload(GenerationJob.model_registry)
            .selectinload(ModelRegistry.backend_routes)
            .selectinload(ModelBackendRoute.inference_backend),
        )
        .where(GenerationJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        return "missing"
    
    # Explicitly load client with all billing relationships to avoid MissingGreenlet
    client_result = await session.execute(
        select(Client)
        .options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules))
        .where(Client.id == job.client_id)
    )
    client = client_result.scalar_one_or_none()
    if client is None:
        return "missing"

    if job.status in {"completed", "failed", "cancelled"}:
        return "skipped"
    if job.status != "queued":
        return "skipped"
    if client.is_blocked or client.billing_status == "suspended":
        now = utc_now()
        job.status = "failed"
        job.error_message = "client blocked, missing or suspended"
        job.completed_at = now
        job.updated_at = now
        await session.commit()
        ASYNC_JOB_COUNTER.labels(status="failed").inc()
        return "failed"

    effective_plan = await resolve_effective_plan_for_session(session, client)

    request_body = json.loads(job.request_json)
    include_reasoning = bool(request_body.pop("include_reasoning", False))
    cache_key, cache_fingerprint = build_chat_cache_key(
        model=job.resolved_model,
        messages=request_body.get("messages", []),
        temperature=request_body.get("temperature"),
        top_p=request_body.get("top_p"),
        max_tokens=request_body.get("max_tokens"),
        include_reasoning=include_reasoning,
    )
    cached = await lookup_exact_cache(
        session,
        endpoint="/v1/chat/completions",
        model=job.resolved_model,
        request_hash=cache_key,
        plan_code=effective_plan.code,
    )
    if cached.hit and cached.payload is not None:
        now = utc_now()
        await record_usage(
            session, 
            job.client_id, 
            job.prompt_tokens_estimated, 
            cached.completion_tokens,
            token_count_method=job.token_count_method,
            tokens_estimated=job.tokens_estimated
        )
        await log_request(
            session,
            client_id=job.client_id,
            model=job.resolved_model,
            endpoint="/v1/chat/completions/async",
            prompt_tokens=job.prompt_tokens_estimated,
            completion_tokens=cached.completion_tokens,
            latency_ms=0,
            status_code=200,
            is_stream=False,
            estimated_cost_usd=float(job.estimated_cost_usd or 0),
            backend_name="cache:exact",
            attempts=0,
            fallback_used=False,
            cache_hit=True,
            backend_errors=[],
            error_message=None,
            request_summary=summarize_chat_request(request_body.get("messages", []), include_reasoning=include_reasoning),
            plan_code=effective_plan.code,
            request_payload=request_body,
            response_payload=cached.payload,
            reproducibility_context={
                "model_alias": selected_model.model_alias if selected_model else None,
                "provider": selected_model.provider if selected_model else None,
                "prompt_template": selected_model.prompt_template if selected_model else None,
                "runtime_engine": selected_model.provider if selected_model else None,
                "model_metadata_json": selected_model.metadata_json if selected_model else None,
                "metadata_json": {"cache_hit": True, "async_job": True},
            },
        )
        job.status = "completed"
        job.backend_name = "cache:exact"
        job.response_json = json.dumps(cached.payload)
        job.attempts = 0
        job.fallback_used = False
        job.completion_tokens_estimated = cached.completion_tokens
        job.completed_at = now
        job.updated_at = now
        await session.commit()
        ASYNC_JOB_COUNTER.labels(status="completed").inc()
        return "completed"

    selected_model = job.model_registry
    if selected_model is None:
        now = utc_now()
        job.status = "failed"
        job.error_message = "configured model no longer exists"
        job.completed_at = now
        job.updated_at = now
        await session.commit()
        ASYNC_JOB_COUNTER.labels(status="failed").inc()
        return "failed"

    chosen_route = None
    for route in plan_routing_order(selected_model):
        backend = route.inference_backend
        if backend is None:
            continue
        if await slot_manager.try_acquire(backend.id):
            chosen_route = route
            break
    if chosen_route is None:
        ASYNC_QUEUE_DEPTH.set(int(await redis_client.llen(get_settings().async_job_queue_name)))
        return "requeue"

    now = utc_now()
    job.status = "running"
    job.started_at = now
    job.dequeued_at = now
    if job.queued_at:
        wait_delta = now - job.queued_at
        job.queue_wait_ms = int(wait_delta.total_seconds() * 1000)
    
    job.updated_at = now
    job.inference_backend_id = chosen_route.inference_backend_id
    job.backend_name = chosen_route.inference_backend.name if chosen_route.inference_backend else None
    await session.commit()

    is_admin = False
    if client.metadata_json:
        try:
            metadata = json.loads(client.metadata_json)
            is_admin = metadata.get("is_admin", False)
        except json.JSONDecodeError:
            pass

    try:
        result = await proxy.chat(
            request_body,
            False,
            include_reasoning,
            backend=chosen_route.inference_backend.provider,
            backend_url=chosen_route.inference_backend.backend_url,
            backend_name=chosen_route.inference_backend.name,
            backend_id=chosen_route.inference_backend.id,
            prompt_template=selected_model.prompt_template,
            manage_slot=False,
            plan_code=effective_plan.code,
            is_admin=is_admin,
        )
        response_payload = json.loads(result.response.body.decode("utf-8"))
        completion_tokens = estimate_tokens_from_text(result.response.body.decode("utf-8"))
        await store_exact_cache(
            session,
            endpoint="/v1/chat/completions",
            model=job.resolved_model,
            request_hash=cache_key,
            request_fingerprint=cache_fingerprint,
            response_payload=response_payload,
            prompt_tokens=job.prompt_tokens_estimated,
            completion_tokens=completion_tokens,
        )
        await record_usage(
            session, 
            job.client_id, 
            job.prompt_tokens_estimated, 
            completion_tokens,
            token_count_method=job.token_count_method,
            tokens_estimated=job.tokens_estimated
        )
        await log_request(
            session,
            client_id=job.client_id,
            model=job.resolved_model,
            endpoint="/v1/chat/completions/async",
            prompt_tokens=job.prompt_tokens_estimated,
            completion_tokens=completion_tokens,
            latency_ms=0,
            status_code=result.response.status_code,
            is_stream=False,
            estimated_cost_usd=float(job.estimated_cost_usd or 0),
            backend_name=result.backend_name,
            attempts=result.attempts,
            fallback_used=result.fallback_used,
            cache_hit=False,
            backend_errors=result.backend_errors,
            error_message=None,
            request_summary=summarize_chat_request(request_body.get("messages", []), include_reasoning=include_reasoning),
            plan_code=effective_plan.code,
            request_payload=request_body,
            response_payload=response_payload,
            reproducibility_context={
                "model_alias": selected_model.model_alias,
                "provider": chosen_route.inference_backend.provider,
                "prompt_template": selected_model.prompt_template,
                "runtime_engine": chosen_route.inference_backend.provider,
                "model_metadata_json": selected_model.metadata_json,
                "backend_metadata_json": chosen_route.inference_backend.metadata_json,
                "metadata_json": {"async_job": True},
            },
        )
        finished_at = utc_now()
        job.status = "completed"
        job.response_json = json.dumps(response_payload)
        job.attempts = result.attempts
        job.fallback_used = result.fallback_used
        job.backend_errors_json = json.dumps(result.backend_errors) if result.backend_errors else None
        job.completion_tokens_estimated = completion_tokens
        job.completed_at = finished_at
        job.updated_at = finished_at
        await session.commit()
        ASYNC_JOB_COUNTER.labels(status="completed").inc()
        return "completed"
    except HTTPException as exc:
        finished_at = utc_now()
        backend_errors = exc.detail.get("backend_errors", []) if isinstance(exc.detail, dict) else []
        await log_request(
            session,
            client_id=job.client_id,
            model=job.resolved_model,
            endpoint="/v1/chat/completions/async",
            prompt_tokens=job.prompt_tokens_estimated,
            completion_tokens=0,
            latency_ms=0,
            status_code=exc.status_code,
            is_stream=False,
            estimated_cost_usd=float(job.estimated_cost_usd or 0),
            backend_name=job.backend_name,
            attempts=max(len(backend_errors), 1),
            fallback_used=len(backend_errors) > 1,
            cache_hit=False,
            backend_errors=backend_errors,
            error_message=str(exc.detail.get("message")) if isinstance(exc.detail, dict) else str(exc.detail),
            request_summary=summarize_chat_request(request_body.get("messages", []), include_reasoning=include_reasoning),
            plan_code=effective_plan.code,
            request_payload=request_body,
            response_payload=None,
            reproducibility_context={
                "model_alias": selected_model.model_alias,
                "provider": chosen_route.inference_backend.provider,
                "prompt_template": selected_model.prompt_template,
                "runtime_engine": chosen_route.inference_backend.provider,
                "model_metadata_json": selected_model.metadata_json,
                "backend_metadata_json": chosen_route.inference_backend.metadata_json,
                "metadata_json": {"async_job": True, "audit_event": "replay_failed"},
            },
        )
        job.status = "failed"
        job.error_message = str(exc.detail.get("message")) if isinstance(exc.detail, dict) else str(exc.detail)
        job.attempts = max(len(backend_errors), 1)
        job.fallback_used = len(backend_errors) > 1
        job.backend_errors_json = json.dumps(backend_errors) if backend_errors else None
        job.completed_at = finished_at
        job.updated_at = finished_at
        await maybe_record_request_error_burst(
            session,
            redis_client,
            client_id=job.client_id,
            endpoint="/v1/chat/completions/async",
            status_code=exc.status_code,
            backend_name=job.backend_name,
        )
        await session.commit()
        ASYNC_JOB_COUNTER.labels(status="failed").inc()
        return "failed"
    finally:
        await slot_manager.release(chosen_route.inference_backend_id)
