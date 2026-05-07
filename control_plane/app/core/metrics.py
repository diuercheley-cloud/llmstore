from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


def _label(value: object | None, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback

REQUEST_COUNTER = Counter(
    "control_plane_requests_total",
    "Total requests handled by the control plane",
    ["endpoint", "status"],
)
CLIENT_REQUEST_COUNTER = Counter(
    "control_plane_client_requests_total",
    "Requests handled per client",
    ["client_id", "endpoint", "status_class"],
)
REQUEST_LATENCY = Histogram(
    "control_plane_request_latency_seconds",
    "Latency for proxied generation requests",
    ["endpoint"],
)
BACKEND_ERROR_COUNTER = Counter(
    "control_plane_backend_errors_total",
    "Backend request errors",
    ["backend_name", "endpoint", "status_code"],
)
BACKEND_LATENCY = Histogram(
    "control_plane_backend_latency_seconds",
    "Latency per backend",
    ["backend_name", "endpoint"],
)
CACHE_RESULT_COUNTER = Counter(
    "control_plane_cache_result_total",
    "Cache hit and miss totals",
    ["endpoint", "result"],
)
ACTIVE_GENERATIONS = Gauge(
    "control_plane_active_generations",
    "Active generations currently executing",
)
QUEUE_DEPTH = Gauge(
    "control_plane_queue_depth",
    "Current in-memory queue depth",
)
QUEUE_WAITING = Gauge(
    "control_plane_queue_waiting",
    "Requests waiting in logical queues",
    ["queue_name"],
)
QUEUE_ACTIVE = Gauge(
    "control_plane_queue_active",
    "Requests active in logical queues",
    ["queue_name"],
)
QUEUE_FAILED = Counter(
    "control_plane_queue_failed_total",
    "Requests that failed due to queue limits or timeouts",
    ["queue_name", "reason"],
)
QUEUE_WAIT_TIME = Histogram(
    "control_plane_queue_wait_time_seconds",
    "Time spent in logical queues",
    ["queue_name"],
)
ASYNC_QUEUE_DEPTH = Gauge(
    "control_plane_async_queue_depth",
    "Current async queue depth in Redis",
)
ASYNC_JOB_COUNTER = Counter(
    "control_plane_async_jobs_total",
    "Async job lifecycle totals",
    ["status"],
)
CIRCUIT_BREAKER_STATE = Gauge(
    "control_plane_circuit_breaker_open",
    "Circuit breaker state for data plane access",
)
SECURITY_EVENT_COUNTER = Counter(
    "control_plane_security_events_total",
    "Security events recorded",
    ["event_type", "severity"],
)
BILLING_STATUS_GAUGE = Gauge(
    "control_plane_clients_billing_status",
    "Clients grouped by billing status",
    ["billing_status"],
)

REQUESTS_TOTAL = Counter(
    "requests",
    "Total requests handled by the control plane",
    ["model", "backend", "plan", "endpoint", "status_code"],
)
REQUEST_LATENCY_SECONDS = Histogram(
    "request_latency_seconds",
    "End-to-end request latency",
    ["model", "backend", "plan", "endpoint", "status_code"],
)
TOKENS_PROMPT_TOTAL = Counter(
    "tokens_prompt",
    "Prompt tokens processed by the control plane",
    ["model", "backend", "plan", "endpoint"],
)
TOKENS_COMPLETION_TOTAL = Counter(
    "tokens_completion",
    "Completion tokens processed by the control plane",
    ["model", "backend", "plan", "endpoint"],
)
TOKENS_TOTAL = Counter(
    "tokens",
    "Total tokens processed by the control plane",
    ["model", "backend", "plan", "endpoint"],
)
INFERENCE_LATENCY_SECONDS = Histogram(
    "inference_latency_seconds",
    "Latency spent talking to the inference backend",
    ["model", "backend", "plan", "endpoint", "status_code"],
)
QUEUE_WAIT_SECONDS = Histogram(
    "queue_wait_seconds",
    "Time spent waiting for a request slot",
    ["plan"],
)
CACHE_HITS_TOTAL = Counter(
    "cache_hits",
    "Cache hits observed by the control plane",
    ["model", "backend", "plan", "endpoint"],
)
CACHE_MISSES_TOTAL = Counter(
    "cache_misses",
    "Cache misses observed by the control plane",
    ["model", "backend", "plan", "endpoint"],
)
BACKEND_ERRORS_TOTAL = Counter(
    "backend_errors",
    "Backend errors observed by the control plane",
    ["model", "backend", "plan", "endpoint", "status_code"],
)
MODEL_ERRORS_TOTAL = Counter(
    "model_errors",
    "Model errors observed by the control plane",
    ["model", "backend", "plan", "endpoint", "status_code"],
)


def record_request_metrics(
    *,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
    status_code: int,
    latency_seconds: float,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    labels = {
        "model": _label(model),
        "backend": _label(backend),
        "plan": _label(plan),
        "endpoint": _label(endpoint),
        "status_code": str(int(status_code)),
    }
    REQUESTS_TOTAL.labels(**labels).inc()
    REQUEST_LATENCY_SECONDS.labels(**labels).observe(max(latency_seconds, 0.0))
    token_labels = {key: labels[key] for key in ("model", "backend", "plan", "endpoint")}
    TOKENS_PROMPT_TOTAL.labels(**token_labels).inc(max(int(prompt_tokens), 0))
    TOKENS_COMPLETION_TOTAL.labels(**token_labels).inc(max(int(completion_tokens), 0))
    TOKENS_TOTAL.labels(**token_labels).inc(max(int(prompt_tokens) + int(completion_tokens), 0))


def record_inference_latency(
    *,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
    status_code: int,
    latency_seconds: float,
) -> None:
    INFERENCE_LATENCY_SECONDS.labels(
        model=_label(model),
        backend=_label(backend),
        plan=_label(plan),
        endpoint=_label(endpoint),
        status_code=str(int(status_code)),
    ).observe(max(latency_seconds, 0.0))


def record_queue_wait(*, plan: str | None, wait_seconds: float) -> None:
    QUEUE_WAIT_SECONDS.labels(plan=_label(plan)).observe(max(wait_seconds, 0.0))


def record_cache_result(
    *,
    hit: bool,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
) -> None:
    labels = {
        "model": _label(model),
        "backend": _label(backend),
        "plan": _label(plan),
        "endpoint": _label(endpoint),
    }
    if hit:
        CACHE_HITS_TOTAL.labels(**labels).inc()
    else:
        CACHE_MISSES_TOTAL.labels(**labels).inc()


def record_backend_error(
    *,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
    status_code: int,
) -> None:
    BACKEND_ERRORS_TOTAL.labels(
        model=_label(model),
        backend=_label(backend),
        plan=_label(plan),
        endpoint=_label(endpoint),
        status_code=str(int(status_code)),
    ).inc()


def record_model_error(
    *,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
    status_code: int,
) -> None:
    MODEL_ERRORS_TOTAL.labels(
        model=_label(model),
        backend=_label(backend),
        plan=_label(plan),
        endpoint=_label(endpoint),
        status_code=str(int(status_code)),
    ).inc()
