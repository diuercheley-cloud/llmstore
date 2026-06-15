from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CostSummary(BaseModel):
    total_cost: float
    currency: str
    event_count: int


class CostByAgent(BaseModel):
    agent_id: UUID | None
    total_cost: float
    event_count: int
    input_tokens: int
    output_tokens: int


class CostByTool(BaseModel):
    tool_name: str | None
    total_cost: float
    event_count: int


class CostByTenant(BaseModel):
    tenant_id: str
    total_cost: float
    event_count: int


class CostEventRead(BaseModel):
    id: UUID
    tenant_id: str
    user_id: str | None
    agent_id: UUID | None
    workflow_id: str | None
    tool_name: str | None
    model: str | None
    backend: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: int | None
    estimated_cost: float
    currency: str
    created_at: datetime
