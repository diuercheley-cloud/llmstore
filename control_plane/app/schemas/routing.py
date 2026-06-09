from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EndpointType(str, Enum):
    chat = "chat"
    responses = "responses"
    embeddings = "embeddings"
    rag = "rag"
    tts = "tts"


class TaskType(str, Enum):
    general = "general"
    coding = "coding"
    summarization = "summarization"
    rag = "rag"
    embedding = "embedding"


class RoutingStrategy(str, Enum):
    local_first = "local_first"
    lowest_cost = "lowest_cost"
    premium_quality = "premium_quality"
    coding = "coding"
    embeddings_optimized = "embeddings_optimized"
    rag_optimized = "rag_optimized"
    fallback_only = "fallback_only"
    commercial_profit = "commercial_profit"


class SmartRouterInput(BaseModel):
    tenant: str | None = None
    client_id: UUID | None = None
    endpoint_type: EndpointType = EndpointType.chat
    requested_model: str | None = None
    task_type: TaskType | None = None
    prompt_estimated_tokens: int = Field(default=0, ge=0)
    max_output_tokens: int = Field(default=512, ge=0)
    plan: str | None = None
    remaining_quota: int | None = None
    wallet_balance_brl: float | None = None
    cloud_allowed: bool = False
    latency_preference: str | None = None
    budget_preference: str | None = None
    strategy: RoutingStrategy = RoutingStrategy.local_first
    request_id: str | None = None,
    correlation_id: str | None = None,
    qos_tier_name: str | None = None,



class RoutingDecision(BaseModel):
    id: str | None = None
    selected_provider: str
    selected_model: str
    selected_backend: str | None = None
    reason: str
    fallback_chain: list[str] = Field(default_factory=list)
    estimated_cost_brl: float = 0.0
    policy_applied: str | None = None
    cloud_used: bool = False
    warnings: list[str] = Field(default_factory=list)
    estimated_revenue_brl: float | None = None
    estimated_margin_brl: float | None = None
    estimated_margin_percent: float | None = None
    selected_score: float | None = None
    ranked_routes: list[Any] | None = None
    rejected_routes: list[Any] | None = None
    guardrail_decisions: list[Any] | None = None
    commercial_config_id: UUID | None = None
    commercial_config_variant: str | None = None


class SimulateRoutingRequest(BaseModel):
    tenant: str | None = None
    client_id: UUID | None = None
    endpoint_type: EndpointType = EndpointType.chat
    requested_model: str | None = None
    task_type: TaskType | None = None
    prompt_estimated_tokens: int = Field(default=100, ge=0)
    max_output_tokens: int = Field(default=512, ge=0)
    plan: str | None = None
    remaining_quota: int | None = None
    wallet_balance_brl: float | None = None
    cloud_allowed: bool = False
    latency_preference: str | None = None
    budget_preference: str | None = None
    strategy: RoutingStrategy = RoutingStrategy.local_first
    request_id: str | None = None,
    correlation_id: str | None = None,
    qos_tier_name: str | None = None,



class SimulateRoutingResponse(BaseModel):
    decision: RoutingDecision
    strategies_considered: list[str] = Field(default_factory=list)
    provider_states: dict[str, str] = Field(default_factory=dict)
    config_snapshot: dict[str, object] = Field(default_factory=dict)


class PolicyRead(BaseModel):
    default_strategy: str
    allow_cloud_fallback: bool
    complexity_threshold: int
    coding_provider_preference: str
    low_budget_provider_preference: str
    premium_provider_preference: str
    max_provider_cost_per_request_brl: float
    tenant_policy_overrides: dict[str, object]
    fallback_order: list[str]


class LastDecisionRead(BaseModel):
    id: str
    timestamp: datetime
    requested_model: str
    resolved_model: str
    selected_provider: str
    routing_strategy: str
    fallback_used: bool
    fallback_reason: str | None
    cloud_used: bool
    estimated_cost_brl: float
    sanitized_reason: str


class CommercialRouteCandidate(BaseModel):
    provider: str
    model: str
    estimated_cost_brl: float
    estimated_price_brl: float
    estimated_margin_brl: float
    estimated_margin_percent: float | None
    is_cloud: bool
    rejected: bool = False
    rejection_reason: str | None = None


class CommercialScoreExplained(BaseModel):
    provider: str
    model: str
    score: float
    estimated_cost_brl: float
    estimated_revenue_brl: float
    estimated_margin_brl: float
    estimated_margin_percent: float | None
    latency_penalty: float = 0.0
    health_penalty: float = 0.0
    local_bonus: float = 0.0
    policy_bonus: float = 0.0
    rejection_reasons: list[str] = Field(default_factory=list)
    commercial_config_id: UUID | None = None
    commercial_config_variant: str | None = None


class CommercialSimulateRequest(BaseModel):
    client_id: str | None = None
    plan: str
    model: str = "default"
    estimated_input_tokens: int = Field(default=100, ge=1)
    estimated_output_tokens: int = Field(default=512, ge=1)
    task_type: TaskType = TaskType.general
    wallet_balance_brl: float | None = None
    billing_status: str = "active"
    cloud_allowed: bool | None = None
    policy: str = "commercial_profit"


class CommercialSimulateResponse(BaseModel):
    selected_route: CommercialScoreExplained | None = None
    ranked_routes: list[CommercialScoreExplained] = Field(default_factory=list)
    rejected_routes: list[CommercialScoreExplained] = Field(default_factory=list)
    guardrail_decisions: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str = ""
    tier: str = "unknown"

class CommercialCalibrationSimulateRequest(BaseModel):
    provider: str
    model: str
    current_estimated_cost_brl: float
    actual_cost_history_days: int = 7

class CommercialCalibrationSimulateResponse(BaseModel):
    current_estimated_cost_brl: float
    recommended_multiplier: float
    adjusted_estimated_cost_brl: float
    confidence: str
    reason: str

class CommercialConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope_type: str
    provider: str | None
    model: str | None
    cost_multiplier: float
    margin_weight: float
    latency_weight: float
    quality_weight: float
    local_route_bonus: float
    min_margin_percent: float
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    notes: str | None

class CommercialConfigApplyRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    recommended_cost_multiplier: float
    confidence: str = "high"
    notes: str | None = None
    force: bool = False


class CommercialReportScheduleCreate(BaseModel):
    name: str
    enabled: bool = True
    frequency: str = "monthly"
    day_of_month: int | None = None
    day_of_week: int | None = None
    hour_utc: int = Field(default=8, ge=0, le=23)
    recipients_json: list[str] = Field(default_factory=list)
    format: str = "html"
    filters_json: dict[str, Any] = Field(default_factory=dict)


class CommercialReportScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    enabled: bool
    frequency: str
    day_of_month: int | None
    day_of_week: int | None
    hour_utc: int
    recipients_json: list[str] = Field(default_factory=list)
    format: str
    filters_json: dict[str, Any] = Field(default_factory=dict)
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None


class CommercialReportScheduleRunResponse(BaseModel):
    schedule_id: UUID
    status: str
    email_mode: str
    generated_at_utc: str
    recipients: list[str] = Field(default_factory=list)
    report_format: str
    preview_html: str | None = None
    report: dict[str, Any] | None = None

class CommercialQoSFairnessSummary(BaseModel):
    fairness_index: float
    tier_waits: dict[str, float]
    starvation_total: int
    sla_violations_total: int
    period_hours: int
    status: str = "ok"

class CommercialQoSChargebackSummary(BaseModel):
    total_chargeback_brl: float
    by_tier: dict[str, float]
    by_client: dict[str, float]
    record_count: int
    period_hours: int


class CommercialReportDeliveryLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schedule_id: UUID | None
    report_format: str
    recipients_json: list[str] = Field(default_factory=list)
    delivery_mode: str
    delivery_status: str
    smtp_host: str | None = None
    subject: str
    attachment_names_json: list[str] = Field(default_factory=list)
    retries: int
    error_message: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None


class CommercialReportDeliveryListResponse(BaseModel):
    smtp_mode: str
    smtp_enabled: bool
    send_real_email: bool
    allowlist_configured: bool
    max_recipients: int
    deliveries: list[CommercialReportDeliveryLogRead] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class CommercialReportSendTestResponse(BaseModel):
    schedule_id: UUID
    status: str
    email_mode: str
    recipients: list[str] = Field(default_factory=list)
    report_format: str
    delivery_id: UUID | None = None

CommercialSimulateResponse.model_rebuild()


class CommercialQoSTierCreate(BaseModel):
    name: str
    enabled: bool = True
    priority: int = 0
    target_latency_ms: int = 500
    max_p95_latency_ms: int = 2000
    min_margin_percent: float = 5.0
    max_cost_per_request_brl: float = 0.50
    allow_cloud: bool = False
    allow_cross_cluster: bool = False
    allow_degraded_cluster: bool = False
    allow_fallback_local: bool = True
    queue_priority: int = 100
    max_retries: int = 3
    timeout_seconds: int = 30
    streaming_timeout_seconds: int = 60
    quality_floor: int | None = None
    degradation_policy: str = "best_effort"
    metadata_json: dict[str, Any] | None = None


class CommercialQoSTierUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    priority: int | None = None
    target_latency_ms: int | None = None
    max_p95_latency_ms: int | None = None
    min_margin_percent: float | None = None
    max_cost_per_request_brl: float | None = None
    allow_cloud: bool | None = None
    allow_cross_cluster: bool | None = None
    allow_degraded_cluster: bool | None = None
    allow_fallback_local: bool | None = None
    queue_priority: int | None = None
    max_retries: int | None = None
    timeout_seconds: int | None = None
    streaming_timeout_seconds: int | None = None
    quality_floor: int | None = None
    degradation_policy: str | None = None
    metadata_json: dict[str, Any] | None = None


class CommercialQoSTierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    enabled: bool
    priority: int
    target_latency_ms: int
    max_p95_latency_ms: int
    min_margin_percent: float
    max_cost_per_request_brl: float
    allow_cloud: bool
    allow_cross_cluster: bool
    allow_degraded_cluster: bool
    allow_fallback_local: bool
    queue_priority: int
    max_retries: int
    timeout_seconds: int
    streaming_timeout_seconds: int
    quality_floor: int | None
    degradation_policy: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class CommercialQoSSimulateRequest(BaseModel):
    client_id: UUID | None = None
    plan: str | None = None
    model: str = "gpt-4"
    estimated_tokens: int = 2000
    stream: bool = False
    task_type: TaskType = TaskType.general


class CommercialQoSSimulateResponse(BaseModel):
    tier: str
    selected_route: CommercialScoreExplained | None = None
    ranked_routes: list[CommercialScoreExplained] = Field(default_factory=list)
    rejected_routes: list[CommercialScoreExplained] = Field(default_factory=list)
    degradation_path: str | None = None
    sla_pass: bool
    warnings: list[str] = Field(default_factory=list)
