from time import time
from pathlib import Path
from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from control_plane.app.core.cors import resolve_cors_origins


def _get_version() -> str:
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


class CoreConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    project_name: str = Field(default="local-llm-inference-stack", alias="PROJECT_NAME")
    project_version: str = Field(default_factory=_get_version)
    start_time: float = Field(default_factory=time)
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    control_plane_host: str = Field(default="0.0.0.0", alias="CONTROL_PLANE_HOST")
    control_plane_port: int = Field(default=8080, alias="CONTROL_PLANE_PORT")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    data_plane_base_url: str = Field(alias="DATA_PLANE_BASE_URL")

    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")

    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    app_public_url: str = Field(default="http://localhost:18080", alias="APP_PUBLIC_URL")
    admin_base_url: str = Field(default="", alias="ADMIN_BASE_URL")
    client_portal_base_url: str = Field(default="", alias="CLIENT_PORTAL_BASE_URL")
    docs_base_url: str = Field(default="", alias="DOCS_BASE_URL")
    api_base_url: str = Field(default="", alias="API_BASE_URL")

    public_exposure: bool = Field(default=False, alias="PUBLIC_EXPOSURE")
    public_signup_enabled: bool = Field(default=True, alias="PUBLIC_SIGNUP_ENABLED")
    public_brand_name: str = Field(default="LLM Inference Stack Cloud", alias="PUBLIC_BRAND_NAME")
    public_support_email: str = Field(default="sales@example.com", alias="PUBLIC_SUPPORT_EMAIL")
    public_analytics_provider: str = Field(default="none", alias="PUBLIC_ANALYTICS_PROVIDER")
    public_plausible_domain: str = Field(default="", alias="PUBLIC_PLAUSIBLE_DOMAIN")
    public_plausible_src: str = Field(default="https://plausible.io/js/script.js", alias="PUBLIC_PLAUSIBLE_SRC")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")
    public_api_enabled: bool = Field(default=False, alias="PUBLIC_API_ENABLED")
    public_signup_rate_limit_per_minute: int = Field(default=5, ge=1, le=60, alias="PUBLIC_SIGNUP_RATE_LIMIT_PER_MINUTE")

    deployment_mode: str = Field(default="appliance", alias="DEPLOYMENT_MODE")
    kubernetes_mode: bool = Field(default=False, alias="KUBERNETES_MODE")
    app_env: str = Field(default="local", alias="APP_ENV")
    localhost_mode: bool = Field(default=False, alias="LOCALHOST_MODE")
    local_appliance_mode: bool = Field(default=False, alias="LOCAL_APPLIANCE_MODE")
    observability_enabled: bool = Field(default=True, alias="OBSERVABILITY_ENABLED")

    # Feature Flag Simplification Profiles
    agent_tool_set: str = Field(default="standard", alias="AGENT_TOOL_SET") # minimal|standard|full
    observability_profile: str = Field(default="basic", alias="OBSERVABILITY_PROFILE") # off|basic|full
    commercial_profile: str = Field(default="off", alias="COMMERCIAL_PROFILE") # off|billing|billing_payments
    security_profile: str = Field(default="local", alias="SECURITY_PROFILE") # local|standard|enterprise

    operational_profile: str = Field(default="lite", alias="OPERATIONAL_PROFILE")
    test_tools_enabled: bool = Field(default=False, alias="TEST_TOOLS_ENABLED")

    tempo_endpoint: str = Field(default="http://localhost:4317", alias="TEMPO_ENDPOINT")

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
    model_hot_swap_enabled: bool = Field(default=False, alias="MODEL_HOT_SWAP_ENABLED")
    model_runtime_mock_enabled: bool = Field(default=False, alias="MODEL_RUNTIME_MOCK_ENABLED")
    create_tables_on_startup: bool = Field(default=False, alias="CREATE_TABLES_ON_STARTUP")
    model_runtime_port_start: int = Field(default=18081, alias="MODEL_RUNTIME_PORT_START")
    model_runtime_port_end: int = Field(default=18120, alias="MODEL_RUNTIME_PORT_END")
    model_load_timeout_seconds: int = Field(default=120, alias="MODEL_LOAD_TIMEOUT_SECONDS")
    model_rollback_on_failure: bool = Field(default=True, alias="MODEL_ROLLBACK_ON_FAILURE")
    distributed_runtime_enabled: bool = Field(default=False, alias="DISTRIBUTED_RUNTIME_ENABLED")
    gpu_autoscaling_enabled: bool = Field(default=False, alias="GPU_AUTOSCALING_ENABLED")
    managed_control_plane_enabled: bool = Field(default=False, alias="MANAGED_CONTROL_PLANE_ENABLED")
    model_id: str = Field(default="unsloth/gemma-4-E4B-it-GGUF", alias="MODEL_ID")
    model_file: str = Field(default="gemma-4-E4B-it-Q4_K_M.gguf", alias="MODEL_FILE")
    models_dir: str = Field(default="/models", alias="MODELS_DIR")

    cloud_providers_enabled: bool = Field(default=False, alias="CLOUD_PROVIDERS_ENABLED")
    openai_provider_enabled: bool = Field(default=True, alias="OPENAI_PROVIDER_ENABLED")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_provider_enabled: bool = Field(default=True, alias="ANTHROPIC_PROVIDER_ENABLED")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepseek_provider_enabled: bool = Field(default=True, alias="DEEPSEEK_PROVIDER_ENABLED")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    openrouter_provider_enabled: bool = Field(default=True, alias="OPENROUTER_PROVIDER_ENABLED")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
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
    provider_max_retries: int = Field(default=2, alias="PROVIDER_MAX_RETRIES")
    provider_fail_closed: bool = Field(default=True, alias="PROVIDER_FAIL_CLOSED")
    routing_test_force_local_failure: bool = Field(default=False, alias="ROUTING_TEST_FORCE_LOCAL_FAILURE")

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
    semantic_cache_ttl_seconds: int = Field(default=3600, alias="SEMANTIC_CACHE_TTL_SECONDS")
    semantic_cache_max_size: int = Field(default=10000, alias="SEMANTIC_CACHE_MAX_SIZE")
    semantic_cache_threshold: float = Field(default=0.9, alias="SEMANTIC_CACHE_THRESHOLD")

    enable_legacy_static: bool = Field(default=False, alias="ENABLE_LEGACY_STATIC")

    # Chaos Engineering
    chaos_enabled: bool = Field(default=False, alias="CHAOS_ENABLED")
    chaos_environment: str = Field(default="test", alias="CHAOS_ENVIRONMENT")
    chaos_allow_production: bool = Field(default=False, alias="CHAOS_ALLOW_PRODUCTION")

    # Agent Runtime Service (Migration)
    agent_runtime_service_remote: bool = Field(default=False, alias="AGENT_RUNTIME_SERVICE_REMOTE")
    agent_runtime_service_url: str = Field(default="http://agent-runtime:8080", alias="AGENT_RUNTIME_SERVICE_URL")
    agent_runtime_service_token: str = Field(default="agent-runtime-secret-token", alias="AGENT_RUNTIME_SERVICE_TOKEN")

    rate_limit_global_per_minute: int = Field(default=1000, alias="RATE_LIMIT_GLOBAL_PER_MINUTE")
    rate_limit_tenant_per_minute: int = Field(default=500, alias="RATE_LIMIT_TENANT_PER_MINUTE")

    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    demo_client_name: str = Field(default="demo-client", alias="DEMO_CLIENT_NAME")
    demo_rate_limit_per_minute: int = Field(default=5, alias="DEMO_RATE_LIMIT_PER_MINUTE")
    demo_daily_token_quota: int = Field(default=20000, alias="DEMO_DAILY_TOKEN_QUOTA")
    demo_monthly_token_quota: int = Field(default=300000, alias="DEMO_MONTHLY_TOKEN_QUOTA")

    token_counting_real_enabled: bool = Field(default=True, alias="TOKEN_COUNTING_REAL_ENABLED")
    token_counting_fallback_allowed: bool = Field(default=True, alias="TOKEN_COUNTING_FALLBACK_ALLOWED")

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

    real_provider_validation_enabled: bool = Field(default=False, alias="REAL_PROVIDER_VALIDATION_ENABLED")
    provider_timeout_seconds: int = Field(default=30, ge=1, le=300, alias="PROVIDER_TIMEOUT_SECONDS")
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
    data_residency_enabled: bool = Field(default=False, alias="DATA_RESIDENCY_ENABLED")

    mlops_dataset_storage_path: str = Field(default="", alias="MLOPS_DATASET_STORAGE_PATH")
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
    rag_embedding_provider: str = Field(default="local", alias="RAG_EMBEDDING_PROVIDER")
    rag_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="RAG_EMBEDDING_MODEL")

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
