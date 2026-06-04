from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class AdapterCapability:
    name: str
    description: str

@dataclass(frozen=True)
class AdapterContract:
    adapter_name: str
    adapter_version: str
    allowed_capabilities: List[str]
    denied_capabilities: List[str]

@dataclass(frozen=True)
class AdapterExecutionRequest:
    client_id: str
    action_type: str
    target_domain: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True

@dataclass(frozen=True)
class AdapterExecutionResult:
    status: str
    output: Dict[str, Any]
    immutable_hash: str
