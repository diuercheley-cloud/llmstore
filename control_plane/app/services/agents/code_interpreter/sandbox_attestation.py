# Owner: agent-platform
import datetime
import hashlib
import json
import uuid
from typing import Any

from pydantic import BaseModel, Field

from .microvm_policy import SandboxIsolationProfile


class SandboxAttestation(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    provider: str
    kernel_isolation_level: str
    network_mode: str
    filesystem_mode: str
    limits: dict[str, Any]
    artifact_hashes: dict[str, str] = Field(default_factory=dict)


class AttestationService:
    def create_attestation(
        self,
        profile: SandboxIsolationProfile,
        code: str,
        stdout: str,
        stderr: str,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> SandboxAttestation:
        artifact_hashes = {
            "code": self._hash_text(code),
            "stdout": self._hash_text(stdout),
            "stderr": self._hash_text(stderr),
        }
        for artifact in artifacts or []:
            name = artifact.get("name") or artifact.get("filename") or f"artifact-{len(artifact_hashes)}"
            artifact_hashes[str(name)] = self._hash_payload(artifact)
        return SandboxAttestation(
            provider=profile.provider,
            kernel_isolation_level=profile.kernel_isolation_level,
            network_mode=profile.network_mode,
            filesystem_mode=profile.filesystem_mode,
            limits=profile.limits,
            artifact_hashes=artifact_hashes,
        )

    def verify_attestation(self, attestation: dict[str, Any] | SandboxAttestation | None) -> bool:
        if attestation is None:
            return False
        record = attestation if isinstance(attestation, SandboxAttestation) else SandboxAttestation.model_validate(attestation)
        required_hashes = {"code", "stdout", "stderr"}
        return (
            bool(record.provider)
            and bool(record.kernel_isolation_level)
            and record.network_mode == "none"
            and bool(record.filesystem_mode)
            and bool(record.limits)
            and required_hashes.issubset(record.artifact_hashes.keys())
        )

    def _hash_text(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _hash_payload(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
