from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


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


class RoutingDecision(BaseModel):
    selected_provider: str
    selected_model: str
    selected_backend: str | None = None
    reason: str
    fallback_chain: list[str] = Field(default_factory=list)
    estimated_cost_brl: float = 0.0
    policy_applied: str | None = None
    cloud_used: bool = False
    warnings: list[str] = Field(default_factory=list)


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
