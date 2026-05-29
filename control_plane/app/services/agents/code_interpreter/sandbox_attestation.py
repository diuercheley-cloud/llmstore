"""Sandbox attestation models and verification helpers."""

# Owner: agent-platform
"""Sandbox attestation models and verification helpers."""

# Owner: agent-platform
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid
from app.core.time import utc_now

class SandboxAttestation(BaseModel):
    provider: str
    isolation_level: str
    runtime_version: Optional[str] = None
    network_policy: str
    filesystem_policy: str
    resource_limits: Dict[str, Any]
    artifact_hashes: List[str] = Field(default_factory=list)
    attestation_time: str = Field(default_factory=lambda: utc_now().isoformat())
    signature: Optional[str] = None

class AttestationService:
    @staticmethod
    def create_attestation(
        profile: Any,
        code: str,
        stdout: str,
        stderr: str,
        artifacts: List[str] = None
    ) -> SandboxAttestation:
        return SandboxAttestation(
            provider=getattr(profile, "provider", "unknown"),
            isolation_level=getattr(profile, "kernel_isolation_level", "unknown"),
            runtime_version=getattr(profile, "runtime_version", None),
            network_policy=getattr(profile, "network_mode", "none"),
            filesystem_policy=getattr(profile, "filesystem_mode", "read-only"),
            resource_limits=getattr(profile, "limits", {}),
            artifact_hashes=artifacts or []
        )

    @staticmethod
    def verify_attestation(attestation: Dict[str, Any]) -> bool:
        # Real verification would check signatures and hashes
        if not attestation.get("provider"):
            return False
        return True
