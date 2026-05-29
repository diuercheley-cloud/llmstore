# Owner: agent-platform
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Constraint(BaseModel):
    id: str
    type: str # comparison|arithmetic|logic|resource
    target_field: str
    operator: str # eq|gt|lt|ge|le|neq|in|subset
    value: Any
    message: Optional[str] = None

class ConstraintModel(BaseModel):
    constraints: List[Constraint] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
