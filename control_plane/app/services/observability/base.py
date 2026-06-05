import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


from app.core.time import utc_now


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class ObservabilityMetric(BaseModel):
    name: str
    value: float
    type: MetricType
    unit: str
    tenant_id: Optional[str] = "default"
    agent_id: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class TraceEvent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    span_id: uuid.UUID
    trace_id: uuid.UUID
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class Span(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    trace_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str
    start_time: datetime = Field(default_factory=utc_now)
    end_time: Optional[datetime] = None
    status: str = "running"
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    evidence: Dict[str, Any] = Field(default_factory=dict)
