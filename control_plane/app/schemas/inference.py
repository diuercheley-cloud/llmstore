import time
from typing import Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ChatContentPart(BaseModel):
    type: Literal["text", "image_url"]
    text: str | None = None
    image_url: dict[str, Any] | None = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, list[ChatContentPart]]


class ChatCompletionRequest(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    messages: list[ChatMessage] = Field(min_length=1, max_length=128)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=1000000)
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
    max_tokens: int | None = Field(default=None, ge=1, le=1000000)
    stream: bool = False
    safety_profile: Literal["default", "strict", "relaxed"] = "default"


class PortalTestChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)
    model: str | None = Field(default=None, min_length=1, max_length=255)
    max_tokens: int | None = Field(default=128, ge=1, le=32768)


class ModelCapabilities(BaseModel):
    chat: bool = True
    streaming: bool = True
    embeddings: bool = False
    responses: bool = True
    tools: bool = False


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "local"
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    enabled: bool = True
    backend_status: str = "unknown"
    production_ready: bool = False
    local_ready: bool = False
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider_info: dict[str, Any] | None = Field(default=None, description="Provider capabilities from multi-provider layer")


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


class ChatCompletionChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatCompletionChoiceMessage
    finish_reason: str | None = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int | None = 0
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo


class EmbeddingsRequest(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    input: Union[str, list[str]] = Field(min_length=1)
    encoding_format: Literal["float", "base64"] = "float"


class EmbeddingData(BaseModel):
    object: str = "embedding"
    index: int
    embedding: list[float]


class EmbeddingsResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingData]
    model: str
    usage: UsageInfo


class ResponseInputTextPart(BaseModel):
    type: Literal["text", "input_text", "output_text"] = "text"
    text: str


class ResponseInputMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: Union[str, list[ResponseInputTextPart]]


class ResponseOutputText(BaseModel):
    type: Literal["output_text"] = "output_text"
    text: str


class ResponseOutputMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: list[ResponseOutputText]


class ResponseOutput(BaseModel):
    type: Literal["message"] = "message"
    message: ResponseOutputMessage


class ResponsesResponse(BaseModel):
    id: str
    object: str = "response"
    created_at: int
    status: str = "completed"
    model: str
    output: list[ResponseOutput]
    output_text: str
    usage: UsageInfo
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResponsesRequest(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    input: Union[str, list[Union[str, ResponseInputMessage]]]
    instructions: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_output_tokens: int | None = Field(default=None, ge=1, le=1000000)
    stream: bool = False
    tools: list[Any] | None = None
    tool_choice: Union[str, dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
