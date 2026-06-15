"""Sandbox attestation models and verification helpers."""

# Owner: agent-platform
"""Sandbox attestation models and verification helpers."""

# Owner: agent-platform
from typing import Any

from app.core.time import utc_now
from pydantic import BaseModel, Field


class SandboxAttestation(BaseModel):
    provider: str
    isolation_level: str
    runtime_version: str | None = None
    network_policy: str
    filesystem_policy: str
    resource_limits: dict[str, Any]
    artifact_hashes: list[str] = Field(default_factory=list)
    attestation_time: str = Field(default_factory=lambda: utc_now().isoformat())
    signature: str | None = None


class AttestationService:
    @staticmethod
    def create_attestation(
        profile: Any, code: str, stdout: str, stderr: str, artifacts: list[str] = None
    ) -> SandboxAttestation:
        att = SandboxAttestation(
            provider=getattr(profile, "provider", "unknown"),
            isolation_level=getattr(profile, "kernel_isolation_level", "unknown"),
            runtime_version=getattr(profile, "runtime_version", None),
            network_policy=getattr(profile, "network_mode", "none"),
            filesystem_policy=getattr(profile, "filesystem_mode", "read-only"),
            resource_limits=getattr(profile, "limits", {}),
            artifact_hashes=artifacts or [],
        )
        # Sign the attestation payload using the real key
        try:
            import json

            from app.services.inference.cryptographic_receipts import sign_payload

            payload_data = att.model_dump(exclude={"signature"}, mode="json")
            canonical_str = json.dumps(payload_data, sort_keys=True)
            att.signature = sign_payload(canonical_str)
        except Exception:
            # Fallback if key infrastructure not initialized in test/dev
            att.signature = "placeholder-signature-fallback"
        return att

    @staticmethod
    def verify_attestation(attestation: dict[str, Any]) -> bool:
        if not attestation.get("provider"):
            return False

        from app.core.config import get_settings

        settings = get_settings()
        is_prod = settings.app_env == "production"

        sig = attestation.get("signature")

        if settings.agent_sandbox_production_requires_attestation and is_prod:
            if not sig:
                return False
            sig_lower = sig.lower()
            if any(p in sig_lower for p in ["placeholder", "mock", "stub", "simulated", "fake"]):
                return False

        if sig:
            if sig == "placeholder-signature-fallback":
                return not is_prod

            try:
                import json

                from app.services.inference.cryptographic_receipts import verify_payload_signature

                payload_data = {k: v for k, v in attestation.items() if k != "signature"}
                canonical_str = json.dumps(payload_data, sort_keys=True)
                return verify_payload_signature(canonical_str, sig)
            except Exception:
                return False

        return not is_prod
