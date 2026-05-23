import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.contracts.agents.base import AgentContract, CompatibilityPolicy

class AgentMemoryCitationV1(BaseModel):
    memory_id: uuid.UUID
    content_snippet: str
    source: str
    relevance_score: float

class AgentMemoryContextV1(BaseModel):
    context_block: str
    citations: List[AgentMemoryCitationV1] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryInjectionContractV1(AgentContract[BaseModel, AgentMemoryContextV1]):
    contract_name = "agent_memory_injection"
    version = "1.0.0"
    input_schema = BaseModel
    output_schema = AgentMemoryContextV1
    compatibility_policy = CompatibilityPolicy.BACKWARD
