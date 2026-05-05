from pydantic import BaseModel, Field


class PublicSignupRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    company: str | None = Field(default=None, max_length=120)
    plan_code: str = Field(default="free", min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")
    use_case: str | None = Field(default=None, max_length=500)


class PublicSignupResponse(BaseModel):
    client_id: str
    account_name: str
    plan_code: str
    plan_name: str
    api_key: str
    api_key_prefix: str
    portal_url: str
    api_base_url: str
    support_email: str
    next_steps: list[str]


class PortalUpgradeRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")


class WebhookPayload(BaseModel):
    invoice_id: str = Field(min_length=36, max_length=36)
    status: str = Field(pattern=r"^(paid|failed)$")
    payment_reference: str | None = Field(default=None, max_length=120)
