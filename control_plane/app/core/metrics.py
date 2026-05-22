from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, REGISTRY


def _label(value: object | None, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback

# Legacy Metrics (Maintain for compatibility)
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

# Standardized SLO Metrics
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total requests handled by the platform",
    ["model", "backend", "plan", "endpoint", "status_code"],
)
LLM_REQUEST_ERRORS_TOTAL = Counter(
    "llm_request_errors_total",
    "Total request errors",
    ["model", "backend", "plan", "endpoint", "error_type"],
)
LLM_REQUEST_LATENCY_SECONDS = Histogram(
    "llm_request_latency_seconds",
    "End-to-end request latency",
    ["model", "backend", "plan", "endpoint"],
)
LLM_TOKENS_INPUT_TOTAL = Counter(
    "llm_tokens_input_total",
    "Total input tokens processed",
    ["model", "backend", "plan"],
)
LLM_TOKENS_OUTPUT_TOTAL = Counter(
    "llm_tokens_output_total",
    "Total output tokens generated",
    ["model", "backend", "plan"],
)
LLM_QUEUE_WAIT_SECONDS = Histogram(
    "llm_queue_wait_seconds",
    "Time spent waiting in queue",
    ["plan"],
)
LLM_QUEUE_DEPTH = Gauge(
    "llm_queue_depth",
    "Current number of requests in queue",
    ["plan"],
)
LLM_PROVIDER_HEALTH_SCORE = Gauge(
    "llm_provider_health_score",
    "Health score of a provider (0-1)",
    ["provider_name"],
)
LLM_PROVIDER_FAILURES_TOTAL = Counter(
    "llm_provider_failures_total",
    "Total failures per provider",
    ["provider_name", "error_code"],
)
LLM_ROUTING_DECISIONS_TOTAL = Counter(
    "llm_routing_decisions_total",
    "Total routing decisions made",
    ["strategy", "model"],
)
LLM_ROUTING_FALLBACKS_TOTAL = Counter(
    "llm_routing_fallbacks_total",
    "Total routing fallbacks triggered",
    ["reason", "model"],
)
LLM_CACHE_HITS_TOTAL = Counter(
    "llm_cache_hits_total",
    "Total cache hits",
    ["model", "endpoint"],
)
LLM_CACHE_MISSES_TOTAL = Counter(
    "llm_cache_misses_total",
    "Total cache misses",
    ["model", "endpoint"],
)
LLM_COST_ESTIMATED_BRL_TOTAL = Counter(
    "llm_cost_estimated_brl_total",
    "Estimated cost in BRL",
    ["model", "client_id"],
)
LLM_GPU_MEMORY_PRESSURE_RATIO = Gauge(
    "llm_gpu_memory_pressure_ratio",
    "GPU memory pressure ratio (0-1)",
    ["node_id", "gpu_id"],
)
LLM_MODEL_RUNTIME_ACTIVE = Gauge(
    "llm_model_runtime_active",
    "Indicates if a model runtime is active (1) or not (0)",
    ["model_id"],
)
LLM_MODEL_HOT_SWAP_FAILURES_TOTAL = Counter(
    "llm_model_hot_swap_failures_total",
    "Total model hot swap failures",
    ["model_id", "reason"],
)
LLM_RBAC_DENIALS_TOTAL = Counter(
    "llm_rbac_denials_total",
    "Total RBAC access denials",
    ["client_id", "resource", "action"],
)
LLM_ATTESTATION_FAILURES_TOTAL = Counter(
    "llm_attestation_failures_total",
    "Total hardware attestation failures",
    ["node_id", "reason"],
)

# Distributed Runtime Metrics
LLM_RUNTIME_NODES_TOTAL = Counter(
    "llm_runtime_nodes_total",
    "Total runtime nodes registered",
    ["node_type"]
)
LLM_RUNTIME_NODE_HEARTBEATS_TOTAL = Counter(
    "llm_runtime_node_heartbeats_total",
    "Total heartbeats received from nodes",
    ["node_id"]
)
LLM_RUNTIME_NODE_FAILURES_TOTAL = Counter(
    "llm_runtime_node_failures_total",
    "Total node failures detected",
    ["node_id", "reason"]
)
LLM_RUNTIME_FAILOVERS_TOTAL = Counter(
    "llm_runtime_failovers_total",
    "Total failovers triggered",
    ["model_id", "reason"]
)
LLM_RUNTIME_NODE_LOAD_RATIO = Gauge(
    "llm_runtime_node_load_ratio",
    "Current load ratio of the node (0-1)",
    ["node_id"]
)
LLM_RUNTIME_MODEL_PLACEMENTS_TOTAL = Gauge(
    "llm_runtime_model_placements_total",
    "Total model placements on nodes",
    ["node_id", "status"]
)

# GPU & Autoscaling Metrics
LLM_GPU_DEVICES_TOTAL = Gauge(
    "llm_gpu_devices_total",
    "Total GPU devices detected",
    ["node_id", "status"]
)
LLM_GPU_MEMORY_USED_BYTES = Gauge(
    "llm_gpu_memory_used_bytes",
    "Current GPU memory used in bytes",
    ["node_id", "gpu_index"]
)
LLM_GPU_MEMORY_TOTAL_BYTES = Gauge(
    "llm_gpu_memory_total_bytes",
    "Total GPU memory in bytes",
    ["node_id", "gpu_index"]
)
LLM_GPU_UTILIZATION_RATIO = Gauge(
    "llm_gpu_utilization_ratio",
    "GPU utilization ratio (0-1)",
    ["node_id", "gpu_index"]
)
LLM_GPU_TEMPERATURE_CELSIUS = Gauge(
    "llm_gpu_temperature_celsius",
    "GPU temperature in Celsius",
    ["node_id", "gpu_index"]
)
LLM_AUTOSCALING_DECISIONS_TOTAL = Counter(
    "llm_autoscaling_decisions_total",
    "Total autoscaling decisions made",
    ["policy_id", "action"]
)
LLM_AUTOSCALING_REPLICAS_DESIRED = Gauge(
    "llm_autoscaling_replicas_desired",
    "Desired number of replicas by autoscaler",
    ["policy_id"]
)
LLM_AUTOSCALING_REPLICAS_CURRENT = Gauge(
    "llm_autoscaling_replicas_current",
    "Current number of replicas reported by autoscaler",
    ["policy_id"]
)

# Agent Observability Metrics
LLM_AGENT_RUNS_TOTAL = Counter(
    "llm_agent_runs_total",
    "Total agent runs started",
    ["agent_id", "status"]
)
LLM_AGENT_RUN_FAILURES_TOTAL = Counter(
    "llm_agent_run_failures_total",
    "Total agent run failures",
    ["agent_id", "reason"]
)
LLM_AGENT_RUN_DURATION_SECONDS = Histogram(
    "llm_agent_run_duration_seconds",
    "End-to-end duration of agent runs",
    ["agent_id"]
)
LLM_AGENT_STEPS_TOTAL = Counter(
    "llm_agent_steps_total",
    "Total agent steps executed",
    ["agent_id", "step_type"]
)
LLM_AGENT_STEP_LATENCY_SECONDS = Histogram(
    "llm_agent_step_latency_seconds",
    "Latency of agent steps",
    ["agent_id", "step_type"]
)
LLM_AGENT_TOOL_DURATION_SECONDS = Histogram(
    "llm_agent_tool_duration_seconds",
    "Time spent executing tools",
    ["agent_id", "tool_name"]
)
LLM_AGENT_APPROVAL_WAIT_SECONDS = Histogram(
    "llm_agent_approval_wait_seconds",
    "Time agents spent waiting for human approval",
    ["agent_id", "tool_name"]
)
LLM_AGENT_MEMORY_LATENCY_SECONDS = Histogram(
    "llm_agent_memory_latency_seconds",
    "Latency of agent memory operations",
    ["agent_id", "operation"]
)
LLM_AGENT_HANDOFF_COUNT = Counter(
    "llm_agent_handoff_count",
    "Total agent handoffs",
    ["agent_id", "target_agent_id"]
)
LLM_AGENT_POLICY_DENIALS_TOTAL = Counter(
    "llm_agent_policy_denials_total",
    "Total agent policy denials",
    ["agent_id", "tool_name"]
)
LLM_AGENT_INCIDENTS_TOTAL = Counter(
    "llm_agent_incidents_total",
    "Total agent incidents detected",
    ["agent_id", "incident_type", "severity"]
)
LLM_AGENT_SLO_BREACHES_TOTAL = Counter(
    "llm_agent_slo_breaches_total",
    "Total agent SLO breaches",
    ["agent_id", "window_type"]
)
LLM_AGENT_COST_BRL_TOTAL = Counter(
    "llm_agent_cost_brl_total",
    "Total estimated cost of agent runs in BRL",
    ["agent_id"]
)
LLM_AGENT_TOKENS_TOTAL = Counter(
    "llm_agent_tokens_total",
    "Total tokens consumed by agents",
    ["agent_id", "token_type"]
)

# Keep legacy metrics for internal compatibility where needed, or alias them
REQUESTS_TOTAL = LLM_REQUESTS_TOTAL
REQUEST_LATENCY_SECONDS = LLM_REQUEST_LATENCY_SECONDS
TOKENS_PROMPT_TOTAL = LLM_TOKENS_INPUT_TOTAL
TOKENS_COMPLETION_TOTAL = LLM_TOKENS_OUTPUT_TOTAL
QUEUE_WAIT_SECONDS = LLM_QUEUE_WAIT_SECONDS
CACHE_HITS_TOTAL = LLM_CACHE_HITS_TOTAL
CACHE_MISSES_TOTAL = LLM_CACHE_MISSES_TOTAL
BACKEND_ERRORS_TOTAL = LLM_PROVIDER_FAILURES_TOTAL


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
    LLM_REQUESTS_TOTAL.labels(**labels).inc()
    
    latency_labels = {k: v for k, v in labels.items() if k != "status_code"}
    LLM_REQUEST_LATENCY_SECONDS.labels(**latency_labels).observe(max(latency_seconds, 0.0))
    
    token_labels = {key: labels[key] for key in ("model", "backend", "plan")}
    LLM_TOKENS_INPUT_TOTAL.labels(**token_labels).inc(max(int(prompt_tokens), 0))
    LLM_TOKENS_OUTPUT_TOTAL.labels(**token_labels).inc(max(int(completion_tokens), 0))
    
    if status_code >= 400:
        error_labels = labels.copy()
        error_labels.pop("status_code")
        error_labels["error_type"] = "client_error" if status_code < 500 else "server_error"
        LLM_REQUEST_ERRORS_TOTAL.labels(**error_labels).inc()


def record_inference_latency(
    *,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
    status_code: int,
    latency_seconds: float,
) -> None:
    # This was originally INFERENCE_LATENCY_SECONDS, using LLM_REQUEST_LATENCY_SECONDS for now or keep it separate if needed.
    # The requirement specifically asked for llm_request_latency_seconds.
    LLM_REQUEST_LATENCY_SECONDS.labels(
        model=_label(model),
        backend=_label(backend),
        plan=_label(plan),
        endpoint=_label(endpoint),
    ).observe(max(latency_seconds, 0.0))


def record_queue_wait(*, plan: str | None, wait_seconds: float) -> None:
    LLM_QUEUE_WAIT_SECONDS.labels(plan=_label(plan)).observe(max(wait_seconds, 0.0))


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
        "endpoint": _label(endpoint),
    }
    if hit:
        LLM_CACHE_HITS_TOTAL.labels(**labels).inc()
    else:
        LLM_CACHE_MISSES_TOTAL.labels(**labels).inc()


def record_backend_error(
    *,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
    status_code: int,
) -> None:
    LLM_PROVIDER_FAILURES_TOTAL.labels(
        provider_name=_label(backend),
        error_code=str(int(status_code)),
    ).inc()


def record_model_error(
    *,
    model: str | None,
    backend: str | None,
    plan: str | None,
    endpoint: str | None,
    status_code: int,
) -> None:
    # Map to request errors
    error_labels = {
        "model": _label(model),
        "backend": _label(backend),
        "plan": _label(plan),
        "endpoint": _label(endpoint),
        "error_type": "model_error",
    }
    LLM_REQUEST_ERRORS_TOTAL.labels(**error_labels).inc()


def record_routing_decision(strategy: str, model: str) -> None:
    LLM_ROUTING_DECISIONS_TOTAL.labels(strategy=strategy, model=_label(model)).inc()


def record_routing_fallback(reason: str, model: str) -> None:
    LLM_ROUTING_FALLBACKS_TOTAL.labels(reason=reason, model=_label(model)).inc()


def record_rbac_denial(client_id: str, resource: str, action: str) -> None:
    LLM_RBAC_DENIALS_TOTAL.labels(client_id=client_id, resource=resource, action=action).inc()


def record_hot_swap_failure(model_id: str, reason: str) -> None:
    LLM_MODEL_HOT_SWAP_FAILURES_TOTAL.labels(model_id=model_id, reason=reason).inc()


def record_attestation_failure(node_id: str, reason: str) -> None:
    LLM_ATTESTATION_FAILURES_TOTAL.labels(node_id=node_id, reason=reason).inc()


# Agent Execution Plane Metrics
LLM_AGENT_JOBS_QUEUED = Gauge(
    "llm_agent_jobs_queued",
    "Current number of agent jobs queued",
    ["tenant_id", "agent_id"],
)
LLM_AGENT_JOBS_RUNNING = Gauge(
    "llm_agent_jobs_running",
    "Current number of agent jobs running",
    ["tenant_id", "agent_id"],
)
LLM_AGENT_JOBS_COMPLETED_TOTAL = Counter(
    "llm_agent_jobs_completed_total",
    "Total agent jobs completed",
    ["tenant_id", "agent_id"],
)
LLM_AGENT_JOBS_FAILED_TOTAL = Counter(
    "llm_agent_jobs_failed_total",
    "Total agent jobs failed",
    ["tenant_id", "agent_id"],
)
LLM_AGENT_JOBS_CANCELLED_TOTAL = Counter(
    "llm_agent_jobs_cancelled_total",
    "Total agent jobs cancelled",
    ["tenant_id", "agent_id"],
)
LLM_AGENT_JOB_RETRIES_TOTAL = Counter(
    "llm_agent_job_retries_total",
    "Total agent job retries",
    ["tenant_id", "agent_id"],
)
LLM_AGENT_DEAD_LETTERS_TOTAL = Counter(
    "llm_agent_dead_letters_total",
    "Total agent jobs sent to dead letter queue",
    ["tenant_id", "agent_id"],
)
LLM_AGENT_WORKER_HEARTBEATS_TOTAL = Counter(
    "llm_agent_worker_heartbeats_total",
    "Total heartbeats received from workers",
    ["worker_id"],
)
LLM_AGENT_QUEUE_BACKPRESSURE_TOTAL = Counter(
    "llm_agent_queue_backpressure_total",
    "Total enqueuing rejections due to backpressure limits",
    ["tenant_id", "agent_id", "limit_type"],
)

