from datetime import datetime
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import CLIENT_REQUEST_COUNTER
from app.core.request_context import get_correlation_id, get_source_ip
from app.core.time import utc_now
from app.models.request_log import RequestLog


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
    backend_errors: list[dict] | None,
    error_message: str | None,
    request_summary: str | None,
    safety_profile: str | None = "default",
    correlation_id: str | None = None,
    source_ip: str | None = None,
) -> None:
    resolved_correlation_id = correlation_id or get_correlation_id() or None
    resolved_source_ip = source_ip or get_source_ip() or None
    request_log = RequestLog(
        client_id=client_id,
        model=model,
        endpoint=endpoint,
        prompt_tokens_estimated=prompt_tokens,
        completion_tokens_estimated=completion_tokens,
        latency_ms=latency_ms,
        http_status=status_code,
        is_stream=is_stream,
        estimated_cost_usd=estimated_cost_usd,
        backend_name=backend_name,
        attempts=attempts,
        fallback_used=fallback_used,
        cache_hit=cache_hit,
        backend_errors_json=json.dumps(backend_errors) if backend_errors else None,
        error_message=error_message,
        request_summary=request_summary,
        safety_profile=safety_profile,
        correlation_id=resolved_correlation_id,
        source_ip=resolved_source_ip,
        created_at=utc_now(),
    )
    session.add(request_log)
    CLIENT_REQUEST_COUNTER.labels(
        client_id=str(client_id),
        endpoint=endpoint,
        status_class=f"{int(status_code) // 100}xx",
    ).inc()
