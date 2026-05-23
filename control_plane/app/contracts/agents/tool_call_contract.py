import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.contracts.agents.base import AgentContract, CompatibilityPolicy

class AgentToolCallV1(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    run_id: Optional[uuid.UUID] = None

class AgentToolResultV1(BaseModel):
    status: str # success|failed
    output: Any
    error_message: Optional[str] = None
    latency_ms: int

class ToolCallContractV1(AgentContract[AgentToolCallV1, AgentToolResultV1]):
    contract_name = "agent_tool_call"
    version = "1.0.0"
    input_schema = AgentToolCallV1
    output_schema = AgentToolResultV1
    compatibility_policy = CompatibilityPolicy.BACKWARD
