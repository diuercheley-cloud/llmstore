from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


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
LLM_AGENT_RUN_SUCCESS_RATE = Gauge(
    "llm_agent_run_success_rate",
    "Current success rate of agent runs",
    ["agent_id"]
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
LLM_AGENT_PLAN_DEPTH = Gauge(
    "llm_agent_plan_depth",
    "Current depth of the agent's plan",
    ["agent_id", "run_id"]
)
LLM_AGENT_TOOL_DURATION_SECONDS = Histogram(
    "llm_agent_tool_duration_seconds",
    "Time spent executing tools",
    ["agent_id", "tool_name"]
)
LLM_AGENT_TOOL_LATENCY_SECONDS = Histogram(
    "llm_agent_tool_latency_seconds",
    "Latency of tool executions in seconds",
    ["agent_id", "tool_name"]
)
LLM_AGENT_TOOL_FAILURE_RATE = Gauge(
    "llm_agent_tool_failure_rate",
    "Current failure rate of tool calls",
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
LLM_AGENT_MEMORY_HIT_RATE = Gauge(
    "llm_agent_memory_hit_rate",
    "Current memory hit rate",
    ["agent_id", "memory_type"]
)
LLM_AGENT_HANDOFF_COUNT = Counter(
    "llm_agent_handoff_count",
    "Total agent handoffs",
    ["agent_id", "target_agent_id"]
)
LLM_AGENT_HANDOFF_DEPTH = Gauge(
    "llm_agent_handoff_depth",
    "Current handoff depth",
    ["agent_id", "run_id"]
)
LLM_AGENT_POLICY_DENIALS_TOTAL = Counter(
    "llm_agent_policy_denials_total",
    "Total agent policy denials",
    ["agent_id", "tool_name"]
)
LLM_AGENT_REPLAN_TOTAL = Counter(
    "llm_agent_replan_total",
    "Total number of replans executed",
    ["agent_id"]
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
LLM_AGENT_COST_BUDGET_USED_BRL = Gauge(
    "llm_agent_cost_budget_used_brl",
    "Total cost in BRL against budget",
    ["agent_id"]
)
LLM_AGENT_TOKENS_TOTAL = Counter(
    "llm_agent_tokens_total",
    "Total tokens consumed by agents",
    ["agent_id", "token_type"]
)
LLM_AGENT_TOKEN_BUDGET_USED = Gauge(
    "llm_agent_token_budget_used",
    "Total tokens consumed against budget",
    ["agent_id"]
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
LLM_AGENT_ACTIVE_WORKERS = Gauge(
    "llm_agent_active_workers",
    "Current number of active agent workers",
)
LLM_AGENT_ACTIVE_LEASES = Gauge(
    "llm_agent_active_leases",
    "Current number of active job leases",
)
LLM_AGENT_STUCK_RUNS_TOTAL = Gauge(
    "llm_agent_stuck_runs_total",
    "Current number of agent runs detected as stuck",
)
LLM_AGENT_DRAIN_STATUS = Gauge(
    "llm_agent_drain_status",
    "Drain status of workers (1 if draining)",
    ["worker_id"]
)
LLM_AGENT_QUEUE_BACKPRESSURE_TOTAL = Counter(
    "llm_agent_queue_backpressure_total",
    "Total enqueuing rejections due to backpressure limits",
    ["tenant_id", "agent_id", "limit_type"],
)

# Agent Telemetry Backpressure Metrics
LLM_AGENT_TELEMETRY_QUEUE_DEPTH = Gauge(
    "llm_agent_telemetry_queue_depth",
    "Current depth of the telemetry span queue",
    ["tenant_id", "agent_id", "priority"],
)
LLM_AGENT_TELEMETRY_SPANS_DROPPED_TOTAL = Counter(
    "llm_agent_telemetry_spans_dropped_total",
    "Total telemetry spans dropped due to backpressure",
    ["tenant_id", "agent_id", "priority", "reason"],
)
LLM_AGENT_TELEMETRY_EXPORT_FAILURES_TOTAL = Counter(
    "llm_agent_telemetry_export_failures_total",
    "Total telemetry export failures",
    ["tenant_id", "agent_id", "exporter"],
)
LLM_AGENT_TELEMETRY_BACKPRESSURE_ACTIVE = Gauge(
    "llm_agent_telemetry_backpressure_active",
    "Whether telemetry backpressure is currently active (1=active)",
    ["tenant_id", "agent_id"],
)

# Backup and Restore Operational Metrics
BACKUP_LAST_SUCCESS_TIMESTAMP = Gauge(
    "backup_last_success_timestamp",
    "Unix timestamp of the last successful backup"
)
BACKUP_AGE_SECONDS = Gauge(
    "backup_age_seconds",
    "Time in seconds since the last successful backup"
)
BACKUP_FAILURE_TOTAL = Counter(
    "backup_failure_total",
    "Total number of failed backup operations"
)
BACKUP_VERIFICATION_FAILURE_TOTAL = Counter(
    "backup_verification_failure_total",
    "Total number of backup verification failures",
    ["reason"]
)
RESTORE_FAILURE_TOTAL = Counter(
    "restore_failure_total",
    "Total number of failed restore operations"
)
RESTORE_DURATION_SECONDS = Histogram(
    "restore_duration_seconds",
    "Duration of restore operations in seconds"
)
RESTORE_STAGING_DURATION_SECONDS = Histogram(
    "restore_staging_duration_seconds",
    "Duration of restore staging operations in seconds"
)
RESTORE_PROMOTION_DURATION_SECONDS = Histogram(
    "restore_promotion_duration_seconds",
    "Duration of restore promotion operations in seconds"
)
RESTORE_ROLLBACK_DURATION_SECONDS = Histogram(
    "restore_rollback_duration_seconds",
    "Duration of restore rollback operations in seconds"
)
RESTORE_LOCK_CONTENTION_TOTAL = Counter(
    "restore_lock_contention_total",
    "Total number of restore lock acquisition failures"
)
BACKUP_DURATION_SECONDS = Histogram(
    "backup_duration_seconds",
    "Duration of backup operations in seconds"
)
BACKUP_SIZE_BYTES = Gauge(
    "backup_size_bytes",
    "Size of the latest successful backup in bytes"
)
ESTIMATED_RPO_SECONDS = Gauge(
    "estimated_rpo_seconds",
    "Estimated Recovery Point Objective in seconds"
)
MEASURED_RTO_SECONDS = Gauge(
    "measured_rto_seconds",
    "Measured Recovery Time Objective of the last successful restore in seconds"
)


def update_dynamic_backup_metrics() -> None:
    import os
    import time
    from pathlib import Path
    from datetime import datetime, UTC
    import json
    from app.core.config import get_settings
    
    try:
        settings = get_settings()
        backup_root = Path(settings.disaster_recovery_backup_dir or "/tmp/agent-backups") / "system"
        if not backup_root.exists():
            return
            
        latest_time = None
        latest_size = 0
        
        # Sort directories by creation time
        manifests = sorted(backup_root.glob("backup-*/manifest.json"), key=os.path.getmtime, reverse=True)
        for manifest_path in manifests:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                payload_file = manifest.get("payload_file", "payload.tar.gz.enc")
                payload_path = manifest_path.parent / payload_file
                if payload_path.exists():
                    created_at_str = manifest.get("created_at")
                    if created_at_str:
                        try:
                            # Use datetime.fromisoformat replacing 'Z' with '+00:00'
                            dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                            ts = dt.timestamp()
                        except Exception:
                            ts = os.path.getmtime(manifest_path)
                    else:
                        ts = os.path.getmtime(manifest_path)
                        
                    latest_time = ts
                    latest_size = payload_path.stat().st_size
                    break
            except Exception:
                continue
                
        if latest_time is not None:
            now = time.time()
            age = max(0.0, now - latest_time)
            
            BACKUP_LAST_SUCCESS_TIMESTAMP.set(latest_time)
            BACKUP_SIZE_BYTES.set(latest_size)
            BACKUP_AGE_SECONDS.set(age)
            ESTIMATED_RPO_SECONDS.set(age)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to update dynamic backup metrics: {e}")


