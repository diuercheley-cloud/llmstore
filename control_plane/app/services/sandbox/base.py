from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SandboxLevel(str, Enum):
    NONE = "none"
    PROCESS = "process"
    WASI = "wasi"
    CONTAINER = "container"
    MICROVM = "microvm"


class SandboxPolicy(BaseModel):
    required_level: SandboxLevel = SandboxLevel.NONE
    allow_network: bool = False
    allow_filesystem: bool = False
    read_only_paths: list[str] = Field(default_factory=list)
    write_paths: list[str] = Field(default_factory=list)
    timeout_seconds: int = 30
    memory_limit_mb: int = 128
    cpu_limit_cores: float = 1.0


class SandboxExecutionRequest(BaseModel):
    command: list[str]
    env: dict[str, str] = Field(default_factory=dict)
    input_data: bytes | None = None
    policy: SandboxPolicy


class SandboxExecutionResult(BaseModel):
    status: str  # success, failure, timeout, blocked
    reason: str | None = None
    exit_code: int = 0
    stdout: bytes = b""
    stderr: bytes = b""
    execution_time: float = 0.0
    resource_usage: dict[str, Any] = Field(default_factory=dict)
    provider_name: str


class SandboxProvider(ABC):
    @abstractmethod
    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Execute a command in the sandbox."""
        pass

    @abstractmethod
    def get_level(self) -> SandboxLevel:
        """Return the sandbox level supported by this provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available in the current environment."""
        pass
