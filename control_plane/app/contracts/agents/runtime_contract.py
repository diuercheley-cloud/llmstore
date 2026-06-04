import uuid
from typing import Any, Dict, Optional

from app.contracts.agents.base import AgentContract, CompatibilityPolicy
from pydantic import BaseModel, Field


class AgentRunRequestV1(BaseModel):
    agent_id: uuid.UUID
    tenant_id: str
    input_text: str
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentRunResultV1(BaseModel):
    run_id: uuid.UUID
    status: str
    output_hash: Optional[str] = None
    total_steps: int
    total_tokens: int
    estimated_cost_brl: float

class RuntimeContractV1(AgentContract[AgentRunRequestV1, AgentRunResultV1]):
    contract_name = "agent_runtime"
    version = "1.0.0"
    input_schema = AgentRunRequestV1
    output_schema = AgentRunResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD
