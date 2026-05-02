from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    billing_plan_id: UUID | None = None
    rate_limit_per_minute: int = Field(default=5, ge=1, le=120)
    daily_token_quota: int = Field(default=20000, ge=1000, le=10_000_000)
    monthly_token_quota: int = Field(default=300000, ge=1000, le=100_000_000)
    max_context_tokens: int = Field(default=32768, ge=512, le=131072)
    max_output_tokens: int = Field(default=2048, ge=128, le=4096)
    allowed_models: list[str] | None = None
    ip_allowlist: list[str] | None = None
    ip_blocklist: list[str] | None = None
    system_prompt: str | None = Field(default=None, max_length=5000)
    metadata_json: str | None = Field(default=None, max_length=5000)


class ClientPatch(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    is_blocked: bool | None = None
    billing_status: str | None = Field(default=None, pattern=r"^(active|past_due|suspended)$")
    billing_plan_id: UUID | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=120)
    daily_token_quota: int | None = Field(default=None, ge=1000, le=10_000_000)
    monthly_token_quota: int | None = Field(default=None, ge=1000, le=100_000_000)
    max_context_tokens: int | None = Field(default=None, ge=512, le=131072)
    max_output_tokens: int | None = Field(default=None, ge=128, le=4096)
    allowed_models: list[str] | None = None
    ip_allowlist: list[str] | None = None
    ip_blocklist: list[str] | None = None
    system_prompt: str | None = Field(default=None, max_length=5000)
    metadata_json: str | None = Field(default=None, max_length=5000)


class ClientRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_blocked: bool
    billing_status: str
    billing_plan_id: UUID | None
    rate_limit_per_minute: int
    daily_token_quota: int
    monthly_token_quota: int
    max_context_tokens: int
    max_output_tokens: int
    allowed_models_json: str | None
    ip_allowlist_json: str | None
    ip_blocklist_json: str | None
    system_prompt: str | None
    metadata_json: str | None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PaymentCreate(BaseModel):
    invoice_id: UUID
    amount: float = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    payment_method: str = Field(default="manual_pix", min_length=3, max_length=32)
    payment_reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    paid_at: datetime | None = None


class PaymentRead(BaseModel):
    id: UUID
    invoice_id: UUID
    client_id: UUID
    status: str
    amount: float
    currency: str
    payment_method: str
    payment_reference: str | None
    note: str | None
    paid_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestCommand(BaseModel):
    id: str
    name: str
    description: str
    command: str


class TestRunRequest(BaseModel):
    command_id: str


class TestRunResponse(BaseModel):
    run_id: str
    command_id: str
    status: str
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    duration_seconds: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreate(BaseModel):
    client_id: UUID
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] | None = Field(default=None)


class ApiKeyCreated(BaseModel):
    id: UUID
    client_id: UUID
    name: str
    key_prefix: str
    api_key: str
    scopes: list[str] | None = None
    created_at: datetime


class ApiKeyRotateResponse(BaseModel):
    rotated_from_id: UUID
    revoked_at: datetime
    api_key: ApiKeyCreated


class ModelReloadResponse(BaseModel):
    status: str
    detail: str


class BillingPlanCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    rate_limit_per_minute: int = Field(ge=1, le=10000)
    daily_token_quota: int = Field(ge=1000, le=1_000_000_000)
    monthly_token_quota: int = Field(ge=1000, le=10_000_000_000)
    max_output_tokens: int = Field(ge=1, le=8192)
    allow_streaming: bool = True
    is_active: bool = True
    allowed_models: list[str] | None = None


class BillingPlanPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=10000)
    daily_token_quota: int | None = Field(default=None, ge=1000, le=1_000_000_000)
    monthly_token_quota: int | None = Field(default=None, ge=1000, le=10_000_000_000)
    max_output_tokens: int | None = Field(default=None, ge=1, le=8192)
    allow_streaming: bool | None = None
    is_active: bool | None = None
    allowed_models: list[str] | None = None


class BillingPlanRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    rate_limit_per_minute: int
    daily_token_quota: int
    monthly_token_quota: int
    max_output_tokens: int
    allow_streaming: bool
    is_active: bool
    allowed_models_json: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientBillingPlanPatch(BaseModel):
    billing_plan_id: UUID


class PricingRuleRead(BaseModel):
    id: UUID
    billing_plan_id: UUID
    currency: str
    monthly_price: float
    overage_price_per_1k_tokens: float
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BillingPlanModelsPatch(BaseModel):
    allowed_models: list[str] = Field(default_factory=list)


class ModelRegistryCreate(BaseModel):
    model_id: str = Field(min_length=1, max_length=255)
    model_alias: str | None = Field(default=None, min_length=1, max_length=128)
    inference_backend_id: UUID | None = None
    provider: str = Field(default="llama.cpp", pattern=r"^(llama\.cpp|ollama|vllm)$")
    model_file: str = Field(min_length=1, max_length=255)
    context_length: int = Field(default=4096, ge=512, le=131072)
    is_active: bool = True
    is_default: bool = False
    status: str = Field(default="configured", min_length=2, max_length=32)
    prompt_template: str | None = Field(default=None, max_length=10000)
    metadata_json: str | None = None
    backend_routes: list["BackendRouteInput"] = Field(default_factory=list)


class ModelRegistryPatch(BaseModel):
    model_alias: str | None = Field(default=None, min_length=1, max_length=128)
    inference_backend_id: UUID | None = None
    provider: str | None = Field(default=None, pattern=r"^(llama\.cpp|ollama|vllm)$")
    model_file: str | None = Field(default=None, min_length=1, max_length=255)
    context_length: int | None = Field(default=None, ge=512, le=131072)
    is_default: bool | None = None
    status: str | None = Field(default=None, min_length=2, max_length=32)
    prompt_template: str | None = Field(default=None, max_length=10000)
    metadata_json: str | None = None
    backend_routes: list["BackendRouteInput"] | None = None


class InferenceBackendCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider: str = Field(pattern=r"^(llama\.cpp|ollama|vllm)$")
    backend_url: str = Field(min_length=8, max_length=255)
    healthcheck_path: str = Field(default="/health", min_length=1, max_length=64)
    is_active: bool = True
    is_default: bool = False
    status: str = Field(default="configured", min_length=2, max_length=32)
    max_parallel_requests: int = Field(default=1, ge=1, le=64)
    metadata_json: str | None = None


class InferenceBackendPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    provider: str | None = Field(default=None, pattern=r"^(llama\.cpp|ollama|vllm)$")
    backend_url: str | None = Field(default=None, min_length=8, max_length=255)
    healthcheck_path: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None
    is_default: bool | None = None
    status: str | None = Field(default=None, min_length=2, max_length=32)
    max_parallel_requests: int | None = Field(default=None, ge=1, le=64)
    metadata_json: str | None = None


class BackendRouteInput(BaseModel):
    inference_backend_id: UUID
    priority: int = Field(default=100, ge=1, le=10000)
    weight: int = Field(default=100, ge=1, le=10000)
    state: str = Field(default="healthy", pattern=r"^(healthy|degraded|unhealthy|disabled)$")


class BackendRoutePatch(BaseModel):
    priority: int | None = Field(default=None, ge=1, le=10000)
    weight: int | None = Field(default=None, ge=1, le=10000)
    state: str | None = Field(default=None, pattern=r"^(healthy|degraded|unhealthy|disabled)$")


class InvoiceGenerateRequest(BaseModel):
    client_id: UUID | None = None
    due_in_days: int = Field(default=7, ge=0, le=90)
    payment_method: str = Field(default="manual_pix", min_length=3, max_length=32)
    payment_instructions: str | None = Field(default=None, max_length=1000)
    force: bool = False


class InvoiceMarkPaidRequest(BaseModel):
    amount_paid: float | None = Field(default=None, ge=0)
    payment_method: str = Field(default="manual_pix", min_length=3, max_length=32)
    payment_reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=1000)
    paid_at: datetime | None = None
