import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    SANDBOXED = "sandboxed"
    TRUSTED = "trusted"
    INTERNAL = "internal"


class ProtocolType(str, Enum):
    MCP = "mcp"
    A2A = "a2a"


class MCPToolServer(BaseModel):
    id: uuid.UUID
    name: str
    endpoint: str
    transport: str
    trust_level: TrustLevel
    capabilities: List[str] = Field(default_factory=list)


class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_id: uuid.UUID
    is_approved: bool = False


class A2AAgentEndpoint(BaseModel):
    id: uuid.UUID
    agent_name: str
    base_url: str
    trust_level: TrustLevel
    allowed_message_types: List[str] = Field(default_factory=list)


class AgentCapability(BaseModel):
    name: str
    version: str
    description: str


class ProtocolTrustPolicy(BaseModel):
    protocol: ProtocolType
    min_trust_level: TrustLevel
    require_approval: bool = True
    require_signature: bool = False
    allowed_scopes: List[str] = Field(default_factory=list)
