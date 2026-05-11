import os
from functools import lru_cache
from pathlib import Path
from time import time

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_version() -> str:
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="local-llm-inference-stack", alias="PROJECT_NAME")
    project_version: str = Field(default_factory=_get_version)
    start_time: float = Field(default_factory=time)
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

    # Queue Settings
    queue_admin_max_waiting: int = Field(default=20, alias="QUEUE_ADMIN_MAX_WAITING")
    queue_admin_max_active: int = Field(default=10, alias="QUEUE_ADMIN_MAX_ACTIVE")
    queue_admin_timeout: int = Field(default=60, alias="QUEUE_ADMIN_TIMEOUT")
    queue_premium_max_waiting: int = Field(default=15, alias="QUEUE_PREMIUM_MAX_WAITING")
    queue_premium_max_active: int = Field(default=5, alias="QUEUE_PREMIUM_MAX_ACTIVE")
    queue_premium_timeout: int = Field(default=30, alias="QUEUE_PREMIUM_TIMEOUT")
    queue_basic_max_waiting: int = Field(default=10, alias="QUEUE_BASIC_MAX_WAITING")
    queue_basic_max_active: int = Field(default=2, alias="QUEUE_BASIC_MAX_ACTIVE")
    queue_basic_timeout: int = Field(default=20, alias="QUEUE_BASIC_TIMEOUT")
    queue_free_max_waiting: int = Field(default=5, alias="QUEUE_FREE_MAX_WAITING")
    queue_free_max_active: int = Field(default=1, alias="QUEUE_FREE_MAX_ACTIVE")
    queue_free_timeout: int = Field(default=15, alias="QUEUE_FREE_TIMEOUT")

    circuit_breaker_failure_threshold: int = Field(default=3, alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_seconds: int = Field(default=20, alias="CIRCUIT_BREAKER_RECOVERY_SECONDS")
    response_cache_enabled: bool = Field(default=True, alias="RESPONSE_CACHE_ENABLED")
    response_cache_ttl_seconds: int = Field(default=3600, alias="RESPONSE_CACHE_TTL_SECONDS")
    semantic_cache_enabled: bool = Field(default=False, alias="SEMANTIC_CACHE_ENABLED")
    local_billing_mode: str = Field(default="manual", alias="LOCAL_BILLING_MODE")
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
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
    localhost_mode: bool = Field(default=False, alias="LOCALHOST_MODE")
    local_appliance_mode: bool = Field(default=False, alias="LOCAL_APPLIANCE_MODE")
    app_public_url: str = Field(default="http://localhost:18080", alias="APP_PUBLIC_URL")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")
    admin_base_url: str = Field(default="", alias="ADMIN_BASE_URL")
    client_portal_base_url: str = Field(default="", alias="CLIENT_PORTAL_BASE_URL")
    docs_base_url: str = Field(default="", alias="DOCS_BASE_URL")
    api_base_url: str = Field(default="", alias="API_BASE_URL")
    test_tools_enabled: bool = Field(default=False, alias="TEST_TOOLS_ENABLED")
    jwt_secret: str = Field(default="change-me-at-all-costs", alias="JWT_SECRET")
    max_request_body_size_bytes: int = Field(default=1024 * 1024 * 5, alias="MAX_REQUEST_BODY_SIZE_BYTES") # 5MB
    inference_max_context_tokens: int = Field(default=4096, alias="INFERENCE_MAX_CONTEXT_TOKENS")
    inference_max_completion_tokens: int = Field(default=512, alias="INFERENCE_MAX_COMPLETION_TOKENS")
    inference_max_system_chars: int = Field(default=2500, alias="INFERENCE_MAX_SYSTEM_CHARS")
    inference_max_history_messages: int = Field(default=8, alias="INFERENCE_MAX_HISTORY_MESSAGES")
    
    # TTS Settings
    tts_enabled: bool = Field(default=True, alias="TTS_ENABLED")
    
    # Embeddings Settings
    embeddings_enabled: bool = Field(default=True, alias="EMBEDDINGS_ENABLED")
    embeddings_backend: str = Field(default="mock", alias="EMBEDDINGS_BACKEND")
    default_embedding_model: str = Field(default="text-embedding-3-small", alias="DEFAULT_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=384, alias="EMBEDDING_DIMENSIONS")

    # Backend Settings
    mock_backend_enabled: bool = Field(default=False, alias="MOCK_BACKEND_ENABLED")
    
    # RAG Settings
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    rag_storage_dir: str = Field(default="./data/rag_uploads", alias="RAG_STORAGE_DIR")
    rag_max_file_mb: int = Field(default=25, alias="RAG_MAX_FILE_MB")
    rag_chunk_size: int = Field(default=1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, alias="RAG_CHUNK_OVERLAP")
    rag_top_k_default: int = Field(default=5, alias="RAG_TOP_K_DEFAULT")
    rag_embedding_provider: str = Field(default="local", alias="RAG_EMBEDDING_PROVIDER")
    rag_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="RAG_EMBEDDING_MODEL")

    @model_validator(mode="after")
    def validate_appliance_mode(self) -> "Settings":
        if self.local_appliance_mode:
            self.localhost_mode = True
            self.local_billing_mode = "manual"
            self.public_exposure = False
            self.public_signup_enabled = False
            
            # Warn if using default tokens in appliance mode
            # (In a real scenario, we might want to raise an error, 
            # but for now we'll rely on health checks to show warnings)
            pass

        if self.localhost_mode:
            # Default to localhost if not set
            if not self.public_base_url:
                self.public_base_url = self.app_public_url.rstrip("/")
            if not self.admin_base_url:
                self.admin_base_url = f"{self.public_base_url}/admin"
            if not self.client_portal_base_url:
                self.client_portal_base_url = f"{self.public_base_url}/client-portal"
            if not self.docs_base_url:
                self.docs_base_url = f"{self.public_base_url}/docs"
            if not self.api_base_url:
                self.api_base_url = f"{self.public_base_url}/v1"
            
            # Ensure app_public_url matches public_base_url for consistency
            self.app_public_url = self.public_base_url
            
        return self

    @property
    def cors_origins(self) -> list[str]:
        raw_origins = [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]
        origins = []

        # Validate and sanitize origins
        for origin in raw_origins:
            if origin == "*":
                if self.local_appliance_mode:
                    # Strictly forbid '*' in appliance mode as default/explicit
                    continue
                return ["*"]
            
            # Simple validation: must start with http:// or https://
            if origin.startswith(("http://", "https://")):
                origins.append(origin.rstrip("/"))

        if self.localhost_mode or self.local_appliance_mode:
            # Add secure defaults for local operation
            # Use public_base_url if it's a valid origin
            if self.public_base_url.startswith(("http://", "https://")):
                origin = self.public_base_url.rstrip("/")
                if origin not in origins:
                    origins.append(origin)

            # Standard localhost variants
            localhost_variants = [
                "http://localhost",
                "http://127.0.0.1",
                "http://0.0.0.0",
            ]
            
            # If we know the port, add variants with port
            port_match = None
            if self.public_base_url:
                import re
                match = re.search(r":(\d+)", self.public_base_url)
                if match:
                    port_match = match.group(1)

            for base in localhost_variants:
                if base not in origins:
                    origins.append(base)
                if port_match:
                    with_port = f"{base}:{port_match}"
                    if with_port not in origins:
                        origins.append(with_port)
                
                # Always include common dev ports if in localhost_mode but not necessarily appliance
                if not self.local_appliance_mode:
                    for p in ["18080", "3000", "3001"]:
                        with_common_port = f"{base}:{p}"
                        if with_common_port not in origins:
                            origins.append(with_common_port)

        return sorted(list(set(origins)))

    @property
    def cors_warnings(self) -> list[dict[str, str]]:
        warnings = []
        raw_origins = [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]
        
        if self.local_appliance_mode:
            if not raw_origins:
                warnings.append({
                    "id": "CORS_EMPTY_APPLIANCE",
                    "severity": "medium",
                    "message": "CORS_ALLOW_ORIGINS is empty in appliance mode. Using secure local defaults."
                })
            if "*" in raw_origins:
                warnings.append({
                    "id": "CORS_WILDCARD_APPLIANCE",
                    "severity": "high",
                    "message": "Wildcard '*' CORS is not allowed in LOCAL_APPLIANCE_MODE and was ignored."
                })
        
        # Check for invalid origins
        for origin in raw_origins:
            if origin != "*" and not origin.startswith(("http://", "https://")):
                warnings.append({
                    "id": "CORS_INVALID_ORIGIN",
                    "severity": "low",
                    "message": f"Invalid CORS origin ignored: {origin}. Must start with http:// or https://"
                })
                
        return warnings



@lru_cache
def get_settings() -> Settings:
    return Settings()
