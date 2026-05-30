from datetime import datetime
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import record_request_metrics
from app.core.request_context import get_correlation_id, get_source_ip
from app.core.time import utc_now
from app.models.request_log import RequestLog
from app.services.inference.reproducibility import capture_reproducibility_record

logger = logging.getLogger(__name__)

async def log_request(
    session: AsyncSession,
    *,
    client_id,
    model: str,
    endpoint: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    status_code: int,
    is_stream: bool,
    estimated_cost_usd: float,
    backend_name: str | None,
    attempts: int,
    fallback_used: bool,
    cache_hit: bool,
    tool_call_count: int = 0,
    tool_calls: list[dict] | None = None,
    backend_errors: list[dict] | None = None,
    error_message: str | None = None,
    request_summary: str | None = None,
    plan_code: str | None = None,
    safety_profile: str | None = "default",
    correlation_id: str | None = None,
    source_ip: str | None = None,
    request_payload: dict | None = None,
    response_payload: dict | None = None,
    reproducibility_context: dict | None = None,
    token_count_method: str | None = None,
    tokens_estimated: bool = True,
) -> RequestLog:
    resolved_correlation_id = correlation_id or get_correlation_id() or None
    resolved_source_ip = source_ip or get_source_ip() or None
    request_log = RequestLog(
        client_id=client_id,
        model=model,
        endpoint=endpoint,
        prompt_tokens_estimated=prompt_tokens,
        completion_tokens_estimated=completion_tokens,
        # TODO: Add token_count_method and tokens_estimated to RequestLog model if needed
        # but for now we follow instructions and they were only requested for usage_record and request_financials.
        latency_ms=latency_ms,
        http_status=status_code,
        is_stream=is_stream,
        estimated_cost_usd=estimated_cost_usd,
        backend_name=backend_name,
        attempts=attempts,
        fallback_used=fallback_used,
        cache_hit=cache_hit,
        tool_call_count=tool_call_count,
        tool_calls_json=json.dumps(tool_calls) if tool_calls else None,
        backend_errors_json=json.dumps(backend_errors) if backend_errors else None,
        error_message=error_message,
        request_summary=request_summary,
        safety_profile=safety_profile,
        correlation_id=resolved_correlation_id,
        source_ip=resolved_source_ip,
        created_at=utc_now(),
    )
    session.add(request_log)
    await session.flush()
    record_request_metrics(
        model=model,
        backend=backend_name,
        plan=plan_code,
        endpoint=endpoint,
        status_code=status_code,
        latency_seconds=float(latency_ms) / 1000.0,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    
    # Model Experiments Phase
    try:
        from app.services.model_experiments.context import get_experiment_context
        from app.services.model_experiments.experiment_metrics import ExperimentMetrics
        exp_ctx = get_experiment_context()
        if exp_ctx:
            exp_metrics = ExperimentMetrics(session)
            exp_id = exp_ctx["experiment_id"]
            var_id = exp_ctx["variant_id"]
            
            # Record base metrics
            await exp_metrics.record_metric(exp_id, var_id, "latency", float(latency_ms))
            await exp_metrics.record_metric(exp_id, var_id, "error_rate", 1.0 if status_code >= 400 else 0.0)
            await exp_metrics.record_metric(exp_id, var_id, "cost", float(estimated_cost_usd))
    except Exception:
        logger.exception("failed to record model experiment metrics")

    if request_payload is not None or response_payload is not None:
        try:
            context = reproducibility_context or {}
            await capture_reproducibility_record(
                session,
                request_id=str(request_log.id),
                correlation_id=resolved_correlation_id,
                client_id=str(client_id) if client_id is not None else None,
                model_name=model,
                model_alias=context.get("model_alias"),
                provider=context.get("provider"),
                backend_name=backend_name,
                request_payload=request_payload,
                response_payload=response_payload,
                prompt_template=context.get("prompt_template"),
                tokenizer_name=context.get("tokenizer_name"),
                tokenizer_version=context.get("tokenizer_version"),
                runtime_engine=context.get("runtime_engine"),
                runtime_engine_version=context.get("runtime_engine_version"),
                model_metadata_json=context.get("model_metadata_json"),
                backend_metadata_json=context.get("backend_metadata_json"),
                metadata_json={
                    "endpoint": endpoint,
                    "request_summary": request_summary,
                    "safety_profile": safety_profile,
                    "tool_call_count": tool_call_count,
                    "backend_errors": backend_errors or [],
                    "error_message": error_message,
                    "audit_event": "reproducibility_record_created",
                    **(context.get("metadata_json") or {}),
                },
            )
        except Exception:
            logger.exception("failed to capture reproducibility record")
    return request_log
