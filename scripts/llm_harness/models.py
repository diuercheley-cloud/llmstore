from typing import Any

from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    id: str
    task: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None
    output: str | None = None
    trace_id: str | None = None
    trace_hash: str | None = None
    duration: float = 0.0
    total_duration_ms: float = 0.0
    command_duration_ms: float = 0.0
    agent_latency_ms: float = 0.0
    retry_count: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0
    llm_provider: str = ""
    llm_model: str = ""
    estimated_cost: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class HarnessEvent(BaseModel):
    event: str
    trace_id: str | None = None
    action_type: str | None = None
    step: int | None = None
    status: str | None = None
    duration_ms: int = 0
    agent_latency_ms: int = 0
    message: str | None = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any]
    result: Any | None = None


class AgentTrace(BaseModel):
    agent_id: str
    task_id: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    start_time: str
    end_time: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0


class PatchResult(BaseModel):
    success: bool
    changed_files: list[str] = Field(default_factory=list)
    error: str | None = None
    stderr: str | None = None
    mode: str = "apply"  # apply | check
    diff_sha256: str | None = None
