from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    local_billing_mode: str = Field(default="manual", alias="LOCAL_BILLING_MODE")
    billing_invoice_day: int = Field(default=1, alias="BILLING_INVOICE_DAY")
    billing_due_days: int = Field(default=7, alias="BILLING_DUE_DAYS")
    billing_suspend_after_days: int = Field(default=15, alias="BILLING_SUSPEND_AFTER_DAYS")

    payment_processing_enabled: bool = Field(default=False, alias="PAYMENT_PROCESSING_ENABLED")
    payment_provider: str = Field(default="mock", alias="PAYMENT_PROVIDER")
    payment_webhook_secret: str = Field(default="", alias="PAYMENT_WEBHOOK_SECRET")
    payment_real_enabled: bool = Field(default=False, alias="PAYMENT_REAL_ENABLED")

    stripe_payment_enabled: bool = Field(default=False, alias="STRIPE_PAYMENT_ENABLED")
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_api_key: str = Field(default="", alias="STRIPE_API_KEY")

    pix_payment_enabled: bool = Field(default=False, alias="PIX_PAYMENT_ENABLED")
    card_payment_enabled: bool = Field(default=False, alias="CARD_PAYMENT_ENABLED")
    mercadopago_access_token: str = Field(default="", alias="MERCADOPAGO_ACCESS_TOKEN")
    asaas_api_key: str = Field(default="", alias="ASAAS_API_KEY")
