# Owner: agent-platform
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentSABManifest(BaseModel):
    # Agent metadata
    agent_id: str
    name: str
    version: str
    instructions: str
    
    # Dependencies
    tool_schemas: List[Dict[str, Any]] = Field(default_factory=list)
    memory_policy: Dict[str, Any] = Field(default_factory=dict)
    
    # Quality & Eval
    eval_suite: Optional[Dict[str, Any]] = None
    
    # Optional Data Snapshot (redacted)
    memory_snapshot: Optional[List[Dict[str, Any]]] = None
    
    # Platform Compatibility
    supported_platform_version: str = "v2.0.0"
    
    # Integrity & Security
    checksums: Dict[str, str] = Field(default_factory=dict)
    signature: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)
