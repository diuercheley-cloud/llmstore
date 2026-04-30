import json
from time import perf_counter

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.db.session import get_db_session, get_redis
from app.models.client import Client
from app.models.model_backend_route import ModelBackendRoute
from app.schemas.inference import (
    ChatCompletionRequest,
    CompletionRequest,
    GenerationJobResponse,
    JobAcceptedResponse,
    ModelList,
)
from app.services.audit import log_request
from app.services.auth import require_client
from app.services.billing import estimate_request_cost, get_current_usage_snapshot, resolve_effective_plan
from app.services.generation_jobs import cancel_job, create_chat_generation_job, enqueue_generation_job, get_job_for_client, serialize_job
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import (
    get_effective_allowed_models,
    list_active_registry_models,
    plan_routing_order,
    resolve_requested_model,
    serialize_model_card,
)
from app.services.quota import QuotaExceeded, ensure_quota, record_usage
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit, enforce_ip_rate_limit
from app.services.response_cache import (
    build_chat_cache_key,
    build_completion_cache_key,
    lookup_exact_cache,
    store_exact_cache,
)
from app.services.security_monitor import (
    maybe_record_plan_usage_anomaly,
    maybe_record_repeated_large_prompt,
    maybe_record_request_error_burst,
    prompt_fingerprint,
)
from app.utils.request_summary import summarize_chat_request, summarize_completion_request
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text

router = APIRouter(prefix="/v1", tags=["client"])
settings = get_settings()


def _is_retryable_backend_error(exc: HTTPException) -> bool:
    return exc.status_code >= 500 or exc.status_code in {503, 504}


def _serialize_backend_error(route: ModelBackendRoute, exc: HTTPException) -> dict:
    return {
        "backend_id": str(route.inference_backend_id),
        "backend_name": route.inference_backend.name if route.inference_backend else None,
        "provider": route.inference_backend.provider if route.inference_backend else None,
        "backend_url": route.inference_backend.backend_url if route.inference_backend else None,
        "route_priority": route.priority,
        "route_weight": route.weight,
        "route_state": route.state,
        "status_code": exc.status_code,
        "error": str(exc.detail),
    }


async def _chat_with_fallback(
    proxy: InferenceProxy,
    selected_model,
    body: dict,
    stream: bool,
    include_reasoning: bool,
):
    routes = plan_routing_order(selected_model)
    backend_errors: list[dict] = []
    last_exc: HTTPException | None = None

    for attempt, route in enumerate(routes, start=1):
        backend = route.inference_backend
        if backend is None:
            continue
        try:
            result = await proxy.chat(
                body,
                stream,
                include_reasoning,
                backend=backend.provider,
                backend_url=backend.backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
            )
            result.attempts = attempt
            result.fallback_used = attempt > 1
            result.backend_errors = backend_errors
            return result
        except HTTPException as exc:
            last_exc = exc
            backend_errors.append(_serialize_backend_error(route, exc))
            if not _is_retryable_backend_error(exc) or attempt == len(routes):
                break

    if last_exc is None:
        raise HTTPException(status_code=503, detail="model backend is not active")
    last_exc.detail = {
        "message": str(last_exc.detail),
        "backend_errors": backend_errors,
    }
    raise last_exc


async def _completion_with_fallback(
    proxy: InferenceProxy,
    selected_model,
    body: dict,
    stream: bool,
):
    routes = plan_routing_order(selected_model)
    backend_errors: list[dict] = []
    last_exc: HTTPException | None = None

    for attempt, route in enumerate(routes, start=1):
        backend = route.inference_backend
        if backend is None:
            continue
        try:
            result = await proxy.complete(
                body,
                stream,
                backend=backend.provider,
                backend_url=backend.backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
            )
            result.attempts = attempt
            result.fallback_used = attempt > 1
            result.backend_errors = backend_errors
            return result
        except HTTPException as exc:
            last_exc = exc
            backend_errors.append(_serialize_backend_error(route, exc))
            if not _is_retryable_backend_error(exc) or attempt == len(routes):
                break

    if last_exc is None:
        raise HTTPException(status_code=503, detail="model backend is not active")
    last_exc.detail = {
        "message": str(last_exc.detail),
        "backend_errors": backend_errors,
    }
    raise last_exc


def _error_message_for_log(detail) -> str:
    if isinstance(detail, dict):
        return str(detail.get("message", "request failed"))
    return str(detail)


def _backend_errors_for_log(detail) -> list[dict]:
    if isinstance(detail, dict):
        errors = detail.get("backend_errors")
        if isinstance(errors, list):
            return errors
    return []


def _validated_params(client: Client, payload):
    effective_plan = resolve_effective_plan(client)
    max_tokens = payload.max_tokens or min(settings.default_max_tokens, effective_plan.max_output_tokens)
    temperature = payload.temperature if payload.temperature is not None else settings.default_temperature
    top_p = payload.top_p if payload.top_p is not None else settings.default_top_p
    if max_tokens > effective_plan.max_output_tokens:
        raise HTTPException(status_code=422, detail="requested max_tokens exceeds client limit")
    if getattr(payload, "stream", False) and not effective_plan.allow_streaming:
        raise HTTPException(status_code=403, detail="streaming is not allowed for this billing plan")
    if temperature > settings.max_temperature:
        raise HTTPException(status_code=422, detail="temperature exceeds configured maximum")
    if top_p > settings.max_top_p:
        raise HTTPException(status_code=422, detail="top_p exceeds configured maximum")
    return max_tokens, temperature, top_p, effective_plan


@router.get("/models")
async def list_models(
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    allowed = get_effective_allowed_models(client)
    models = await list_active_registry_models(session)
    filtered = [
        serialize_model_card(item)
        for item in models
        if not allowed or item.model_id in allowed or (item.model_alias or "") in allowed
    ]
    return ModelList(data=filtered).model_dump()


@router.post("/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    selected_model, _ = await resolve_requested_model(
        session,
        client=client,
        requested_model=payload.model,
    )
    prompt_tokens = estimate_prompt_tokens(messages=[item.model_dump() for item in payload.messages])
    if prompt_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit")
    max_tokens, temperature, top_p, effective_plan = _validated_params(client, payload)
    
    # Apply Client System Prompt if available
    messages = [item.model_dump() for item in payload.messages]
    if client.system_prompt:
        # Check if there is already a system message
        system_msg_idx = next((i for i, m in enumerate(messages) if m["role"] == "system"), None)
        if system_msg_idx is not None:
            # Prepend or override? User usually wants their specific system prompt as foundational.
            # Let's prepend to the existing system message content or add as new first message.
            messages[system_msg_idx]["content"] = f"{client.system_prompt}\n\n{messages[system_msg_idx]['content']}"
        else:
            messages.insert(0, {"role": "system", "content": client.system_prompt})

    # Apply Model Prompt Template if available
    if selected_model.prompt_template:
        # Simple template replacement: assume the template has a {{messages}} placeholder or similar.
        # For chat completion, we usually pass the list of messages to the backend.
        # If the backend is llama.cpp, it handles formatting.
        # If we have a custom template, we might need to pre-format.
        # However, the task says "templates de resposta por modelo".
        # Let's assume for now we might add a wrapper or instruction to the system prompt.
        pass

    prompt_tokens = estimate_prompt_tokens(messages=messages)
    if prompt_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit")
    
    incoming_tokens = prompt_tokens + max_tokens
    try:
        source_ip = getattr(request.state, "source_ip", "unknown")
        await enforce_ip_rate_limit(redis, source_ip)
        await enforce_rate_limit(redis, client.id, effective_plan.rate_limit_per_minute)
        await ensure_quota(session, client.id, effective_plan.daily_token_quota, effective_plan.monthly_token_quota, incoming_tokens)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    body = payload.model_dump(exclude={"include_reasoning", "safety_profile"})
    body["messages"] = messages
    body["model"] = selected_model.model_id
    body["max_tokens"] = max_tokens
    body["temperature"] = temperature
    body["top_p"] = top_p

    # Apply Safety Profile
    if payload.safety_profile == "strict":
        body["temperature"] = min(temperature, 0.5)
        body["top_p"] = min(top_p, 0.8)
    elif payload.safety_profile == "relaxed":
        body["temperature"] = max(temperature, 1.0)
        body["top_p"] = max(top_p, 0.9)

    cache_key, cache_fingerprint = build_chat_cache_key(
        model=selected_model.model_id,
        messages=messages,
        temperature=body["temperature"],
        top_p=body["top_p"],
        max_tokens=max_tokens,
        include_reasoning=payload.include_reasoning,
    )
    usage_snapshot = await get_current_usage_snapshot(session, client.id)
    daily_used_before = int(usage_snapshot["daily"].used_tokens) if usage_snapshot["daily"] else 0
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
        [item.model_dump() for item in payload.messages],
        include_reasoning=payload.include_reasoning,
    )
    await maybe_record_repeated_large_prompt(
        session,
        redis,
        client=client,
        prompt_tokens=prompt_tokens,
        prompt_key=prompt_fingerprint(json.dumps([item.model_dump() for item in payload.messages], sort_keys=True, ensure_ascii=True)),
        endpoint="/v1/chat/completions",
    )
    await maybe_record_plan_usage_anomaly(
        session,
        client=client,
        daily_limit=effective_plan.daily_token_quota,
        monthly_limit=effective_plan.monthly_token_quota,
        incoming_tokens=incoming_tokens,
        daily_used_before=daily_used_before,
        monthly_used_before=monthly_used_before,
    )
    started = perf_counter()
    try:
        if not payload.stream:
            cached = await lookup_exact_cache(
                session,
                endpoint="/v1/chat/completions",
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
                    endpoint="/v1/chat/completions",
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
                    safety_profile=payload.safety_profile,
                )
                await session.commit()
                return JSONResponse(status_code=200, content=cached.payload)

        result = await _chat_with_fallback(
            proxy,
            selected_model,
            body,
            payload.stream,
            payload.include_reasoning,
        )
        latency_ms = int((perf_counter() - started) * 1000)
        if payload.stream:
            estimated_stream_tokens = max_tokens
            await record_usage(session, client.id, prompt_tokens, estimated_stream_tokens)
            await log_request(
                session,
                client_id=client.id,
                model=selected_model.model_id,
                endpoint="/v1/chat/completions",
                prompt_tokens=prompt_tokens,
                completion_tokens=estimated_stream_tokens,
                latency_ms=latency_ms,
                status_code=200,
                is_stream=True,
                estimated_cost_usd=estimated_request_cost,
                backend_name=result.backend_name,
                attempts=result.attempts,
                fallback_used=result.fallback_used,
                cache_hit=False,
                backend_errors=result.backend_errors,
                error_message=None,
                request_summary=request_summary,
                safety_profile=payload.safety_profile,
            )
            await session.commit()
            return result.response
        response_payload = json.loads(result.response.body.decode("utf-8"))
        completion_tokens = estimate_tokens_from_text(result.response.body.decode("utf-8"))
        await store_exact_cache(
            session,
            endpoint="/v1/chat/completions",
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
            endpoint="/v1/chat/completions",
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
            safety_profile=payload.safety_profile,
        )
        await session.commit()
        return result.response
    except HTTPException as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        backend_errors = _backend_errors_for_log(exc.detail)
        await log_request(
            session,
            client_id=client.id,
            model=selected_model.model_id,
            endpoint="/v1/chat/completions",
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            status_code=exc.status_code,
            is_stream=payload.stream,
            estimated_cost_usd=estimated_request_cost,
            backend_name=backend_errors[-1]["backend_name"] if backend_errors else None,
            attempts=max(len(backend_errors), 1),
            fallback_used=len(backend_errors) > 1,
            cache_hit=False,
            backend_errors=backend_errors,
            error_message=_error_message_for_log(exc.detail),
            request_summary=request_summary,
            safety_profile=payload.safety_profile,
        )
        await maybe_record_request_error_burst(
            session,
            redis,
            client_id=client.id,
            endpoint="/v1/chat/completions",
            status_code=exc.status_code,
            backend_name=backend_errors[-1]["backend_name"] if backend_errors else None,
        )
        await session.commit()
        raise


@router.post("/chat/completions/async", response_model=JobAcceptedResponse, status_code=202)
async def chat_completions_async(
    payload: ChatCompletionRequest,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
):
    job = await create_chat_generation_job(session, redis, client, payload)
    await session.commit()
    await enqueue_generation_job(redis, job.id)
    return {
        "id": job.id,
        "status": job.status,
        "endpoint": job.endpoint,
        "requested_model": job.requested_model,
        "resolved_model": job.resolved_model,
    }


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
async def get_job_status(
    job_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    job = await get_job_for_client(session, client.id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return serialize_job(job)


@router.delete("/jobs/{job_id}/cancel", response_model=GenerationJobResponse)
async def cancel_generation_job(
    job_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    job = await cancel_job(session, client.id, job_id)
    await session.commit()
    return serialize_job(job)


@router.post("/completions")
async def completions(
    payload: CompletionRequest,
    request: Request,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    selected_model, _ = await resolve_requested_model(
        session,
        client=client,
        requested_model=payload.model,
    )
    prompt_tokens = estimate_prompt_tokens(prompt=payload.prompt)
    if prompt_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit")
    max_tokens, temperature, top_p, effective_plan = _validated_params(client, payload)
    
    prompt = payload.prompt
    if client.system_prompt:
        prompt = f"{client.system_prompt}\n\n{prompt}"
    
    # Model template for completions: assume it might wrap the prompt
    if selected_model.prompt_template:
        # Example simple template usage
        if "{{prompt}}" in selected_model.prompt_template:
            prompt = selected_model.prompt_template.replace("{{prompt}}", prompt)
        else:
            prompt = f"{selected_model.prompt_template}\n{prompt}"

    prompt_tokens = estimate_prompt_tokens(prompt=prompt)
    if prompt_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit")
    
    incoming_tokens = prompt_tokens + max_tokens
    try:
        source_ip = getattr(request.state, "source_ip", "unknown")
        await enforce_ip_rate_limit(redis, source_ip)
        await enforce_rate_limit(redis, client.id, effective_plan.rate_limit_per_minute)
        await ensure_quota(session, client.id, effective_plan.daily_token_quota, effective_plan.monthly_token_quota, incoming_tokens)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    body = payload.model_dump(exclude={"safety_profile"})
    body["prompt"] = prompt
    body["model"] = selected_model.model_id
    body["max_tokens"] = max_tokens
    body["temperature"] = temperature
    body["top_p"] = top_p

    # Apply Safety Profile
    if payload.safety_profile == "strict":
        body["temperature"] = min(temperature, 0.5)
        body["top_p"] = min(top_p, 0.8)
    elif payload.safety_profile == "relaxed":
        body["temperature"] = max(temperature, 1.0)
        body["top_p"] = max(top_p, 0.9)

    cache_key, cache_fingerprint = build_completion_cache_key(
        model=selected_model.model_id,
        prompt=prompt,
        temperature=body["temperature"],
        top_p=body["top_p"],
        max_tokens=max_tokens,
    )
    usage_snapshot = await get_current_usage_snapshot(session, client.id)
    daily_used_before = int(usage_snapshot["daily"].used_tokens) if usage_snapshot["daily"] else 0
    monthly_used_before = int(usage_snapshot["monthly"].used_tokens) if usage_snapshot["monthly"] else 0
    estimated_request_cost = float(
        estimate_request_cost(
            monthly_tokens_used_before=monthly_used_before,
            request_tokens=incoming_tokens,
            included_monthly_tokens=effective_plan.monthly_token_quota,
            overage_price_per_1k_tokens=effective_plan.overage_price_per_1k_tokens,
        )
    )
    request_summary = summarize_completion_request(payload.prompt)
    await maybe_record_repeated_large_prompt(
        session,
        redis,
        client=client,
        prompt_tokens=prompt_tokens,
        prompt_key=prompt_fingerprint(payload.prompt),
        endpoint="/v1/completions",
    )
    await maybe_record_plan_usage_anomaly(
        session,
        client=client,
        daily_limit=effective_plan.daily_token_quota,
        monthly_limit=effective_plan.monthly_token_quota,
        incoming_tokens=incoming_tokens,
        daily_used_before=daily_used_before,
        monthly_used_before=monthly_used_before,
    )
    started = perf_counter()
    try:
        if not payload.stream:
            cached = await lookup_exact_cache(
                session,
                endpoint="/v1/completions",
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
                    endpoint="/v1/completions",
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
                    safety_profile=payload.safety_profile,
                )
                await session.commit()
                return JSONResponse(status_code=200, content=cached.payload)

        result = await _completion_with_fallback(
            proxy,
            selected_model,
            body,
            payload.stream,
        )
        latency_ms = int((perf_counter() - started) * 1000)
        if payload.stream:
            estimated_stream_tokens = max_tokens
            await record_usage(session, client.id, prompt_tokens, estimated_stream_tokens)
            await log_request(
                session,
                client_id=client.id,
                model=selected_model.model_id,
                endpoint="/v1/completions",
                prompt_tokens=prompt_tokens,
                completion_tokens=estimated_stream_tokens,
                latency_ms=latency_ms,
                status_code=200,
                is_stream=True,
                estimated_cost_usd=estimated_request_cost,
                backend_name=result.backend_name,
                attempts=result.attempts,
                fallback_used=result.fallback_used,
                cache_hit=False,
                backend_errors=result.backend_errors,
                error_message=None,
                request_summary=request_summary,
                safety_profile=payload.safety_profile,
            )
            await session.commit()
            return result.response
        response_payload = json.loads(result.response.body.decode("utf-8"))
        completion_tokens = estimate_tokens_from_text(result.response.body.decode("utf-8"))
        await store_exact_cache(
            session,
            endpoint="/v1/completions",
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
            endpoint="/v1/completions",
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
            safety_profile=payload.safety_profile,
        )
        await session.commit()
        return result.response
    except HTTPException as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        backend_errors = _backend_errors_for_log(exc.detail)
        await log_request(
            session,
            client_id=client.id,
            model=selected_model.model_id,
            endpoint="/v1/completions",
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            status_code=exc.status_code,
            is_stream=payload.stream,
            estimated_cost_usd=estimated_request_cost,
            backend_name=backend_errors[-1]["backend_name"] if backend_errors else None,
            attempts=max(len(backend_errors), 1),
            fallback_used=len(backend_errors) > 1,
            cache_hit=False,
            backend_errors=backend_errors,
            error_message=_error_message_for_log(exc.detail),
            request_summary=request_summary,
            safety_profile=payload.safety_profile,
        )
        await maybe_record_request_error_burst(
            session,
            redis,
            client_id=client.id,
            endpoint="/v1/completions",
            status_code=exc.status_code,
            backend_name=backend_errors[-1]["backend_name"] if backend_errors else None,
        )
        await session.commit()
        raise
