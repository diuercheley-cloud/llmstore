import json
import logging
from time import perf_counter

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.db.session import get_db_session, get_redis
from app.models.client import Client
from app.models.model_backend_route import ModelBackendRoute
from app.schemas.inference import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    EmbeddingsRequest,
    EmbeddingsResponse,
    GenerationJobResponse,
    JobAcceptedResponse,
    ModelList,
    ResponseOutput,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponsesRequest,
    ResponsesResponse,
    UsageInfo,
)
from app.services.audit import log_request
from app.services.auth import require_client
from app.services.billing import estimate_request_cost, get_current_usage_snapshot, resolve_effective_plan
from app.services.generation_jobs import cancel_job, create_chat_generation_job, enqueue_generation_job, get_job_for_client, serialize_job
from app.services.context_manager import ContextManager, get_context_manager
from app.services.embeddings_mock import process_mock_embeddings
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import (
    get_effective_allowed_models,
    list_active_registry_models,
    plan_routing_order,
    resolve_requested_model,
    serialize_model_card,
)
from app.services.quota import QuotaExceeded, ensure_quota, ensure_embeddings_quota, record_usage, record_embedding_usage
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
from app.utils.validation import normalize_messages, validate_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["client"])

settings = get_settings()


def _unsupported_feature_response(*, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": message,
                "type": "unsupported_feature",
                "code": code,
            }
        },
    )


def _response_compat_headers(
    *,
    requested_model: str,
    resolved_model: str,
    backend_name: str | None = None,
    fallback_used: bool | None = None,
) -> dict[str, str]:
    headers = {
        "X-Requested-Model": requested_model,
        "X-Resolved-Model": resolved_model,
    }
    if backend_name:
        headers["X-Backend-Name"] = backend_name
    if fallback_used is not None:
        headers["X-Fallback-Used"] = "true" if fallback_used else "false"
    return headers


def _apply_compat_headers(response: Response, headers: dict[str, str]) -> Response:
    for key, value in headers.items():
        if value:
            response.headers[key] = value
    return response


def _passthrough_response_headers(headers: dict[str, str]) -> dict[str, str]:
    excluded = {"content-length", "content-type"}
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in excluded
    }


def _responses_input_to_messages(payload: ResponsesRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if payload.instructions:
        messages.append({"role": "system", "content": payload.instructions})

    if isinstance(payload.input, str):
        messages.append({"role": "user", "content": payload.input})
        return messages

    for item in payload.input:
        if isinstance(item, str):
            messages.append({"role": "user", "content": item})
            continue

        content = item.content
        if isinstance(content, list):
            content_text = "\n".join(part.text for part in content)
        else:
            content_text = content
        messages.append({"role": item.role, "content": content_text})
    return messages


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
    client: Client | None = None,
):
    routes = plan_routing_order(selected_model, client=client)
    backend_errors: list[dict] = []
    last_exc: HTTPException | None = None

    plan_code = "free"
    is_admin = False
    if client:
        effective_plan = resolve_effective_plan(client)
        plan_code = effective_plan.code
        if client.metadata_json:
            try:
                metadata = json.loads(client.metadata_json)
                is_admin = metadata.get("is_admin", False)
            except json.JSONDecodeError:
                pass

    for attempt, route in enumerate(routes, start=1):
        backend = route.inference_backend
        if backend is None:
            continue
            
        api_key = None
        if backend.metadata_json:
            try:
                metadata = json.loads(backend.metadata_json)
                api_key = metadata.get("api_key")
            except json.JSONDecodeError:
                pass
                
        try:
            result = await proxy.chat(
                body,
                stream,
                include_reasoning,
                backend=backend.provider,
                backend_url=backend.backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
                prompt_template=selected_model.prompt_template,
                api_key=api_key,
                plan_code=plan_code,
                is_admin=is_admin,
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
    client: Client | None = None,
):
    routes = plan_routing_order(selected_model, client=client)
    backend_errors: list[dict] = []
    last_exc: HTTPException | None = None

    plan_code = "free"
    is_admin = False
    if client:
        effective_plan = resolve_effective_plan(client)
        plan_code = effective_plan.code
        if client.metadata_json:
            try:
                metadata = json.loads(client.metadata_json)
                is_admin = metadata.get("is_admin", False)
            except json.JSONDecodeError:
                pass

    for attempt, route in enumerate(routes, start=1):
        backend = route.inference_backend
        if backend is None:
            continue
            
        api_key = None
        if backend.metadata_json:
            try:
                metadata = json.loads(backend.metadata_json)
                api_key = metadata.get("api_key")
            except json.JSONDecodeError:
                pass

        try:
            result = await proxy.complete(
                body,
                stream,
                backend=backend.provider,
                backend_url=backend.backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
                api_key=api_key,
                plan_code=plan_code,
                is_admin=is_admin,
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


@router.get("/models", response_model=ModelList)
async def list_models(
    session: AsyncSession = Depends(get_db_session),
    client: Client = Depends(require_client),
):
    """
    Lista os modelos disponíveis para o cliente com base no seu plano.
    Compatível com o formato da API OpenAI.
    """
    allowed = get_effective_allowed_models(client)
    models = await list_active_registry_models(session)
    
    # Adiciona o modelo de embedding mock/default se habilitado
    if settings.embeddings_enabled:
        from app.schemas.inference import ModelCard
        filtered = [
            serialize_model_card(item)
            for item in models
            if not allowed or item.model_id in allowed or (item.model_alias or "") in allowed
        ]
        # Always include the default embedding model for now if enabled
        if not any(m["id"] == settings.default_embedding_model for m in filtered):
            filtered.append({
                "id": settings.default_embedding_model,
                "object": "model",
                "owned_by": "local-mock" if settings.embeddings_backend == "mock" else "local",
                "metadata": {"type": "embedding", "dimensions": settings.embedding_dimensions}
            })
        return ModelList(data=filtered)

    filtered = [
        serialize_model_card(item)
        for item in models
        if not allowed or item.model_id in allowed or (item.model_alias or "") in allowed
    ]
    return ModelList(data=filtered)


@router.post("/embeddings", response_model=EmbeddingsResponse)
async def embeddings(
    payload: EmbeddingsRequest,
    request: Request,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    """
    Gera embeddings para o input fornecido.
    Compatível com o formato da API OpenAI.
    """
    if not settings.embeddings_enabled:
        raise HTTPException(status_code=404, detail="embeddings endpoint is disabled")

    effective_plan = resolve_effective_plan(client)
    if not effective_plan.embeddings_enabled:
        raise HTTPException(status_code=403, detail="embeddings are not enabled for your plan")

    inputs = payload.input
    if isinstance(inputs, list):
        if len(inputs) > effective_plan.embeddings_max_inputs_per_request:
            raise HTTPException(
                status_code=400, 
                detail=f"too many inputs: max {effective_plan.embeddings_max_inputs_per_request} allowed per request"
            )
    else:
        inputs = [inputs]

    # Estima tokens (4 chars por token)
    total_tokens = sum(max(1, len(text) // 4) for text in inputs)
    
    try:
        source_ip = getattr(request.state, "source_ip", "unknown")
        await enforce_ip_rate_limit(redis, source_ip)
        await enforce_rate_limit(redis, client.id, effective_plan.rate_limit_per_minute)
        await ensure_embeddings_quota(
            session, 
            client.id, 
            effective_plan.embeddings_requests_per_month, 
            effective_plan.embeddings_tokens_per_month, 
            total_tokens
        )
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    started = perf_counter()
    backend_name = "mock"
    
    if settings.embeddings_backend == "mock":
        response_data = process_mock_embeddings(
            inputs, 
            model=payload.model, 
            dimensions=settings.embedding_dimensions
        )
        latency_ms = int((perf_counter() - started) * 1000)
    else:
        # Futuro: Suporte a backend real (local via inference proxy)
        # result = await proxy.embeddings(...)
        # Para v1.6.0 alvo inicial é mock
        response_data = process_mock_embeddings(
            inputs, 
            model=payload.model, 
            dimensions=settings.embedding_dimensions
        )
        latency_ms = int((perf_counter() - started) * 1000)
        backend_name = settings.embeddings_backend

    await record_embedding_usage(session, client.id, len(inputs), total_tokens)
    
    # Log request (reusando log_request se possível, ou criando um específico)
    # log_request espera prompt_tokens e completion_tokens
    await log_request(
        session,
        client_id=client.id,
        model=payload.model,
        endpoint="/v1/embeddings",
        prompt_tokens=total_tokens,
        completion_tokens=0,
        latency_ms=latency_ms,
        status_code=200,
        is_stream=False,
        estimated_cost_usd=0.0, # Embeddings por enquanto free em termos de overage
        backend_name=f"embeddings:{backend_name}",
        attempts=1,
        fallback_used=False,
        cache_hit=False,
        backend_errors=[],
        error_message=None,
        request_summary=f"Embeddings for {len(inputs)} inputs",
        plan_code=effective_plan.code,
    )
    await session.commit()
    
    return response_data


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
    context_manager: ContextManager = Depends(get_context_manager),
):
    """
    Executa uma inferência de chat compatível com OpenAI.
    Suporta streaming SSE se `stream: true` for enviado.
    """
    return await _process_chat_completion(
        payload=payload,
        request=request,
        client=client,
        session=session,
        redis=redis,
        proxy=proxy,
        context_manager=context_manager,
        endpoint="/v1/chat/completions",
    )


@router.post("/responses", response_model=ResponsesResponse)
async def responses(
    payload: ResponsesRequest,
    request: Request,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
    proxy: InferenceProxy = Depends(get_inference_proxy),
    context_manager: ContextManager = Depends(get_context_manager),
):
    """
    Endpoint de compatibilidade simplificado /v1/responses.
    Mapeia para o pipeline de chat completions.
    """
    if payload.tools or payload.tool_choice is not None:
        return _unsupported_feature_response(
            code="responses_tools_unsupported",
            message="Tools are not supported in /v1/responses yet.",
        )
    
    if payload.stream:
        return _unsupported_feature_response(
            code="responses_streaming",
            message="Streaming is not supported in /v1/responses yet.",
        )

    effective_plan = resolve_effective_plan(client)
    if not effective_plan.responses_enabled:
        raise HTTPException(status_code=403, detail="responses feature is not enabled for your plan")

    messages = _responses_input_to_messages(payload)
    
    chat_payload = ChatCompletionRequest(
        model=payload.model,
        messages=messages,
        temperature=payload.temperature,
        top_p=payload.top_p,
        max_tokens=payload.max_output_tokens,
        stream=False,
    )

    response = await _process_chat_completion(
        payload=chat_payload,
        request=request,
        client=client,
        session=session,
        redis=redis,
        proxy=proxy,
        context_manager=context_manager,
        endpoint="/v1/responses",
    )

    if isinstance(response, JSONResponse):
        data = json.loads(response.body.decode("utf-8"))
        choices = data.get("choices") or []
        output = []
        output_text = ""
        if choices:
            choice = choices[0]
            msg = choice.get("message", {})
            output_text = msg.get("content", "") or ""
            output.append(ResponseOutput(
                type="message",
                message=ResponseOutputMessage(
                    role=msg.get("role", "assistant"),
                    content=[ResponseOutputText(text=output_text)],
                ),
            ))

        responses_payload = ResponsesResponse(
            id=data.get("id"),
            object="response",
            created_at=data.get("created"),
            status="completed",
            model=data.get("model"),
            output=output,
            output_text=output_text,
            usage=UsageInfo(**(data.get("usage") or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})),
            metadata=payload.metadata or {}
        )
        return JSONResponse(
            status_code=response.status_code,
            content=responses_payload.model_dump(),
            headers=_passthrough_response_headers(dict(response.headers)),
        )
    
    return response


async def _process_chat_completion(
    payload: ChatCompletionRequest,
    request: Request,
    client: Client,
    session: AsyncSession,
    redis,
    proxy: InferenceProxy,
    context_manager: ContextManager,
    endpoint: str = "/v1/chat/completions",
):
    selected_model, _ = await resolve_requested_model(
        session,
        client=client,
        requested_model=payload.model,
    )
    
    logger.debug(
        "chat completions request resolved",
        extra={
            "extra_data": {
                "requested_model": payload.model,
                "resolved_model_id": selected_model.model_id,
                "resolved_model_alias": selected_model.model_alias,
                "prompt_template": selected_model.prompt_template,
                "endpoint": endpoint,
            }
        },
    )
    
    # Normalize messages (handling content parts)
    messages = normalize_messages([item.model_dump() for item in payload.messages])
    
    # Apply Client System Prompt if available
    if client.system_prompt:
        # Check if there is already a system message
        system_msg_idx = next((i for i, m in enumerate(messages) if m["role"] == "system"), None)
        if system_msg_idx is not None:
            messages[system_msg_idx]["content"] = f"{client.system_prompt}\n\n{messages[system_msg_idx]['content']}"
        else:
            messages.insert(0, {"role": "system", "content": client.system_prompt})

    # Manage Context (limiting system, history, tokens)
    messages, max_tokens_capped, context_metrics = context_manager.manage(
        messages=messages,
        requested_max_tokens=payload.max_tokens,
        model_id=selected_model.model_id,
    )

    prompt_tokens = context_metrics["final_tokens_estimate"]
    if prompt_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit after management")
    
    # Still call validate_params for plan and basic params, but use capped max_tokens if needed
    _, temperature, top_p, effective_plan = validate_params(client, payload)
    max_tokens = max_tokens_capped

    # Improve behavior for local small models
    if payload.temperature is None and selected_model.provider in {"llama.cpp", "ollama"}:
        temperature = 0.4
    if payload.top_p is None and selected_model.provider in {"llama.cpp", "ollama"}:
        top_p = 0.9

    logger.info(
        "Inference context optimized",
        extra={
            "extra_data": context_metrics
        }
    )

    incoming_tokens = prompt_tokens + max_tokens
    try:
        source_ip = getattr(request.state, "source_ip", "unknown")
        await enforce_ip_rate_limit(redis, source_ip)
        await enforce_rate_limit(redis, client.id, effective_plan.rate_limit_per_minute)
        await ensure_quota(
            session, 
            client.id, 
            effective_plan.daily_token_quota, 
            effective_plan.weekly_token_quota, 
            effective_plan.monthly_token_quota, 
            incoming_tokens,
            requests_per_day_limit=effective_plan.requests_per_day
        )
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
    if getattr(payload, "safety_profile", None) == "strict":
        body["temperature"] = min(temperature, 0.5)
        body["top_p"] = min(top_p, 0.8)
    elif getattr(payload, "safety_profile", None) == "relaxed":
        body["temperature"] = max(temperature, 1.0)
        body["top_p"] = max(top_p, 0.9)

    cache_key, cache_fingerprint = build_chat_cache_key(
        model=selected_model.model_id,
        messages=messages,
        temperature=body["temperature"],
        top_p=body["top_p"],
        max_tokens=max_tokens,
        include_reasoning=getattr(payload, "include_reasoning", False),
    )
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
        include_reasoning=getattr(payload, "include_reasoning", False),
    )
    await maybe_record_repeated_large_prompt(
        session,
        redis,
        client=client,
        prompt_tokens=prompt_tokens,
        prompt_key=prompt_fingerprint(json.dumps(messages, sort_keys=True, ensure_ascii=True)),
        endpoint=endpoint,
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
    started = perf_counter()
    try:
        if not payload.stream:
            cached = await lookup_exact_cache(
                session,
                endpoint=endpoint,
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
                    endpoint=endpoint,
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
                    safety_profile=getattr(payload, "safety_profile", "default"),
                )
                await session.commit()
                cached_response = JSONResponse(status_code=200, content=cached.payload)
                return _apply_compat_headers(
                    cached_response,
                    _response_compat_headers(
                        requested_model=payload.model,
                        resolved_model=selected_model.model_id,
                        backend_name="cache:exact",
                        fallback_used=False,
                    ),
                )

        result = await _chat_with_fallback(
            proxy,
            selected_model,
            body,
            payload.stream,
            getattr(payload, "include_reasoning", False),
            client=client,
        )
        latency_ms = int((perf_counter() - started) * 1000)
        compat_headers = _response_compat_headers(
            requested_model=payload.model,
            resolved_model=selected_model.model_id,
            backend_name=result.backend_name,
            fallback_used=result.fallback_used,
        )
        if payload.stream:
            estimated_stream_tokens = max_tokens
            await record_usage(session, client.id, prompt_tokens, estimated_stream_tokens)
            await log_request(
                session,
                client_id=client.id,
                model=selected_model.model_id,
                endpoint=endpoint,
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
                plan_code=effective_plan.code,
                safety_profile=getattr(payload, "safety_profile", "default"),
                )
            await session.commit()
            return _apply_compat_headers(result.response, compat_headers)
        response_payload = json.loads(result.response.body.decode("utf-8"))
        completion_tokens = estimate_tokens_from_text(result.response.body.decode("utf-8"))
        await store_exact_cache(
            session,
            endpoint=endpoint,
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
            endpoint=endpoint,
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
            safety_profile=getattr(payload, "safety_profile", "default"),
        )
        await session.commit()
        return _apply_compat_headers(result.response, compat_headers)
    except HTTPException as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        backend_errors = _backend_errors_for_log(exc.detail)
        await log_request(
            session,
            client_id=client.id,
            model=selected_model.model_id,
            endpoint=endpoint,
            prompt_tokens=prompt_tokens if 'prompt_tokens' in locals() else 0,
            completion_tokens=0,
            latency_ms=latency_ms,
            status_code=exc.status_code,
            is_stream=payload.stream,
            estimated_cost_usd=estimated_request_cost if 'estimated_request_cost' in locals() else 0,
            backend_name=backend_errors[-1]["backend_name"] if backend_errors else None,
            attempts=max(len(backend_errors), 1),
            fallback_used=len(backend_errors) > 1,
            cache_hit=False,
            backend_errors=backend_errors,
            error_message=_error_message_for_log(exc.detail),
            request_summary=request_summary if 'request_summary' in locals() else "",
            plan_code=effective_plan.code if 'effective_plan' in locals() else "free",
            safety_profile=getattr(payload, "safety_profile", "default"),
        )
        await maybe_record_request_error_burst(
            session,
            redis,
            client_id=client.id,
            endpoint=endpoint,
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
    
    logger.debug(
        "completions request resolved",
        extra={
            "extra_data": {
                "requested_model": payload.model,
                "resolved_model_id": selected_model.model_id,
                "resolved_model_alias": selected_model.model_alias,
                "prompt_template": selected_model.prompt_template,
            }
        },
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
        await ensure_quota(
            session, 
            client.id, 
            effective_plan.daily_token_quota, 
            effective_plan.weekly_token_quota, 
            effective_plan.monthly_token_quota, 
            incoming_tokens,
            requests_per_day_limit=effective_plan.requests_per_day
        )
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
        weekly_limit=effective_plan.weekly_token_quota,
        monthly_limit=effective_plan.monthly_token_quota,
        incoming_tokens=incoming_tokens,
        daily_used_before=daily_used_before,
        weekly_used_before=weekly_used_before,
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
                plan_code=effective_plan.code,
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
                    plan_code=effective_plan.code,
                    safety_profile=payload.safety_profile,
                )
                await session.commit()
                return JSONResponse(status_code=200, content=cached.payload)

        result = await _completion_with_fallback(
            proxy,
            selected_model,
            body,
            payload.stream,
            client=client,
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
                plan_code=effective_plan.code,
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
            plan_code=effective_plan.code,
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
            plan_code=effective_plan.code,
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
