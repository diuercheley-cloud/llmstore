from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1, max_length=20000)


class ChatCompletionRequest(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    messages: list[ChatMessage] = Field(min_length=1, max_length=128)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    stream: bool = False
    safety_profile: Literal["default", "strict", "relaxed"] = "default"
    include_reasoning: bool = False

    @model_validator(mode="after")
    def ensure_non_empty_user_content(self) -> "ChatCompletionRequest":
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("at least one user message is required")
        return self


class CompletionRequest(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=1, max_length=20000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    stream: bool = False
    safety_profile: Literal["default", "strict", "relaxed"] = "default"


class PortalTestChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)
    model: str | None = Field(default=None, min_length=1, max_length=255)
    max_tokens: int | None = Field(default=128, ge=1, le=1024)


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "local"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelCard]


class JobAcceptedResponse(BaseModel):
    id: UUID
    status: Literal["queued"]
    endpoint: str
    requested_model: str
    resolved_model: str


class GenerationJobResponse(BaseModel):
    id: UUID
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    endpoint: str
    requested_model: str
    resolved_model: str
    backend_name: str | None = None
    attempts: int
    fallback_used: bool
    prompt_tokens_estimated: int
    completion_tokens_estimated: int
    estimated_cost_usd: float
    max_tokens_requested: int
    response: dict[str, Any] | None = None
    error: str | None = None
    backend_errors: list[dict[str, Any]] = Field(default_factory=list)
    queued_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    cancelled_at: str | None = None
    created_at: str
    updated_at: str


class OnboardingEventRequest(BaseModel):
    event: str = Field(min_length=1, max_length=100)
