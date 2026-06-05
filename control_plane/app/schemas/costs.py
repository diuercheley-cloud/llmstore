from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CostSummary(BaseModel):
    total_cost: float
    currency: str
    event_count: int


class CostByAgent(BaseModel):
    agent_id: Optional[UUID]
    total_cost: float
    event_count: int
    input_tokens: int
    output_tokens: int


class CostByTool(BaseModel):
    tool_name: Optional[str]
    total_cost: float
    event_count: int


class CostByTenant(BaseModel):
    tenant_id: str
    total_cost: float
    event_count: int


class CostEventRead(BaseModel):
    id: UUID
    tenant_id: str
    user_id: Optional[str]
    agent_id: Optional[UUID]
    workflow_id: Optional[str]
    tool_name: Optional[str]
    model: Optional[str]
    backend: Optional[str]
    input_tokens: int
    output_tokens: int
    latency_ms: Optional[int]
    estimated_cost: float
    currency: str
    created_at: datetime
