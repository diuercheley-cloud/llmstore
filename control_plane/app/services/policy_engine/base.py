from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DecisionResult(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_ATTESTATION = "require_attestation"
    REQUIRE_SANDBOX = "require_sandbox"
    REDACT = "redact"
    AUDIT_ONLY = "audit_only"


class PolicyContext(BaseModel):
    tenant_id: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    action_type: str  # tool_call, inference, memory_access, etc.
    tool_name: Optional[str] = None
    model: Optional[str] = None
    backend: Optional[str] = None
    data_classification: Optional[str] = "unclassified"
    risk_score: float = 0.0
    attestation_status: Optional[str] = "none"
    sandbox_level: int = 0
    extra: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    result: DecisionResult
    reason: str
    engine: str
    decision_id: str
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyBundle(BaseModel):
    name: str
    version: str
    rules: List[Dict[str, Any]]
    engine_type: str  # builtin, opa, cedar


class PolicyEngine(ABC):
    @abstractmethod
    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """Evaluate a policy context and return a decision."""
        pass

    @abstractmethod
    def get_engine_name(self) -> str:
        """Return the name of the engine."""
        pass
