from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AdapterCapability:
    name: str
    description: str


@dataclass(frozen=True)
class AdapterContract:
    adapter_name: str
    adapter_version: str
    allowed_capabilities: list[str]
    denied_capabilities: list[str]


@dataclass(frozen=True)
class AdapterExecutionRequest:
    client_id: str
    action_type: str
    target_domain: str
    parameters: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True


@dataclass(frozen=True)
class AdapterExecutionResult:
    status: str
    output: dict[str, Any]
    immutable_hash: str
