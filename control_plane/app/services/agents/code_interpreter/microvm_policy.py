# Owner: agent-platform
import shutil
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings


MICROVM_PROVIDERS = {"firecracker", "gvisor"}
SENSITIVE_MOUNTS = (
    "/",
    "/boot",
    "/dev",
    "/etc",
    "/proc",
    "/root",
    "/sys",
    "/var/run/docker.sock",
)
SENSITIVE_PROC_PATHS = (
    "/proc/kcore",
    "/proc/keys",
    "/proc/sys",
    "/proc/sysrq-trigger",
)
METADATA_ENDPOINTS = (
    "169.254.169.254",
    "169.254.170.2",
    "metadata.google.internal",
    "100.100.100.200",
)


class SandboxIsolationProfile(BaseModel):
    provider: str
    kernel_isolation_level: str
    network_mode: str = Field(default="none")
    filesystem_mode: str = Field(default="read-only")
    sensitive_mounts_blocked: bool = Field(default=True)
    docker_sock_blocked: bool = Field(default=True)
    proc_restricted: bool = Field(default=True)
    metadata_endpoints_blocked: bool = Field(default=True)
    limits: dict[str, Any] = Field(default_factory=dict)


class MicroVMPolicy:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def resolve_provider_name(self) -> str:
        provider = self.settings.agent_code_sandbox_provider or "docker"
        
        # In production-like environments, block 'mock' if simulation is not allowed
        if provider == "mock" and not self.settings.agent_sandbox_allow_simulated_provider:
            raise RuntimeError("Mock sandbox is blocked in production-like environments")

        if provider == "mock":
            for candidate, enabled in (
                ("firecracker", self.settings.agent_code_sandbox_firecracker_enabled),
                ("gvisor", self.settings.agent_code_sandbox_gvisor_enabled),
                ("docker", self.settings.agent_code_sandbox_docker_enabled),
                ("wasm", self.settings.agent_code_sandbox_wasm_enabled),
            ):
                if enabled:
                    provider = candidate
                    break

        if self.settings.agent_code_sandbox_microvm_required and provider not in MICROVM_PROVIDERS:
            raise RuntimeError(f"Provider '{provider}' is blocked because MicroVM isolation is required")
        
        return provider

    def ensure_provider_enabled(self, provider: str) -> None:
        enabled_flags = {
            "docker": self.settings.agent_code_sandbox_docker_enabled,
            "wasm": self.settings.agent_code_sandbox_wasm_enabled,
            "firecracker": self.settings.agent_code_sandbox_firecracker_enabled,
            "gvisor": self.settings.agent_code_sandbox_gvisor_enabled,
            "mock": True,
        }
        enabled = enabled_flags.get(provider)
        if enabled is None:
            raise RuntimeError(f"Unsupported sandbox provider '{provider}'")
        if not enabled:
            raise RuntimeError(f"{provider} sandbox provider is disabled by feature flag")

    def is_fallback_allowed(self) -> bool:
        return not self.settings.agent_code_sandbox_microvm_required

    def is_provider_available(self, provider: str) -> bool:
        if provider == "mock":
            return True
        if provider == "docker":
            return shutil.which("docker") is not None
        if provider == "gvisor":
            return shutil.which("docker") is not None and shutil.which("runsc") is not None
        if provider == "firecracker":
            return shutil.which("firecracker") is not None
        if provider == "wasm":
            return False
        return False

    def build_isolation_profile(self, provider: str, limits: dict[str, Any]) -> SandboxIsolationProfile:
        kernel_levels = {
            "mock": "simulated",
            "docker": "container-shared-kernel",
            "gvisor": "user-space-kernel",
            "firecracker": "microvm",
            "wasm": "wasi-experimental",
        }
        filesystem_modes = {
            "mock": "simulated-read-only",
            "docker": "read-only-rootfs",
            "gvisor": "read-only-rootfs",
            "firecracker": "read-only-rootfs",
            "wasm": "read-only-rootfs",
        }
        return SandboxIsolationProfile(
            provider=provider,
            kernel_isolation_level=kernel_levels[provider],
            network_mode="none",
            filesystem_mode=filesystem_modes[provider],
            limits=limits,
        )

    def readiness_report(self) -> dict[str, Any]:
        provider = self.resolve_provider_name()
        configured = True
        available = self.is_provider_available(provider)
        healthy = available
        fallback_allowed = self.is_fallback_allowed()
        return {
            "provider": provider,
            "sandbox_provider_available": available,
            "provider_configured": configured,
            "provider_healthy": healthy,
            "microvm_required": self.settings.agent_code_sandbox_microvm_required,
            "fallback_allowed": fallback_allowed,
            "fallback_blocked": not fallback_allowed,
            "sensitive_mounts_blocked": True,
            "docker_sock_blocked": True,
            "proc_restricted": True,
            "metadata_endpoints_blocked": True,
            "metadata_endpoints": list(METADATA_ENDPOINTS),
        }
