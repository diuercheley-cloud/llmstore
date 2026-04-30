from prometheus_client import Counter, Gauge, Histogram

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
