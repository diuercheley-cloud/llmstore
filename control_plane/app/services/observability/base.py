import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.time import utc_now
from pydantic import BaseModel, Field


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class ObservabilityMetric(BaseModel):
    name: str
    value: float
    type: MetricType
    unit: str
    tenant_id: str | None = "default"
    agent_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class TraceEvent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    span_id: uuid.UUID
    trace_id: uuid.UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class Span(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    trace_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    name: str
    start_time: datetime = Field(default_factory=utc_now)
    end_time: datetime | None = None
    status: str = "running"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnomalySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Anomaly(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    metric_name: str
    severity: AnomalySeverity
    description: str
    value: float
    baseline: float
    timestamp: datetime = Field(default_factory=utc_now)
    evidence: dict[str, Any] = Field(default_factory=dict)
