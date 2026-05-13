from pydantic import BaseModel, Field


class ProviderCapabilities(BaseModel):
    chat: bool = False
    streaming: bool = False
    responses: bool = False
    embeddings: bool = False
    tools: bool = False
    vision: bool = False
    json_mode: bool = False
    max_context_tokens: int = 0
    pricing_configured: bool = False


class ProviderConfig(BaseModel):
    provider_id: str
    provider_type: str
    enabled: bool = False
    configured: bool = False
    base_url: str | None = None
    models: list[str] = Field(default_factory=list)


class ProviderHealth(BaseModel):
    provider_id: str
    enabled: bool
    configured: bool
    healthy: bool | None = None
    last_error_sanitized: str | None = None
    latency_ms: float | None = None


class ProviderStatus(BaseModel):
    provider_id: str
    provider_type: str
    enabled: bool
    configured: bool
    healthy: bool | None = None
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    models: list[str] = Field(default_factory=list)
    last_error_sanitized: str | None = None


class ProviderSummary(BaseModel):
    provider_id: str
    provider_type: str
    enabled: bool
    configured: bool
    healthy: bool | None = None
