# Owner: platform-ops
import json
import logging
from time import perf_counter

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.core.request_context import get_correlation_id
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
from app.services.commercial_guardrails import (
    build_openai_guardrail_error_payload,
    build_runtime_enforcement_context,
    record_enforcement_outcome,
    record_report_only_events,
)
from app.services.routing import commercial_analytics
from app.services.generation_jobs import cancel_job, create_chat_generation_job, enqueue_generation_job, get_job_for_client, serialize_job
from app.services.context_manager import ContextManager, get_context_manager
from app.services.embeddings_mock import process_mock_embeddings
from app.services.inference_proxy import InferenceProxy
from app.services.provider_classification import is_cloud_provider
from app.services.model_policy import (
    get_effective_allowed_models,
    list_active_registry_models,
    plan_routing_order,
    resolve_effective_backend_url,
    resolve_requested_model,
    serialize_model_card,
)
from app.services.routing.commercial_global_traffic_shifter import CommercialGlobalTrafficShifter
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
from app.services.tokenizer_service import get_tokenizer_service, TokenizerService
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text
from app.utils.tool_calling import (
    chat_response_has_tool_calls,
    enforce_tool_argument_limits,
    extract_tool_calls_from_chat_payload,
    filter_unsupported_tooling_parameters,
    model_supports_native_tools,
    sanitize_inert_tooling_fields,
    sanitize_tool_calls,
    validate_tooling_request,
)
from app.utils.validation import normalize_messages, validate_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["client"])

settings = get_settings()


class CommercialGuardrailBlockedError(Exception):
    pass


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


def _capability_not_supported_response(*, provider: str, endpoint: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": f"Tool calling is not supported for provider '{provider}' on {endpoint}.",
                "type": "capability_not_supported",
                "code": "capability_not_supported",
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


def _response_tool_outputs(choice: dict) -> list[ResponseOutput]:
    outputs: list[ResponseOutput] = []
    message = choice.get("message") or {}
    content = message.get("content") or ""
    if content:
        outputs.append(
            ResponseOutput(
                type="message",
                message=ResponseOutputMessage(
                    role=message.get("role", "assistant"),
                    content=[ResponseOutputText(text=content)],
                ),
            )
        )
    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function") or {}
        outputs.append(
            ResponseOutput(
                type="function_call",
                name=function.get("name"),
                arguments=function.get("arguments"),
                call_id=tool_call.get("id"),
            )
        )
    return outputs


def _is_retryable_backend_error(exc: HTTPException) -> bool:
    return exc.status_code >= 500 or exc.status_code in {503, 504}


def _should_fallback_to_default_model(exc: HTTPException) -> bool:
    if exc.status_code != 404:
        return False
    detail = exc.detail
    if not isinstance(detail, dict):
        return False
    message = str(detail.get("message", "")).lower()
    if "data plane rejected request" not in message:
        return False
    backend_response = detail.get("backend_response")
    if not isinstance(backend_response, dict):
        return False
    error_payload = backend_response.get("error")
    if not isinstance(error_payload, dict):
        return False
    backend_message = str(error_payload.get("message", "")).lower()
    return "no endpoints found for" in backend_message


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
    cloud_blocked_by_guardrail: bool = False,
    commercial_guardrail_context: dict | None = None,
    session: AsyncSession | None = None,
    allow_default_model_fallback: bool = True,
):
    from app.services.routing.commercial_qos import CommercialQoSService
    qos_tier = None
    if session:
        qos_tier = await CommercialQoSService.resolve_qos_tier(
            session, 
            client.id if client else None, 
            client.billing_plan.code if client and client.billing_plan else None
        )

    routes = plan_routing_order(
        selected_model,
        client=client,
        cloud_blocked_by_guardrail=cloud_blocked_by_guardrail,
        commercial_guardrail_context=commercial_guardrail_context,
        qos_tier=qos_tier,
    )
    
    # Record commercial routing analytics event (best-effort)
    if session:
        from app.services.billing.pricing_engine import estimate_provider_cost, calculate_customer_price
        from app.schemas.routing import TaskType
        
        selected_pid = routes[0].inference_backend.provider if routes else None
        est_cost = 0.0
        est_rev = 0.0
        if selected_pid:
            est_cost_res = estimate_provider_cost(selected_pid, 100, 500)
            est_rev_res = calculate_customer_price(client.billing_plan.code if client and client.billing_plan else "free", 100, 500)
            est_cost = est_cost_res.cost_brl
            est_rev = est_rev_res.price_brl
        
        await commercial_analytics.record_routing_event(
            session,
            client_id=client.id if client else None,
            correlation_id=get_correlation_id(),
            endpoint="/v1/chat/completions", # Simplified
            model_requested=selected_model.model_id,
            task_type=TaskType.general,
            policy="commercial_profit",
            selected_provider=selected_pid,
            selected_model=routes[0].inference_backend.name if routes else None,
            selected_is_cloud=is_cloud_provider(selected_pid) if selected_pid else False,
            blocked=not routes and bool(commercial_guardrail_context and commercial_guardrail_context.get("blocked_without_fallback")),
            block_reason="guardrail_block" if not routes and commercial_guardrail_context and commercial_guardrail_context.get("blocked_without_fallback") else None,
            estimated_cost_brl=est_cost,
            estimated_revenue_brl=est_rev,
            estimated_margin_brl=est_rev - est_cost,
            estimated_margin_percent=((est_rev - est_cost) / est_rev * 100) if est_rev > 0 else 0,
            ranked_routes=routes,
            guardrail_decisions=commercial_guardrail_context.get("blocked_candidates", []) if commercial_guardrail_context else [],
            qos_tier=qos_tier.name if qos_tier else None,
            sla_pass=len(routes) > 0,
            qos_priority=qos_tier.priority if qos_tier else None,
        )

    record_report_only_events(commercial_guardrail_context)
    if not routes:
        if commercial_guardrail_context and commercial_guardrail_context.get("blocked_without_fallback"):
            record_enforcement_outcome(commercial_guardrail_context, blocked_without_fallback=True)
            raise CommercialGuardrailBlockedError()
        raise HTTPException(status_code=503, detail="model backend is not active")
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
            backend_url = backend.backend_url
            if session:
                backend_url = await resolve_effective_backend_url(session, route)

            result = await proxy.chat(
                body,
                stream,
                include_reasoning,
                backend=backend.provider,
                backend_url=backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
                prompt_template=selected_model.prompt_template,
                api_key=api_key,
                plan_code=plan_code,
                is_admin=is_admin,
            )
            result.attempts = attempt
            result.fallback_used = attempt > 1 or bool(commercial_guardrail_context and commercial_guardrail_context.get("guardrail_fallback_active"))
            result.backend_errors = backend_errors
            record_enforcement_outcome(commercial_guardrail_context, selected_provider=backend.provider)
            return result
        except HTTPException as exc:
            last_exc = exc
            backend_errors.append(_serialize_backend_error(route, exc))
            if not _is_retryable_backend_error(exc) or attempt == len(routes):
                break

    if (
        allow_default_model_fallback
        and last_exc is not None
        and session is not None
        and client is not None
        and _should_fallback_to_default_model(last_exc)
    ):
        default_model, _ = await resolve_requested_model(
            session,
            client=client,
            requested_model="default",
        )
        if default_model.id != selected_model.id:
            fallback_body = dict(body)
            fallback_body["model"] = default_model.model_id
            result = await _chat_with_fallback(
                proxy,
                default_model,
                fallback_body,
                stream,
                include_reasoning,
                client=client,
                cloud_blocked_by_guardrail=cloud_blocked_by_guardrail,
                commercial_guardrail_context=commercial_guardrail_context,
                session=session,
                allow_default_model_fallback=False,
            )
            result.fallback_used = True
            result.backend_errors = backend_errors + result.backend_errors
            return result

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
    cloud_blocked_by_guardrail: bool = False,
    commercial_guardrail_context: dict | None = None,
    session: AsyncSession | None = None,
):
    from app.services.routing.commercial_qos import CommercialQoSService
    qos_tier = None
    if session:
        qos_tier = await CommercialQoSService.resolve_qos_tier(
            session, 
            client.id if client else None, 
            client.billing_plan.code if client and client.billing_plan else None
        )

    routes = plan_routing_order(
        selected_model,
        client=client,
        cloud_blocked_by_guardrail=cloud_blocked_by_guardrail,
        commercial_guardrail_context=commercial_guardrail_context,
        qos_tier=qos_tier,
    )
    
    # Record commercial routing analytics event (best-effort)
    if session:
        from app.services.billing.pricing_engine import estimate_provider_cost, calculate_customer_price
        from app.schemas.routing import TaskType
        
        selected_pid = routes[0].inference_backend.provider if routes else None
        est_cost = 0.0
        est_rev = 0.0
        if selected_pid:
            est_cost_res = estimate_provider_cost(selected_pid, 100, 500)
            est_rev_res = calculate_customer_price(client.billing_plan.code if client and client.billing_plan else "free", 100, 500)
            est_cost = est_cost_res.cost_brl
            est_rev = est_rev_res.price_brl
        
        await commercial_analytics.record_routing_event(
            session,
            client_id=client.id if client else None,
            correlation_id=get_correlation_id(),
            endpoint="/v1/chat/completions", # Simplified
            model_requested=selected_model.model_id,
            task_type=TaskType.general,
            policy="commercial_profit",
            selected_provider=selected_pid,
            selected_model=routes[0].inference_backend.name if routes else None,
            selected_is_cloud=is_cloud_provider(selected_pid) if selected_pid else False,
            blocked=not routes and bool(commercial_guardrail_context and commercial_guardrail_context.get("blocked_without_fallback")),
            block_reason="guardrail_block" if not routes and commercial_guardrail_context and commercial_guardrail_context.get("blocked_without_fallback") else None,
            estimated_cost_brl=est_cost,
            estimated_revenue_brl=est_rev,
            estimated_margin_brl=est_rev - est_cost,
            estimated_margin_percent=((est_rev - est_cost) / est_rev * 100) if est_rev > 0 else 0,
            ranked_routes=routes,
            guardrail_decisions=commercial_guardrail_context.get("blocked_candidates", []) if commercial_guardrail_context else [],
            qos_tier=qos_tier.name if qos_tier else None,
            sla_pass=len(routes) > 0,
            qos_priority=qos_tier.priority if qos_tier else None,
        )

    record_report_only_events(commercial_guardrail_context)
    if not routes:
        if commercial_guardrail_context and commercial_guardrail_context.get("blocked_without_fallback"):
            record_enforcement_outcome(commercial_guardrail_context, blocked_without_fallback=True)
            raise CommercialGuardrailBlockedError()
        raise HTTPException(status_code=503, detail="model backend is not active")
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
            backend_url = backend.backend_url
            if session:
                backend_url = await resolve_effective_backend_url(session, route)

            result = await proxy.complete(
                body,
                stream,
                backend=backend.provider,
                backend_url=backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
                api_key=api_key,
                plan_code=plan_code,
                is_admin=is_admin,
            )
            result.attempts = attempt
            result.fallback_used = attempt > 1 or bool(commercial_guardrail_context and commercial_guardrail_context.get("guardrail_fallback_active"))
            result.backend_errors = backend_errors
            record_enforcement_outcome(commercial_guardrail_context, selected_provider=backend.provider)
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
                "capabilities": {
                    "chat": False,
                    "streaming": False,
                    "embeddings": True,
                    "responses": False,
                    "tools": False,
                },
                "enabled": True,
                "backend_status": "healthy" if settings.embeddings_backend == "mock" else "unknown",
                "production_ready": settings.app_env == "production",
                "local_ready": True,
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
    tokenizer: TokenizerService = Depends(get_tokenizer_service),
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

    # Contagem real de tokens
    token_res = await tokenizer.count_embedding_tokens(inputs, model=payload.model)
    total_tokens = token_res.input_tokens
    
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

    await record_embedding_usage(
        session, 
        client.id, 
        len(inputs), 
        total_tokens,
        token_count_method=token_res.method,
        tokens_estimated=token_res.is_estimated
    )
    
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
    tokenizer: TokenizerService = Depends(get_tokenizer_service),
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
        tokenizer=tokenizer,
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
    tokenizer: TokenizerService = Depends(get_tokenizer_service),
):
    """
    Endpoint de compatibilidade simplificado /v1/responses.
    Mapeia para o pipeline de chat completions.
    """
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
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        parallel_tool_calls=payload.parallel_tool_calls,
        response_format=payload.response_format,
    )

    response = await _process_chat_completion(
        payload=chat_payload,
        request=request,
        client=client,
        session=session,
        redis=redis,
        proxy=proxy,
        context_manager=context_manager,
        tokenizer=tokenizer,
        endpoint="/v1/responses",
    )

    if isinstance(response, JSONResponse):
        if response.status_code >= 400:
            return response
        data = json.loads(response.body.decode("utf-8"))
        if "choices" not in data:
            return response
        choices = data.get("choices") or []
        output = []
        output_text = ""
        if choices:
            choice = choices[0]
            msg = choice.get("message", {})
            output_text = msg.get("content", "") or ""
            output.extend(_response_tool_outputs(choice))

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
            content=responses_payload.model_dump(exclude_none=True),
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
    tokenizer: TokenizerService,
    endpoint: str = "/v1/chat/completions",
):
    cloud_blocked_by_guardrail = False
    payload.tools, payload.tool_choice, payload.parallel_tool_calls = sanitize_inert_tooling_fields(
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        parallel_tool_calls=payload.parallel_tool_calls,
    )

    validate_tooling_request(
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        parallel_tool_calls=payload.parallel_tool_calls,
        response_format=payload.response_format,
    )
    selected_model, _ = await resolve_requested_model(
        session,
        client=client,
        requested_model=payload.model,
    )
    
    # Phase 18: Cross-Cluster Forwarding
    if endpoint in ["/v1/chat/completions", "/v1/completions"]:
        request_payload = {
            "tenant_id": getattr(client, "tenant_id", None),
            "provider": selected_model.provider if selected_model else None,
            "model": payload.model,
            "correlation_id": get_correlation_id(),
            "client_id": str(client.id)
        }
        shifter = CommercialGlobalTrafficShifter(session)
        decision = await shifter.decide_cluster_for_request(request_payload)

        if decision.decision == "shift_to_target" and decision.target_cluster_id:
            res = await session.execute(select(CommercialClusterRegistry).where(CommercialClusterRegistry.cluster_id == decision.target_cluster_id))
            target_cluster = res.scalar_one_or_none()
            if target_cluster:
                forwarder = CommercialCrossClusterForwarder(session)
                if forwarder.should_forward_request(target_cluster):
                    body_bytes = await request.body()
                    if payload.stream:
                        response = await forwarder.stream_sse_forward(request, target_cluster, body_bytes)
                    else:
                        response = await forwarder.forward_request(request, target_cluster, body_bytes)
                    if response is not None:
                        return response
                    # Fallback local if response is None

    # If cloud is blocked by guardrail and the selected model is ONLY cloud, we should ideally fallback to a local default
    # But resolve_requested_model doesn't know about guardrails yet.
    # For now, plan_routing_order will return an empty list if ONLY cloud routes exist and are blocked.
    
    if payload.tools and not model_supports_native_tools(selected_model.provider, selected_model.metadata_json):
        return _capability_not_supported_response(provider=selected_model.provider, endpoint=endpoint)
    
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
    messages = normalize_messages([item.model_dump(exclude_none=True) for item in payload.messages])
    
    # Apply Client System Prompt if available
    if client.system_prompt:
        # Check if there is already a system message
        system_msg_idx = next((i for i, m in enumerate(messages) if m["role"] == "system"), None)
        if system_msg_idx is not None:
            messages[system_msg_idx]["content"] = f"{client.system_prompt}\n\n{messages[system_msg_idx]['content']}"
        else:
            messages.insert(0, {"role": "system", "content": client.system_prompt})

    # Manage Context (limiting system, history, tokens)
    messages, max_tokens_capped, context_metrics = await context_manager.manage(
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

    body = payload.model_dump(exclude={"include_reasoning", "safety_profile"}, exclude_none=True)
    body = filter_unsupported_tooling_parameters(
        selected_model.provider,
        body,
        selected_model.metadata_json
    )
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
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        parallel_tool_calls=payload.parallel_tool_calls,
        response_format=payload.response_format,
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
        tool_count=len(payload.tools or []),
        tool_choice=payload.tool_choice if isinstance(payload.tool_choice, str) else ((payload.tool_choice or {}).get("function") or {}).get("name"),
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
    commercial_guardrail_context = await build_runtime_enforcement_context(
        session,
        client_id=str(client.id),
        plan_code=effective_plan.code,
        prompt_tokens=prompt_tokens,
        completion_tokens=max_tokens,
    )
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
                if not proxy._chat_response_has_visible_output(
                    cached.payload,
                    include_reasoning=getattr(payload, "include_reasoning", False),
                ):
                    cached.hit = False
                    cached.payload = None
                else:
                    latency_ms = int((perf_counter() - started) * 1000)
                    cached_tool_calls = sanitize_tool_calls(extract_tool_calls_from_chat_payload(cached.payload))
                    await record_usage(
                        session, 
                        client.id, 
                        prompt_tokens, 
                        cached.completion_tokens,
                        token_count_method=token_count_method,
                        tokens_estimated=tokens_estimated
                    )
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
                        tool_call_count=len(cached_tool_calls),
                        tool_calls=cached_tool_calls,
                        backend_errors=[],
                        error_message=None,
                        request_summary=request_summary,
                        plan_code=effective_plan.code,
                        safety_profile=getattr(payload, "safety_profile", "default"),
                        request_payload=body,
                        response_payload=cached.payload,
                        reproducibility_context={
                            "model_alias": selected_model.model_alias,
                            "provider": selected_model.provider,
                            "prompt_template": selected_model.prompt_template,
                            "runtime_engine": selected_model.provider,
                            "model_metadata_json": selected_model.metadata_json,
                            "metadata_json": {"cache_hit": True},
                        },
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
            cloud_blocked_by_guardrail=cloud_blocked_by_guardrail,
            commercial_guardrail_context=commercial_guardrail_context,
            session=session,
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
            await record_usage(
                session, 
                client.id, 
                prompt_tokens, 
                estimated_stream_tokens,
                token_count_method=token_count_method,
                tokens_estimated=tokens_estimated
            )
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
                tool_call_count=0,
                tool_calls=None,
                backend_errors=result.backend_errors,
                error_message=None,
                request_summary=request_summary,
                plan_code=effective_plan.code,
                safety_profile=getattr(payload, "safety_profile", "default"),
                request_payload=body,
                response_payload=None,
                reproducibility_context={
                    "model_alias": selected_model.model_alias,
                    "provider": selected_model.provider,
                    "prompt_template": selected_model.prompt_template,
                    "runtime_engine": selected_model.provider,
                    "model_metadata_json": selected_model.metadata_json,
                    "metadata_json": {"audit_event": "replay_disabled_stream", "stream": True},
                },
                )
            
            # Update commercial routing analytics with actual results (stream)
            try:
                from app.services.billing.pricing_engine import estimate_provider_cost, calculate_customer_price
                act_cost_res = estimate_provider_cost(result.backend_name, prompt_tokens, estimated_stream_tokens)
                act_rev_res = calculate_customer_price(effective_plan.code, prompt_tokens, estimated_stream_tokens)
                
                await commercial_analytics.update_actual_financials(
                    session,
                    correlation_id=get_correlation_id(),
                    actual_cost_brl=act_cost_res.cost_brl,
                    actual_revenue_brl=act_rev_res.price_brl,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                logger.warning(f"Failed to update commercial analytics: {e}")

            await session.commit()
            return _apply_compat_headers(result.response, compat_headers)
        response_payload = json.loads(result.response.body.decode("utf-8"))
        proxy._validate_chat_response_payload(
            response_payload,
            include_reasoning=getattr(payload, "include_reasoning", False),
            backend_name=result.backend_name,
        )
        tool_calls = extract_tool_calls_from_chat_payload(response_payload)
        sanitized_tool_calls = enforce_tool_argument_limits(tool_calls)
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
        await record_usage(
            session, 
            client.id, 
            prompt_tokens, 
            completion_tokens,
            token_count_method=token_count_method,
            tokens_estimated=tokens_estimated
        )
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
            tool_call_count=len(tool_calls),
            tool_calls=sanitized_tool_calls,
            backend_errors=result.backend_errors,
            error_message=None,
            request_summary=request_summary,
            plan_code=effective_plan.code,
            safety_profile=getattr(payload, "safety_profile", "default"),
            request_payload=body,
            response_payload=response_payload,
            reproducibility_context={
                "model_alias": selected_model.model_alias,
                "provider": selected_model.provider,
                "prompt_template": selected_model.prompt_template,
                "runtime_engine": selected_model.provider,
                "model_metadata_json": selected_model.metadata_json,
                "metadata_json": {"cache_hit": False},
            },
        )
        
        # Update commercial routing analytics with actual results
        try:
            from app.services.billing.pricing_engine import estimate_provider_cost, calculate_customer_price
            act_cost_res = estimate_provider_cost(result.backend_name, prompt_tokens, completion_tokens)
            act_rev_res = calculate_customer_price(effective_plan.code, prompt_tokens, completion_tokens)
            
            await commercial_analytics.update_actual_financials(
                session,
                correlation_id=get_correlation_id(),
                actual_cost_brl=act_cost_res.cost_brl,
                actual_revenue_brl=act_rev_res.price_brl,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to update commercial analytics: {e}")

        await session.commit()
        return _apply_compat_headers(result.response, compat_headers)
    except CommercialGuardrailBlockedError:
        latency_ms = int((perf_counter() - started) * 1000)
        payload_body = build_openai_guardrail_error_payload()
        await log_request(
            session,
            client_id=client.id,
            model=selected_model.model_id,
            endpoint=endpoint,
            prompt_tokens=prompt_tokens if 'prompt_tokens' in locals() else 0,
            completion_tokens=0,
            latency_ms=latency_ms,
            status_code=503,
            is_stream=payload.stream,
            estimated_cost_usd=estimated_request_cost if 'estimated_request_cost' in locals() else 0,
            backend_name=None,
            attempts=0,
            fallback_used=False,
            cache_hit=False,
            tool_call_count=0,
            tool_calls=None,
            backend_errors=[],
            error_message=payload_body["error"]["message"],
            request_summary=request_summary if 'request_summary' in locals() else "",
            plan_code=effective_plan.code if 'effective_plan' in locals() else "free",
            safety_profile=getattr(payload, "safety_profile", "default"),
            request_payload=body if 'body' in locals() else None,
            response_payload=None,
            reproducibility_context={
                "model_alias": selected_model.model_alias if 'selected_model' in locals() else None,
                "provider": selected_model.provider if 'selected_model' in locals() else None,
                "prompt_template": selected_model.prompt_template if 'selected_model' in locals() else None,
                "runtime_engine": selected_model.provider if 'selected_model' in locals() else None,
                "model_metadata_json": selected_model.metadata_json if 'selected_model' in locals() else None,
                "metadata_json": {"audit_event": "replay_failed_guardrail"},
            },
        )
        await session.commit()
        return JSONResponse(status_code=503, content=payload_body)
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
            tool_call_count=0,
            tool_calls=None,
            backend_errors=backend_errors,
            error_message=_error_message_for_log(exc.detail),
            request_summary=request_summary if 'request_summary' in locals() else "",
            plan_code=effective_plan.code if 'effective_plan' in locals() else "free",
            safety_profile=getattr(payload, "safety_profile", "default"),
            request_payload=body if 'body' in locals() else None,
            response_payload=None,
            reproducibility_context={
                "model_alias": selected_model.model_alias if 'selected_model' in locals() else None,
                "provider": selected_model.provider if 'selected_model' in locals() else None,
                "prompt_template": selected_model.prompt_template if 'selected_model' in locals() else None,
                "runtime_engine": selected_model.provider if 'selected_model' in locals() else None,
                "model_metadata_json": selected_model.metadata_json if 'selected_model' in locals() else None,
                "metadata_json": {"audit_event": "replay_failed_http_exception"},
            },
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
    await enqueue_generation_job(
        redis, 
        job.id, 
        priority=job.priority, 
        effective_priority=float(job.effective_priority or 0)
    )
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
    tokenizer: TokenizerService = Depends(get_tokenizer_service),
):
    cloud_blocked_by_guardrail = False

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
    
    token_res_early = await tokenizer.count_text_tokens(payload.prompt, model=selected_model.model_id)
    if token_res_early.input_tokens > client.max_context_tokens:
        raise HTTPException(status_code=413, detail="prompt exceeds client context limit")
    
    # Using validate_params instead of _validated_params
    max_tokens, temperature, top_p, effective_plan = validate_params(client, payload)
    
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

    token_res = await tokenizer.count_text_tokens(prompt, model=selected_model.model_id)
    prompt_tokens = token_res.input_tokens
    token_count_method = token_res.method
    tokens_estimated = token_res.is_estimated
    
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
    commercial_guardrail_context = await build_runtime_enforcement_context(
        session,
        client_id=str(client.id),
        plan_code=effective_plan.code,
        prompt_tokens=prompt_tokens,
        completion_tokens=max_tokens,
    )
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
                await record_usage(
                    session, 
                    client.id, 
                    prompt_tokens, 
                    cached.completion_tokens,
                    token_count_method=token_count_method,
                    tokens_estimated=tokens_estimated
                )
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
            cloud_blocked_by_guardrail=cloud_blocked_by_guardrail,
            commercial_guardrail_context=commercial_guardrail_context,
            session=session,
        )
        latency_ms = int((perf_counter() - started) * 1000)
        if payload.stream:
            estimated_stream_tokens = max_tokens
            await record_usage(
                session, 
                client.id, 
                prompt_tokens, 
                estimated_stream_tokens,
                token_count_method=token_count_method,
                tokens_estimated=tokens_estimated
            )
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
        await record_usage(
            session, 
            client.id, 
            prompt_tokens, 
            completion_tokens,
            token_count_method=token_count_method,
            tokens_estimated=tokens_estimated
        )
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
        
        # Update commercial routing analytics with actual results
        try:
            from app.services.billing.pricing_engine import estimate_provider_cost, calculate_customer_price
            # Try to get completion tokens from local scope if available
            c_tokens = locals().get("completion_tokens") or locals().get("estimated_stream_tokens") or 0
            act_cost_res = estimate_provider_cost(result.backend_name if 'result' in locals() else "unknown", prompt_tokens, c_tokens)
            act_rev_res = calculate_customer_price(effective_plan.code, prompt_tokens, c_tokens)
            
            await commercial_analytics.update_actual_financials(
                session,
                correlation_id=get_correlation_id(),
                actual_cost_brl=act_cost_res.cost_brl,
                actual_revenue_brl=act_rev_res.price_brl,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to update commercial analytics: {e}")

        await session.commit()
        return result.response
    except CommercialGuardrailBlockedError:
        latency_ms = int((perf_counter() - started) * 1000)
        payload_body = build_openai_guardrail_error_payload()
        await log_request(
            session,
            client_id=client.id,
            model=selected_model.model_id,
            endpoint="/v1/completions",
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            status_code=503,
            is_stream=payload.stream,
            estimated_cost_usd=estimated_request_cost,
            backend_name=None,
            attempts=0,
            fallback_used=False,
            cache_hit=False,
            backend_errors=[],
            error_message=payload_body["error"]["message"],
            request_summary=request_summary,
            plan_code=effective_plan.code,
            safety_profile=payload.safety_profile,
        )
        
        # Update commercial routing analytics with actual results
        try:
            from app.services.billing.pricing_engine import estimate_provider_cost, calculate_customer_price
            # Try to get completion tokens from local scope if available
            c_tokens = locals().get("completion_tokens") or locals().get("estimated_stream_tokens") or 0
            act_cost_res = estimate_provider_cost(result.backend_name if 'result' in locals() else "unknown", prompt_tokens, c_tokens)
            act_rev_res = calculate_customer_price(effective_plan.code, prompt_tokens, c_tokens)
            
            await commercial_analytics.update_actual_financials(
                session,
                correlation_id=get_correlation_id(),
                actual_cost_brl=act_cost_res.cost_brl,
                actual_revenue_brl=act_rev_res.price_brl,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to update commercial analytics: {e}")

        await session.commit()
        return JSONResponse(status_code=503, content=payload_body)
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
