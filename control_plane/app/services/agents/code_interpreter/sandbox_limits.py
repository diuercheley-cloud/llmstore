# Owner: agent-platform
from pydantic import BaseModel, Field


class ExecutionLimits(BaseModel):
    timeout_seconds: int = Field(default=10, ge=1, le=300)
    memory_limit_mb: int = Field(default=256, ge=64, le=2048)
    cpu_limit_seconds: int = Field(default=10, ge=1, le=300)
    max_output_size_bytes: int = Field(default=64 * 1024, ge=1024, le=10 * 1024 * 1024)
    max_artifact_size_bytes: int = Field(default=2 * 1024 * 1024, ge=1024, le=32 * 1024 * 1024)
    max_artifacts: int = Field(default=4, ge=0, le=32)
    writable_tmp_size_mb: int = Field(default=16, ge=1, le=256)


class SandboxLimits:
    def get_defaults(self) -> ExecutionLimits:
        return ExecutionLimits()
