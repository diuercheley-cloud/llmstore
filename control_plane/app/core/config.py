from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="local-llm-inference-stack", alias="PROJECT_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    control_plane_host: str = Field(default="0.0.0.0", alias="CONTROL_PLANE_HOST")
    control_plane_port: int = Field(default=8080, alias="CONTROL_PLANE_PORT")
    admin_token: str = Field(alias="ADMIN_TOKEN")
    admin_read_token: str | None = Field(default=None, alias="ADMIN_READ_TOKEN")
    admin_write_token: str | None = Field(default=None, alias="ADMIN_WRITE_TOKEN")
    admin_super_token: str | None = Field(default=None, alias="ADMIN_SUPER_TOKEN")
    admin_tests_rate_limit_enabled: bool = Field(default=True, alias="ADMIN_TESTS_RATE_LIMIT_ENABLED")
    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")
    public_exposure: bool = Field(default=False, alias="PUBLIC_EXPOSURE")
    public_signup_enabled: bool = Field(default=True, alias="PUBLIC_SIGNUP_ENABLED")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")
    public_brand_name: str = Field(default="LLM Inference Stack Cloud", alias="PUBLIC_BRAND_NAME")
    public_support_email: str = Field(default="sales@example.com", alias="PUBLIC_SUPPORT_EMAIL")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    data_plane_base_url: str = Field(alias="DATA_PLANE_BASE_URL")
    ollama_base_url: str = Field(default="http://data-plane-ollama:11434", alias="OLLAMA_BASE_URL")
    lmstudio_enabled: bool = Field(default=True, alias="LMSTUDIO_ENABLED")
    lmstudio_base_url: str = Field(default="http://192.168.101.1:1234/v1", alias="LMSTUDIO_BASE_URL")
    lmstudio_api_key: str = Field(default="", alias="LMSTUDIO_API_KEY")
    lmstudio_default_model: str = Field(default="nvidia/nemotron-3-nano-4b", alias="LMSTUDIO_DEFAULT_MODEL")
    data_plane_timeout_seconds: int = Field(default=120, alias="DATA_PLANE_TIMEOUT_SECONDS")
    request_timeout_seconds: int = Field(default=120, alias="REQUEST_TIMEOUT_SECONDS")
    queue_timeout_seconds: int = Field(default=30, alias="QUEUE_TIMEOUT_SECONDS")
    max_concurrent_generations: int = Field(default=1, alias="MAX_CONCURRENT_GENERATIONS")
    max_queue_size: int = Field(default=8, alias="MAX_QUEUE_SIZE")
    async_job_queue_name: str = Field(default="generation_jobs:queue", alias="ASYNC_JOB_QUEUE_NAME")
    async_worker_block_seconds: int = Field(default=5, alias="ASYNC_WORKER_BLOCK_SECONDS")
    max_context_tokens: int = Field(default=32768, alias="MAX_CONTEXT_TOKENS")
    max_input_tokens: int = Field(default=32768, alias="MAX_INPUT_TOKENS")
    default_max_tokens: int = Field(default=512, alias="DEFAULT_MAX_TOKENS")
    max_completion_tokens: int = Field(
        default=2048,
        validation_alias=AliasChoices("MAX_COMPLETION_TOKENS", "MAX_TOKENS_LIMIT"),
    )
    default_temperature: float = Field(default=0.7, alias="DEFAULT_TEMPERATURE")
    max_temperature: float = Field(default=1.5, alias="MAX_TEMPERATURE")
    default_top_p: float = Field(default=0.95, alias="DEFAULT_TOP_P")
    max_top_p: float = Field(default=1.0, alias="MAX_TOP_P")
    retry_attempts: int = Field(default=2, alias="RETRY_ATTEMPTS")
    retry_backoff_seconds: float = Field(default=1.0, alias="RETRY_BACKOFF_SECONDS")
    circuit_breaker_failure_threshold: int = Field(default=3, alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_seconds: int = Field(default=20, alias="CIRCUIT_BREAKER_RECOVERY_SECONDS")
    response_cache_enabled: bool = Field(default=True, alias="RESPONSE_CACHE_ENABLED")
    response_cache_ttl_seconds: int = Field(default=3600, alias="RESPONSE_CACHE_TTL_SECONDS")
    semantic_cache_enabled: bool = Field(default=False, alias="SEMANTIC_CACHE_ENABLED")
    billing_invoice_day: int = Field(default=1, alias="BILLING_INVOICE_DAY")
    billing_due_days: int = Field(default=7, alias="BILLING_DUE_DAYS")
    billing_suspend_after_days: int = Field(default=15, alias="BILLING_SUSPEND_AFTER_DAYS")
    demo_client_name: str = Field(default="demo-client", alias="DEMO_CLIENT_NAME")
    demo_rate_limit_per_minute: int = Field(default=5, alias="DEMO_RATE_LIMIT_PER_MINUTE")
    demo_daily_token_quota: int = Field(default=20000, alias="DEMO_DAILY_TOKEN_QUOTA")
    demo_monthly_token_quota: int = Field(default=300000, alias="DEMO_MONTHLY_TOKEN_QUOTA")
    model_id: str = Field(default="unsloth/gemma-4-E4B-it-GGUF", alias="MODEL_ID")
    model_file: str = Field(default="gemma-4-E4B-it-Q4_K_M.gguf", alias="MODEL_FILE")
    models_dir: str = Field(default="/models", alias="MODELS_DIR")
    public_api_enabled: bool = Field(default=False, alias="PUBLIC_API_ENABLED")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_public_url: str = Field(default="http://localhost:18080", alias="APP_PUBLIC_URL")
    test_tools_enabled: bool = Field(default=False, alias="TEST_TOOLS_ENABLED")
    jwt_secret: str = Field(default="change-me-at-all-costs", alias="JWT_SECRET")
    max_request_body_size_bytes: int = Field(default=1024 * 1024 * 5, alias="MAX_REQUEST_BODY_SIZE_BYTES") # 5MB

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
