import time
from app.services.sandbox.base import (
    SandboxProvider, 
    SandboxLevel, 
    SandboxExecutionRequest, 
    SandboxExecutionResult
)


class NoopSandboxProvider(SandboxProvider):
    """
    Provider that does not provide isolation. 
    Only used for simulation or local trusted execution.
    """
    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        start_time = time.time()
        # In NOOP, we don't actually execute for security safety unless explicitly enabled in settings
        # This acts as a simulator by default
        return SandboxExecutionResult(
            status="success",
            exit_code=0,
            stdout=b"Simulation: Command executed successfully in NOOP sandbox.",
            execution_time=time.time() - start_time,
            provider_name="noop"
        )

    def get_level(self) -> SandboxLevel:
        return SandboxLevel.PROCESS

    def is_available(self) -> bool:
        return True


class WasiSandboxProvider(SandboxProvider):
    """Placeholder for Wasmtime/WASI provider."""
    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        return SandboxExecutionResult(status="blocked", reason="WASI Provider not configured", provider_name="wasi-placeholder")
    
    def get_level(self) -> SandboxLevel:
        return SandboxLevel.WASI
    
    def is_available(self) -> bool:
        return False


class GVisorSandboxProvider(SandboxProvider):
    """Placeholder for gVisor/runsc provider."""
    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        return SandboxExecutionResult(status="blocked", reason="gVisor Provider not configured", provider_name="gvisor-placeholder")
    
    def get_level(self) -> SandboxLevel:
        return SandboxLevel.CONTAINER
    
    def is_available(self) -> bool:
        return False


class FirecrackerSandboxProvider(SandboxProvider):
    """Placeholder for Firecracker MicroVM provider."""
    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        return SandboxExecutionResult(status="blocked", reason="Firecracker Provider not configured", provider_name="firecracker-placeholder")
    
    def get_level(self) -> SandboxLevel:
        return SandboxLevel.MICROVM
    
    def is_available(self) -> bool:
        return False
