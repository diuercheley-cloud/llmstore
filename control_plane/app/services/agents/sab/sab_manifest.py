# Owner: agent-platform
from typing import Any

from pydantic import BaseModel, Field


class AgentSABManifest(BaseModel):
    # Agent metadata
    agent_id: str
    name: str
    version: str
    instructions: str

    # Dependencies
    tool_schemas: list[dict[str, Any]] = Field(default_factory=list)
    memory_policy: dict[str, Any] = Field(default_factory=dict)

    # Quality & Eval
    eval_suite: dict[str, Any] | None = None

    # Optional Data Snapshot (redacted)
    memory_snapshot: list[dict[str, Any]] | None = None

    # Platform Compatibility
    supported_platform_version: str = "v2.0.0"

    # Integrity & Security
    checksums: dict[str, str] = Field(default_factory=dict)
    signature: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
