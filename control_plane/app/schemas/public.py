import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublicSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    company: str | None = Field(default=None, max_length=120)
    plan_code: str = Field(default="free", min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")
    use_case: str | None = Field(default=None, max_length=500)

    @field_validator("full_name", "company", "use_case")
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        if value is not None and re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("control characters are not allowed")
        return value

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        normalized = value.lower()
        if normalized.count("@") != 1:
            raise ValueError("invalid email")
        local, domain = normalized.split("@", 1)
        if not local or not domain or "." not in domain:
            raise ValueError("invalid email")
        if len(local) > 64 or len(domain) > 253:
            raise ValueError("invalid email")
        if re.search(r"[\x00-\x20\x7f]", normalized):
            raise ValueError("invalid email")
        return normalized


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


class CapabilityItem(BaseModel):
    id: str
    name: str
    status: str
    capability_level: str
    limitations: str = ""
    docs_url: str = ""
    since_version: str = ""
    test_coverage: str | None = None


class CapabilitiesResponse(BaseModel):
    version: str
    local_appliance_mode: bool
    features: list[CapabilityItem]
    limitations: list[str]
    note: str
