from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

@dataclass(frozen=True)
class AdapterSandboxContext:
    """
    Immutable execution context for a sandbox run.
    """
    client_id: uuid.UUID
    manifest_id: uuid.UUID
    sandbox_mode: str
    dry_run: bool = True
    approval_verified: bool = False
    gates_verified: bool = False
    allowed_capabilities: List[str] = field(default_factory=list)
    denied_capabilities: List[str] = field(default_factory=list)
    approval_required: bool = True
    gates_required: bool = True
    deterministic_version: str = "v1"

    def can_perform(self, capability: str) -> bool:
        """
        Checks if a capability is allowed in this context.
        Denied capabilities ALWAYS take precedence.
        """
        if capability in self.denied_capabilities:
            return False
        return capability in self.allowed_capabilities
