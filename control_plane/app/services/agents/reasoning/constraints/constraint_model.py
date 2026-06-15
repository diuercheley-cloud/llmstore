# Owner: agent-platform
from typing import Any

from pydantic import BaseModel, Field


class Constraint(BaseModel):
    id: str
    type: str  # comparison|arithmetic|logic|resource
    target_field: str
    operator: str  # eq|gt|lt|ge|le|neq|in|subset
    value: Any
    message: str | None = None


class ConstraintModel(BaseModel):
    constraints: list[Constraint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
