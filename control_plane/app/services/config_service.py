from typing import Any, Dict, Optional, Self, Tuple, List
from pydantic import AliasChoices, Field, model_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
from pathlib import Path
import os
from time import time

from control_plane.app.core.config_agent import AgentSettings
from control_plane.app.core.config_commercial import CommercialSettings
from control_plane.app.core.cors import resolve_cors_origins

def _get_version() -> str:
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


def _read_dotenv_keys() -> set[str]:
    keys: set[str] = set()
    for p in (Path(".env"), Path(".env.local")):
        try:
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            keys.add(line.split("=", 1)[0].strip())
        except Exception:
            pass
    return keys

class BaseAppConfig(AgentSettings, CommercialSettings):
    """
    Unified configuration base class.
    Precedence: 
    1. Environment variables
    2. YAML configuration file (defined by PROFILE)
    3. Defaults defined in the model
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    multimodal_enabled: bool = Field(default=False, alias="MULTIMODAL_ENABLED")
    vision_input_enabled: bool = Field(default=False, alias="VISION_INPUT_ENABLED")
    image_generation_enabled: bool = Field(default=False, alias="IMAGE_GENERATION_ENABLED")
    speech_to_text_enabled: bool = Field(default=False, alias="SPEECH_TO_TEXT_ENABLED")
    realtime_audio_enabled: bool = Field(default=False, alias="REALTIME_AUDIO_ENABLED")
    document_vision_enabled: bool = Field(default=False, alias="DOCUMENT_VISION_ENABLED")
    mlops_enabled: bool = Field(default=False, alias="MLOPS_ENABLED")
    fine_tuning_enabled: bool = Field(default=False, alias="FINE_TUNING_ENABLED")
    experiment_tracking_enabled: bool = Field(default=False, alias="EXPERIMENT_TRACKING_ENABLED")
    mlflow_integration_enabled: bool = Field(default=False, alias="MLFLOW_INTEGRATION_ENABLED")
    wandb_integration_enabled: bool = Field(default=False, alias="WANDB_INTEGRATION_ENABLED")
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-east-1-aws", alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="agent-memory", alias="PINECONE_INDEX_NAME")
    agentic_router_v2_enabled: bool = Field(default=False, alias="AGENTIC_ROUTER_V2_ENABLED")
    nats_url: str = Field(default="nats://localhost:4222", alias="NATS_URL")
    nats_trigger_enabled: bool = Field(default=False, alias="NATS_TRIGGER_ENABLED")
    pulsar_url: str = Field(default="pulsar://localhost:6650", alias="PULSAR_URL")
    pulsar_trigger_enabled: bool = Field(default=False, alias="PULSAR_TRIGGER_ENABLED")
    multi_cluster_enabled: bool = Field(default=False, alias="MULTI_CLUSTER_ENABLED")
    otlp_export_enabled: bool = Field(default=False, alias="OTLP_EXPORT_ENABLED")
    jaeger_export_enabled: bool = Field(default=False, alias="JAEGER_EXPORT_ENABLED")
    zipkin_export_enabled: bool = Field(default=False, alias="ZIPKIN_EXPORT_ENABLED")
    platform_profile: str = Field(default="appliance", alias="PLATFORM_PROFILE")
    email_provider: str = Field(default="mock", alias="EMAIL_PROVIDER")
    push_provider: str = Field(default="mock", alias="PUSH_PROVIDER")
    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    sendgrid_api_key: str = Field(default="", alias="SENDGRID_API_KEY")
    fcm_api_key: str = Field(default="", alias="FCM_API_KEY")
    apns_key_id: str = Field(default="", alias="APNS_KEY_ID")
    plugin_runtime_enabled: bool = Field(default=False, alias="PLUGIN_RUNTIME_ENABLED")
    plugin_signature_required: bool = Field(default=False, alias="PLUGIN_SIGNATURE_REQUIRED")
    prompt_templates_enabled: bool = Field(default=False, alias="PROMPT_TEMPLATES_ENABLED")
    prompt_template_playground_enabled: bool = Field(default=False, alias="PROMPT_TEMPLATE_PLAYGROUND_ENABLED")
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
    rbac_admin_enabled: bool = Field(default=True, alias="RBAC_ADMIN_ENABLED")
    admin_tests_rate_limit_enabled: bool = Field(default=True, alias="ADMIN_TESTS_RATE_LIMIT_ENABLED")
    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")
    public_exposure: bool = Field(default=False, alias="PUBLIC_EXPOSURE")
    public_signup_enabled: bool = Field(default=True, alias="PUBLIC_SIGNUP_ENABLED")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")
    public_brand_name: str = Field(default="LLM Inference Stack Cloud", alias="PUBLIC_BRAND_NAME")
    public_support_email: str = Field(default="sales@example.com", alias="PUBLIC_SUPPORT_EMAIL")
    public_analytics_provider: str = Field(default="none", alias="PUBLIC_ANALYTICS_PROVIDER")
    public_plausible_domain: str = Field(default="", alias="PUBLIC_PLAUSIBLE_DOMAIN")
    public_plausible_src: str = Field(default="https://plausible.io/js/script.js", alias="PUBLIC_PLAUSIBLE_SRC")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    data_plane_base_url: str = Field(alias="DATA_PLANE_BASE_URL")
    ollama_base_url: str = Field(default="http://data-plane-ollama:11434", alias="OLLAMA_BASE_URL")
    lmstudio_enabled: bool = Field(default=False, alias="LMSTUDIO_ENABLED")
    lmstudio_base_url: str = Field(default="http://192.168.101.1:1234/v1", alias="LMSTUDIO_BASE_URL")
    lmstudio_api_key: str = Field(default="lm-studio", alias="LMSTUDIO_API_KEY")
    lmstudio_chat_model: str = Field(default="nvidia/nemotron-3-nano-4b", alias="LMSTUDIO_CHAT_MODEL")
    lmstudio_timeout: int = Field(default=60, alias="LMSTUDIO_TIMEOUT")
    vllm_backend_enabled: bool = Field(default=False, alias="VLLM_BACKEND_ENABLED")
    vllm_openai_compat_enabled: bool = Field(default=False, alias="VLLM_OPENAI_COMPAT_ENABLED")
    vllm_base_url: str = Field(default="http://localhost:8000/v1", alias="VLLM_BASE_URL")
    vllm_api_key: str = Field(default="", alias="VLLM_API_KEY")
    vllm_default_model: str = Field(default="facebook/opt-125m", alias="VLLM_DEFAULT_MODEL")
    vllm_timeout_seconds: int = Field(default=120, alias="VLLM_TIMEOUT_SECONDS")
    vllm_max_concurrent_requests: int = Field(default=16, alias="VLLM_MAX_CONCURRENT_REQUESTS")
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
    default_temperature: float = Field(default=0.7, alias="DEFAULT_TEMPERATURE")
    max_temperature: float = Field(default=1.5, alias="MAX_TEMPERATURE")
    default_top_p: float = Field(default=0.95, alias="DEFAULT_TOP_P")
    max_top_p: float = Field(default=1.0, alias="MAX_TOP_P")
    retry_attempts: int = Field(default=2, alias="RETRY_ATTEMPTS")
    retry_backoff_seconds: float = Field(default=1.0, alias="RETRY_BACKOFF_SECONDS")
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
    payment_processing_enabled: bool = Field(default=False, alias="PAYMENT_PROCESSING_ENABLED")
    payment_provider: str = Field(default="mock", alias="PAYMENT_PROVIDER")
    stripe_payment_enabled: bool = Field(default=False, alias="STRIPE_PAYMENT_ENABLED")
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    token_counting_real_enabled: bool = Field(default=True, alias="TOKEN_COUNTING_REAL_ENABLED")
    token_counting_fallback_allowed: bool = Field(default=True, alias="TOKEN_COUNTING_FALLBACK_ALLOWED")
    demo_client_name: str = Field(default="demo-client", alias="DEMO_CLIENT_NAME")
    demo_rate_limit_per_minute: int = Field(default=5, alias="DEMO_RATE_LIMIT_PER_MINUTE")
    demo_daily_token_quota: int = Field(default=20000, alias="DEMO_DAILY_TOKEN_QUOTA")
    demo_monthly_token_quota: int = Field(default=300000, alias="DEMO_MONTHLY_TOKEN_QUOTA")
    model_id: str = Field(default="unsloth/gemma-4-E4B-it-GGUF", alias="MODEL_ID")
    model_file: str = Field(default="gemma-4-E4B-it-Q4_K_M.gguf", alias="MODEL_FILE")
    models_dir: str = Field(default="/models", alias="MODELS_DIR")
    observability_enabled: bool = Field(default=True, alias="OBSERVABILITY_ENABLED")
    public_api_enabled: bool = Field(default=False, alias="PUBLIC_API_ENABLED")
    deployment_mode: str = Field(default="appliance", alias="DEPLOYMENT_MODE")
    kubernetes_mode: bool = Field(default=False, alias="KUBERNETES_MODE")
    distributed_runtime_enabled: bool = Field(default=False, alias="DISTRIBUTED_RUNTIME_ENABLED")
    gpu_autoscaling_enabled: bool = Field(default=False, alias="GPU_AUTOSCALING_ENABLED")
    plugin_marketplace_enabled: bool = Field(default=False, alias="PLUGIN_MARKETPLACE_ENABLED")
    managed_control_plane_enabled: bool = Field(default=False, alias="MANAGED_CONTROL_PLANE_ENABLED")
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
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    admin_token: str = Field(..., alias="ADMIN_TOKEN")
    max_request_body_size_bytes: int = Field(default=1024 * 1024 * 5, alias="MAX_REQUEST_BODY_SIZE_BYTES")
    max_tools_per_request: int = Field(default=16, alias="MAX_TOOLS_PER_REQUEST")
    max_tool_schema_bytes: int = Field(default=24 * 1024, alias="MAX_TOOL_SCHEMA_BYTES")
    max_tool_schema_depth: int = Field(default=16, alias="MAX_TOOL_SCHEMA_DEPTH")
    max_tool_schema_properties: int = Field(default=256, alias="MAX_TOOL_SCHEMA_PROPERTIES")
    max_tool_arguments_bytes: int = Field(default=16 * 1024, alias="MAX_TOOL_ARGUMENTS_BYTES")
    tool_argument_preview_chars: int = Field(default=160, alias="TOOL_ARGUMENT_PREVIEW_CHARS")
    abuse_detection_enabled: bool = Field(default=True, alias="ABUSE_DETECTION_ENABLED")
    abuse_auto_suspend_enabled: bool = Field(default=False, alias="ABUSE_AUTO_SUSPEND_ENABLED")
    abuse_dry_run: bool = Field(default=True, alias="ABUSE_DRY_RUN")
    tokenizer_mode: str = Field(default="auto", alias="TOKENIZER_MODE")
    tokenizer_model_path: str | None = Field(default=None, alias="TOKENIZER_MODEL_PATH")
    tokenizer_strict: bool = Field(default=False, alias="TOKENIZER_STRICT")
    tokenizer_cache_enabled: bool = Field(default=True, alias="TOKENIZER_CACHE_ENABLED")
    inference_max_context_tokens: int = Field(default=4096, alias="INFERENCE_MAX_CONTEXT_TOKENS")
    inference_max_completion_tokens: int = Field(default=512, alias="INFERENCE_MAX_COMPLETION_TOKENS")
    inference_max_system_chars: int = Field(default=2500, alias="INFERENCE_MAX_SYSTEM_CHARS")
    inference_max_history_messages: int = Field(default=8, alias="INFERENCE_MAX_HISTORY_MESSAGES")
    tts_enabled: bool = Field(default=True, alias="TTS_ENABLED")
    embeddings_enabled: bool = Field(default=True, alias="EMBEDDINGS_ENABLED")
    embeddings_backend: str = Field(default="local", alias="EMBEDDINGS_BACKEND")
    default_embedding_model: str = Field(default="text-embedding-3-small", alias="DEFAULT_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=384, alias="EMBEDDING_DIMENSIONS")
    mock_backend_enabled: bool = Field(default=False, alias="MOCK_BACKEND_ENABLED")
    providers_enabled: str = Field(default="local,lmstudio", alias="PROVIDERS_ENABLED")
    cloud_providers_enabled: bool = Field(default=False, alias="CLOUD_PROVIDERS_ENABLED")
    openai_provider_enabled: bool = Field(default=False, alias="OPENAI_PROVIDER_ENABLED")
    deepseek_provider_enabled: bool = Field(default=False, alias="DEEPSEEK_PROVIDER_ENABLED")
    anthropic_provider_enabled: bool = Field(default=False, alias="ANTHROPIC_PROVIDER_ENABLED")
    real_provider_validation_enabled: bool = Field(default=False, alias="REAL_PROVIDER_VALIDATION_ENABLED")
    real_provider_max_cost_brl: float = Field(default=2.00, alias="REAL_PROVIDER_MAX_COST_BRL")
    real_provider_log_prompts: bool = Field(default=False, alias="REAL_PROVIDER_LOG_PROMPTS")
    real_provider_store_responses: bool = Field(default=False, alias="REAL_PROVIDER_STORE_RESPONSES")
    max_global_provider_cost_per_day_brl: float = Field(default=0.0, alias="MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL")
    max_provider_cost_per_day_brl: float = Field(default=0.0, alias="MAX_PROVIDER_COST_PER_DAY_BRL")
    max_client_provider_cost_per_day_brl: float = Field(default=0.0, alias="MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL")
    margin_warning_percent: float = Field(default=20.0, alias="MARGIN_WARNING_PERCENT")
    negative_margin_block_mode: str = Field(default="report_only", alias="NEGATIVE_MARGIN_BLOCK_MODE")
    global_cloud_kill_switch: bool = Field(default=False, alias="GLOBAL_CLOUD_KILL_SWITCH")
    node_id: str = Field(default="", alias="NODE_ID")
    node_role: str = Field(default="api", alias="NODE_ROLE")
    cluster_id: str = Field(default="local", alias="CLUSTER_ID")
    pki_enabled: bool = Field(default=False, alias="PKI_ENABLED")
    pki_storage_path: str = Field(default="./data/pki", alias="PKI_STORAGE_PATH")
    pki_ca_rotation_days: int = Field(default=365, alias="PKI_CA_ROTATION_DAYS")
    pki_cert_rotation_days: int = Field(default=90, alias="PKI_CERT_ROTATION_DAYS")
    hardware_trust_enabled: bool = Field(default=False, alias="HARDWARE_TRUST_ENABLED")
    hardware_trust_provider: str = Field(default="mock", alias="HARDWARE_TRUST_PROVIDER")
    attestation_mode: str = Field(default="advisory", alias="ATTESTATION_MODE")
    plugin_signature_required: bool = Field(default=False, alias="PLUGIN_SIGNATURE_REQUIRED")
    model_hot_swap_enabled: bool = Field(default=False, alias="MODEL_HOT_SWAP_ENABLED")
    model_runtime_mock_enabled: bool = Field(default=False, alias="MODEL_RUNTIME_MOCK_ENABLED")
    create_tables_on_startup: bool = Field(default=False, alias="CREATE_TABLES_ON_STARTUP")
    model_runtime_port_start: int = Field(default=18081, alias="MODEL_RUNTIME_PORT_START")
    model_runtime_port_end: int = Field(default=18120, alias="MODEL_RUNTIME_PORT_END")
    model_load_timeout_seconds: int = Field(default=120, alias="MODEL_LOAD_TIMEOUT_SECONDS")
    model_rollback_on_failure: bool = Field(default=True, alias="MODEL_ROLLBACK_ON_FAILURE")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openai_provider_enabled: bool = Field(default=True, alias="OPENAI_PROVIDER_ENABLED")
    anthropic_provider_enabled: bool = Field(default=True, alias="ANTHROPIC_PROVIDER_ENABLED")
    deepseek_provider_enabled: bool = Field(default=True, alias="DEEPSEEK_PROVIDER_ENABLED")
    openrouter_provider_enabled: bool = Field(default=True, alias="OPENROUTER_PROVIDER_ENABLED")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_chat_model: str = Field(default="", alias="OPENAI_CHAT_MODEL")
    openai_embeddings_model: str = Field(default="", alias="OPENAI_EMBEDDINGS_MODEL")
    anthropic_base_url: str = Field(default="", alias="ANTHROPIC_BASE_URL")
    anthropic_model: str = Field(default="", alias="ANTHROPIC_MODEL")
    deepseek_base_url: str = Field(default="", alias="DEEPSEEK_BASE_URL")
    deepseek_chat_model: str = Field(default="", alias="DEEPSEEK_CHAT_MODEL")
    openrouter_base_url: str = Field(default="", alias="OPENROUTER_BASE_URL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_base_url: str = Field(default="", alias="GEMINI_BASE_URL")
    gemini_provider_enabled: bool = Field(default=True, alias="GEMINI_PROVIDER_ENABLED")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_provider_enabled: bool = Field(default=True, alias="BEDROCK_PROVIDER_ENABLED")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(default="2024-10-21", alias="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_provider_enabled: bool = Field(default=True, alias="AZURE_OPENAI_PROVIDER_ENABLED")
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")
    mistral_provider_enabled: bool = Field(default=True, alias="MISTRAL_PROVIDER_ENABLED")
    cohere_api_key: str = Field(default="", alias="COHERE_API_KEY")
    cohere_provider_enabled: bool = Field(default=True, alias="COHERE_PROVIDER_ENABLED")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_provider_enabled: bool = Field(default=True, alias="GROQ_PROVIDER_ENABLED")
    together_api_key: str = Field(default="", alias="TOGETHER_API_KEY")
    together_provider_enabled: bool = Field(default=True, alias="TOGETHER_PROVIDER_ENABLED")
    perplexity_api_key: str = Field(default="", alias="PERPLEXITY_API_KEY")
    perplexity_provider_enabled: bool = Field(default=True, alias="PERPLEXITY_PROVIDER_ENABLED")
    replicate_api_key: str = Field(default="", alias="REPLICATE_API_KEY")
    replicate_provider_enabled: bool = Field(default=True, alias="REPLICATE_PROVIDER_ENABLED")
    xai_api_key: str = Field(default="", alias="XAI_API_KEY")
    xai_provider_enabled: bool = Field(default=True, alias="XAI_PROVIDER_ENABLED")
    fireworks_api_key: str = Field(default="", alias="FIREWORKS_API_KEY")
    fireworks_provider_enabled: bool = Field(default=True, alias="FIREWORKS_PROVIDER_ENABLED")
    ai21_api_key: str = Field(default="", alias="AI21_API_KEY")
    ai21_provider_enabled: bool = Field(default=True, alias="AI21_PROVIDER_ENABLED")
    rate_limit_global_per_minute: int = Field(default=1000, alias="RATE_LIMIT_GLOBAL_PER_MINUTE")
    rate_limit_tenant_per_minute: int = Field(default=500, alias="RATE_LIMIT_TENANT_PER_MINUTE")
    oauth_google_client_id: str = Field(default="", alias="OAUTH_GOOGLE_CLIENT_ID")
    oauth_google_client_secret: str = Field(default="", alias="OAUTH_GOOGLE_CLIENT_SECRET")
    oauth_github_client_id: str = Field(default="", alias="OAUTH_GITHUB_CLIENT_ID")
    oauth_github_client_secret: str = Field(default="", alias="OAUTH_GITHUB_CLIENT_SECRET")
    oauth_enabled: bool = Field(default=False, alias="OAUTH_ENABLED")
    enterprise_sso_enabled: bool = Field(default=False, alias="ENTERPRISE_SSO_ENABLED")
    enterprise_sso_tenant_id: str = Field(default="", alias="ENTERPRISE_SSO_TENANT_ID")
    enterprise_sso_azure_client_id: str = Field(default="", alias="ENTERPRISE_SSO_AZURE_CLIENT_ID")
    enterprise_sso_azure_client_secret: str = Field(default="", alias="ENTERPRISE_SSO_AZURE_CLIENT_SECRET")
    enterprise_sso_okta_client_id: str = Field(default="", alias="ENTERPRISE_SSO_OKTA_CLIENT_ID")
    enterprise_sso_okta_client_secret: str = Field(default="", alias="ENTERPRISE_SSO_OKTA_CLIENT_SECRET")
    enterprise_sso_okta_domain: str = Field(default="", alias="ENTERPRISE_SSO_OKTA_DOMAIN")
    enterprise_sso_saml_sso_url: str = Field(default="", alias="ENTERPRISE_SSO_SAML_SSO_URL")
    enterprise_sso_saml_entity_id: str = Field(default="", alias="ENTERPRISE_SSO_SAML_ENTITY_ID")
    enterprise_sso_saml_certificate: str = Field(default="", alias="ENTERPRISE_SSO_SAML_CERTIFICATE")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    provider_max_retries: int = Field(default=2, alias="PROVIDER_MAX_RETRIES")
    provider_fail_closed: bool = Field(default=True, alias="PROVIDER_FAIL_CLOSED")
    routing_test_force_local_failure: bool = Field(default=False, alias="ROUTING_TEST_FORCE_LOCAL_FAILURE")
    payment_provider: str = Field(default="disabled", alias="PAYMENT_PROVIDER")
    payment_webhook_secret: str = Field(default="", alias="PAYMENT_WEBHOOK_SECRET")
    payment_real_enabled: bool = Field(default=False, alias="PAYMENT_REAL_ENABLED")
    kb_url_ingestion_enabled: bool = Field(default=False, alias="KB_URL_INGESTION_ENABLED")
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    vector_db_provider: str = Field(default="pgvector", alias="VECTOR_DB_PROVIDER")
    qdrant_enabled: bool = Field(default=False, alias="QDRANT_ENABLED")
    milvus_enabled: bool = Field(default=False, alias="MILVUS_ENABLED")
    weaviate_enabled: bool = Field(default=False, alias="WEAVIATE_ENABLED")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    milvus_url: str = Field(default="http://localhost:19530", alias="MILVUS_URL")
    milvus_token: str | None = Field(default=None, alias="MILVUS_TOKEN")
    weaviate_url: str = Field(default="http://localhost:8080", alias="WEAVIATE_URL")
    weaviate_api_key: str | None = Field(default=None, alias="WEAVIATE_API_KEY")
    rag_storage_dir: str = Field(default="./data/rag_uploads", alias="RAG_STORAGE_DIR")
    rag_max_file_mb: int = Field(default=25, alias="RAG_MAX_FILE_MB")
    rag_chunk_size: int = Field(default=1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, alias="RAG_CHUNK_OVERLAP")
    rag_top_k_default: int = Field(default=5, alias="RAG_TOP_K_DEFAULT")
    collab_chat_enabled: bool = Field(default=False, alias="COLLAB_CHAT_ENABLED")
    collab_chat_websocket_enabled: bool = Field(default=False, alias="COLLAB_CHAT_WEBSOCKET_ENABLED")
    realtime_voice_enabled: bool = Field(default=False, alias="REALTIME_VOICE_ENABLED")
    webrtc_audio_enabled: bool = Field(default=False, alias="WEBRTC_AUDIO_ENABLED")
    voice_agent_enabled: bool = Field(default=False, alias="VOICE_AGENT_ENABLED")
    voice_stt_streaming_enabled: bool = Field(default=False, alias="VOICE_STT_STREAMING_ENABLED")
    voice_tts_streaming_enabled: bool = Field(default=False, alias="VOICE_TTS_STREAMING_ENABLED")
    webrtc_voice_enabled: bool = Field(default=False, alias="WEBRTC_VOICE_ENABLED")
    model_experiments_enabled: bool = Field(default=False, alias="MODEL_EXPERIMENTS_ENABLED")
    model_canary_enabled: bool = Field(default=False, alias="MODEL_CANARY_ENABLED")
    model_ab_testing_enabled: bool = Field(default=False, alias="MODEL_AB_TESTING_ENABLED")
    web_ide_enabled: bool = Field(default=False, alias="WEB_IDE_ENABLED")
    web_ide_workspaces_dir: str = Field(default="./data/ide_workspaces", alias="WEB_IDE_WORKSPACES_DIR")
    mobile_foundation_enabled: bool = Field(default=False, alias="MOBILE_FOUNDATION_ENABLED")
    push_notifications_enabled: bool = Field(default=False, alias="PUSH_NOTIFICATIONS_ENABLED")
    payment_processing_enabled: bool = Field(default=False, alias="PAYMENT_PROCESSING_ENABLED")
    payment_provider: str = Field(default="mock", alias="PAYMENT_PROVIDER")
    pix_payment_enabled: bool = Field(default=False, alias="PIX_PAYMENT_ENABLED")
    card_payment_enabled: bool = Field(default=False, alias="CARD_PAYMENT_ENABLED")
    stripe_api_key: str = Field(default="", alias="STRIPE_API_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    mercadopago_access_token: str = Field(default="", alias="MERCADOPAGO_ACCESS_TOKEN")
    asaas_api_key: str = Field(default="", alias="ASAAS_API_KEY")
    rag_embedding_provider: str = Field(default="local", alias="RAG_EMBEDDING_PROVIDER")
    rag_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="RAG_EMBEDDING_MODEL")
    mlops_dataset_storage_path: str = Field(default="", alias="MLOPS_DATASET_STORAGE_PATH")
    fine_tuning_enabled: bool = Field(default=False, alias="FINE_TUNING_ENABLED")
    fine_tuning_gpu_provider: bool = Field(default=False, alias="FINE_TUNING_GPU_PROVIDER_ENABLED")
    deployment_autoscale_enabled: bool = Field(default=True, alias="DEPLOYMENT_AUTOSCALE_ENABLED")
    deployment_autoscale_window_sec: int = Field(default=60, alias="DEPLOYMENT_AUTOSCALE_WINDOW_SEC")
    pagerduty_routing_key: str = Field(default="", alias="PAGERDUTY_ROUTING_KEY")
    opsgenie_api_key: str = Field(default="", alias="OPSGENIE_API_KEY")
    opsgenie_api_url: str = Field(default="https://api.opsgenie.com/v2/alerts", alias="OPSGENIE_API_URL")
    content_moderation_enabled: bool = Field(default=True, alias="CONTENT_MODERATION_ENABLED")
    content_moderation_toxicity_threshold: float = Field(default=0.7, alias="CONTENT_MODERATION_TOXICITY_THRESHOLD")
    a2a_enabled: bool = Field(default=False, alias="A2A_ENABLED")
    a2a_base_url: str = Field(default="", alias="A2A_BASE_URL")
    a2a_api_key: str = Field(default="", alias="A2A_API_KEY")
    secrets_manager_provider: str = Field(default="vault", alias="SECRETS_MANAGER_PROVIDER")
    vault_addr: str = Field(default="http://localhost:8200", alias="VAULT_ADDR")
    vault_token: str = Field(default="", alias="VAULT_TOKEN")
    vault_kv_mount: str = Field(default="secret", alias="VAULT_KV_MOUNT")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    cluster_region: str = Field(default="default", alias="CLUSTER_REGION")
    data_residency_enabled: bool = Field(default=False, alias="DATA_RESIDENCY_ENABLED")
    disaster_recovery_enabled: bool = Field(default=False, alias="DISASTER_RECOVERY_ENABLED")
    disaster_recovery_backup_dir: str = Field(default="/tmp/agent-backups", alias="DISASTER_RECOVERY_BACKUP_DIR")
    disaster_recovery_schedule_hours: int = Field(default=24, alias="DISASTER_RECOVERY_SCHEDULE_HOURS")
    marketplace_governance_enabled: bool = Field(default=True, alias="MARKETPLACE_GOVERNANCE_ENABLED")
    marketplace_require_security_scan: bool = Field(default=True, alias="MARKETPLACE_REQUIRE_SECURITY_SCAN")
    marketplace_require_approval: bool = Field(default=True, alias="MARKETPLACE_REQUIRE_APPROVAL")

    @model_validator(mode='after')
    def validate_sensitive_fields(self) -> Self:
        sensitive_fields = [
            "jwt_secret", "admin_token", "pinecone_api_key", "sendgrid_api_key",
            "fcm_api_key", "stripe_secret_key", "stripe_webhook_secret",
            "openai_api_key", "anthropic_api_key", "deepseek_api_key",
            "openrouter_api_key", "gemini_api_key", "aws_secret_access_key",
            "azure_openai_api_key", "mistral_api_key", "cohere_api_key",
            "groq_api_key", "together_api_key", "perplexity_api_key",
            "replicate_api_key", "xai_api_key", "fireworks_api_key",
            "ai21_api_key", "oauth_google_client_secret", "oauth_github_client_secret",
            "enterprise_sso_azure_client_secret", "enterprise_sso_okta_client_secret",
            "vault_token", "a2a_api_key"
        ]
        
        for field in sensitive_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if isinstance(value, str) and value:
                    if value == "change-me-at-all-costs" or value == "default-admin-token":
                        raise ValueError(f"{field.upper()} must be set to a secure, unique value.")
                    if len(value) < 32:
                        raise ValueError(f"{field.upper()} is too short. Minimum 32 characters required.")
        return self

    @computed_field
    @property
    def max_completion_tokens(self) -> int:
        return self.inference_max_completion_tokens

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        return resolve_cors_origins(
            self.cors_allow_origins,
            self.app_public_url,
            self.localhost_mode,
            self.local_appliance_mode
        )

def load_config_profile(profile: str = "local") -> Dict[str, Any]:
    config_dir = Path(__file__).resolve().parents[3] / "config" / "profiles"
    profile_path = config_dir / f"{profile}.yaml"
    
    if profile_path.exists():
        with open(profile_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

class ConfigService:
    _instance = None

    def __init__(self):
        self.profile = os.environ.get("DEPLOYMENT_PROFILE", "local")
        self.profile_config = load_config_profile(self.profile)
        # Initialize BaseAppConfig with YAML overrides + Environment variables
        self.settings = BaseAppConfig(**self.profile_config)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    @property
    def config(self):
        return self.settings

_service = None

def get_config_service():
    global _service
    if _service is None:
        _service = ConfigService.get_instance()
    return _service
