from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

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
    user_id: str | None = None
    agent_id: str | None = None
    action_type: str  # tool_call, inference, memory_access, etc.
    tool_name: str | None = None
    model: str | None = None
    backend: str | None = None
    data_classification: str | None = "unclassified"
    risk_score: float = 0.0
    attestation_status: str | None = "none"
    sandbox_level: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    result: DecisionResult
    reason: str
    engine: str
    decision_id: str
    explanation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyBundle(BaseModel):
    name: str
    version: str
    rules: list[dict[str, Any]]
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
