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
    commercial_witness_federation_enabled: bool = False
    commercial_witness_mode: str = "dry_run"
    commercial_witness_min_signatures: int = 1
    commercial_witness_require_external: bool = False
    commercial_witness_signature_algorithm: str = "ed25519_placeholder"
    commercial_witness_request_timeout_seconds: int = 10
    commercial_transparency_gossip_enabled: bool = False
    commercial_transparency_gossip_mode: str = "dry_run"
    commercial_transparency_checkpoint_interval_minutes: int = 60
    commercial_transparency_require_witness_quorum: bool = False
    commercial_transparency_split_view_alerts: bool = True
    commercial_public_attestation_gateway_enabled: bool = False
    commercial_public_attestation_mode: str = "local_only"
    commercial_public_attestation_rate_limit_rpm: int = 60
    commercial_public_attestation_allow_anonymous: bool = False
    commercial_public_attestation_max_payload_kb: int = 512
    commercial_confidential_runtime_enabled: bool = False
    commercial_confidential_runtime_mode: str = "report_only"
    commercial_confidential_require_model_trust: bool = True
    commercial_confidential_prohibit_plaintext_logging: bool = True
    commercial_confidential_default_retention_seconds: int = 0
    commercial_agent_governance_enabled: bool = False
    commercial_agent_governance_mode: str = "audit_only"
    commercial_agent_default_delegation_limit: int = 3
    commercial_agent_memory_isolation_level: str = "strict"
    commercial_agent_tool_approval_required: bool = True
    commercial_workflow_determinism_enabled: bool = False
    commercial_workflow_enforce_reproducibility: bool = True
    commercial_workflow_checkpoint_frequency: int = 1 # every N steps
    commercial_workflow_drift_threshold: float = 0.01
    commercial_appliance_mode_enabled: bool = False
    commercial_appliance_id: str = "appliance-000"
    commercial_appliance_deployment_tier: str = "regulated"
    commercial_appliance_require_removable_media: bool = False

    # Owner: agent-platform
    # Status: beta
    agent_runtime_enabled: bool = Field(default=False, alias="AGENT_RUNTIME_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_execution_enabled: bool = Field(default=False, alias="AGENT_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_async_execution_enabled: bool = Field(default=False, alias="AGENT_ASYNC_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_execution_plane_enabled: bool = Field(default=False, alias="AGENT_EXECUTION_PLANE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_worker_enabled: bool = Field(default=False, alias="AGENT_WORKER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_embedded_worker_enabled: bool = Field(default=False, alias="AGENT_EMBEDDED_WORKER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_queue_backpressure_enabled: bool = Field(default=True, alias="AGENT_QUEUE_BACKPRESSURE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_replay_enabled: bool = Field(default=True, alias="AGENT_REPLAY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_runtime_advisory_mode: bool = Field(default=True, alias="AGENT_RUNTIME_ADVISORY_MODE")

    # Owner: agent-platform
    # Status: beta
    agent_tool_registry_enabled: bool = Field(default=False, alias="AGENT_TOOL_REGISTRY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_tool_execution_enabled: bool = Field(default=False, alias="AGENT_TOOL_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_destructive_tools_enabled: bool = Field(default=False, alias="AGENT_DESTRUCTIVE_TOOLS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_tool_sandbox_enabled: bool = Field(default=True, alias="AGENT_TOOL_SANDBOX_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_tool_credential_delegation_enabled: bool = Field(default=False, alias="AGENT_TOOL_CREDENTIAL_DELEGATION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_tool_rollback_enabled: bool = Field(default=True, alias="AGENT_TOOL_ROLLBACK_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_tool_adapters_enabled: bool = Field(default=False, alias="AGENT_TOOL_ADAPTERS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_saas_connectors_enabled: bool = Field(default=False, alias="AGENT_SAAS_CONNECTORS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_connector_write_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_WRITE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_connector_external_network_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_connector_oauth_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_OAUTH_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_http_tool_enabled: bool = Field(default=False, alias="AGENT_HTTP_TOOL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_db_read_tool_enabled: bool = Field(default=False, alias="AGENT_DB_READ_TOOL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_shell_tool_enabled: bool = Field(default=False, alias="AGENT_SHELL_TOOL_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_planner_real_execution_enabled: bool = Field(default=False, alias="AGENT_PLANNER_REAL_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_replan_enabled: bool = Field(default=True, alias="AGENT_REPLAN_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_human_approval_enabled: bool = Field(default=True, alias="AGENT_HUMAN_APPROVAL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_approval_required_for_high_risk: bool = Field(default=True, alias="AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK")
    agent_approval_timeout_seconds: int = Field(default=86400, alias="AGENT_APPROVAL_TIMEOUT_SECONDS")

    # Owner: agent-platform
    # Status: beta
    agent_observability_enabled: bool = Field(default=True, alias="AGENT_OBSERVABILITY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_trace_export_enabled: bool = Field(default=False, alias="AGENT_TRACE_EXPORT_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_evals_enabled: bool = Field(default=False, alias="AGENT_EVALS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_production_requires_eval_baseline: bool = Field(default=True, alias="AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE")
    # Owner: agent-platform
    # Status: beta
    agent_regression_evals_required: bool = Field(default=True, alias="AGENT_REGRESSION_EVALS_REQUIRED")
    # Owner: agent-platform
    # Status: beta
    agent_eval_regression_gate_enabled: bool = Field(default=True, alias="AGENT_EVAL_REGRESSION_GATE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_eval_datasets_versioned: bool = Field(default=True, alias="AGENT_EVAL_DATASETS_VERSIONED")
    # Owner: agent-platform
    # Status: beta
    agent_eval_real_provider_enabled: bool = Field(default=False, alias="AGENT_EVAL_REAL_PROVIDER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_eval_provider: str = Field(default="mock", alias="AGENT_EVAL_PROVIDER")
    # Owner: agent-platform
    # Status: beta
    agent_promotion_requires_evals: bool = Field(default=True, alias="AGENT_PROMOTION_REQUIRES_EVALS")

    # SaaS Connectors Auth
    # Owner: agent-platform
    # Status: beta
    agent_connector_token_storage_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_TOKEN_STORAGE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_connector_credential_rotation_enabled: bool = Field(default=True, alias="AGENT_CONNECTOR_CREDENTIAL_ROTATION_ENABLED")

    # Agent Studio
    # Owner: agent-platform
    # Status: beta
    agent_studio_enabled: bool = Field(default=False, alias="AGENT_STUDIO_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_visual_builder_enabled: bool = Field(default=False, alias="AGENT_VISUAL_BUILDER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_debugger_enabled: bool = Field(default=False, alias="AGENT_DEBUGGER_ENABLED")

    # Multi-Agent Orchestration
    # Owner: agent-platform
    # Status: beta
    agent_hierarchical_teams_enabled: bool = Field(default=False, alias="AGENT_HIERARCHICAL_TEAMS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_debate_teams_enabled: bool = Field(default=False, alias="AGENT_DEBATE_TEAMS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_shared_workspace_enabled: bool = Field(default=False, alias="AGENT_SHARED_WORKSPACE_ENABLED")

    # Reasoning Loops
    # Owner: agent-platform
    # Status: beta
    agent_reasoning_loop_enabled: bool = Field(default=False, alias="AGENT_REASONING_LOOP_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_react_loop_enabled: bool = Field(default=False, alias="AGENT_REACT_LOOP_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_plan_and_solve_enabled: bool = Field(default=False, alias="AGENT_PLAN_AND_SOLVE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_structured_output_retry_enabled: bool = Field(default=True, alias="AGENT_STRUCTURED_OUTPUT_RETRY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_context_compression_enabled: bool = Field(default=False, alias="AGENT_CONTEXT_COMPRESSION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_semantic_model_fallback_enabled: bool = Field(default=False, alias="AGENT_SEMANTIC_MODEL_FALLBACK_ENABLED")

    # Stateful Workflows
    # Owner: agent-platform
    # Status: beta
    agent_stateful_workflows_enabled: bool = Field(default=False, alias="AGENT_STATEFUL_WORKFLOWS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_workflow_timers_enabled: bool = Field(default=False, alias="AGENT_WORKFLOW_TIMERS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_workflow_webhooks_enabled: bool = Field(default=False, alias="AGENT_WORKFLOW_WEBHOOKS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_workflow_polling_enabled: bool = Field(default=False, alias="AGENT_WORKFLOW_POLLING_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_workflow_distributed_locks_enabled: bool = Field(default=True, alias="AGENT_WORKFLOW_DISTRIBUTED_LOCKS_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_memory_enabled: bool = Field(default=False, alias="AGENT_MEMORY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_long_term_memory_enabled: bool = Field(default=False, alias="AGENT_LONG_TERM_MEMORY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_write_enabled: bool = Field(default=False, alias="AGENT_MEMORY_WRITE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_export_enabled: bool = Field(default=False, alias="AGENT_MEMORY_EXPORT_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_search_enabled: bool = Field(default=False, alias="AGENT_MEMORY_SEARCH_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_consent_required: bool = Field(default=True, alias="AGENT_MEMORY_CONSENT_REQUIRED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_encryption_enabled: bool = Field(default=False, alias="AGENT_MEMORY_ENCRYPTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_semantic_search_enabled: bool = Field(default=False, alias="AGENT_MEMORY_SEMANTIC_SEARCH_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_context_injection_enabled: bool = Field(default=False, alias="AGENT_MEMORY_CONTEXT_INJECTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_embeddings_provider: str = Field(default="mock", alias="AGENT_MEMORY_EMBEDDINGS_PROVIDER")

    # Owner: agent-platform
    # Status: beta
    agent_planning_enabled: bool = Field(default=False, alias="AGENT_PLANNING_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_plan_execution_enabled: bool = Field(default=False, alias="AGENT_PLAN_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_auto_retry_enabled: bool = Field(default=True, alias="AGENT_AUTO_RETRY_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_handoffs_enabled: bool = Field(default=False, alias="AGENT_HANDOFFS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_multi_agent_enabled: bool = Field(default=False, alias="AGENT_MULTI_AGENT_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_llm_provider: str = Field(default="mock", alias="AGENT_LLM_PROVIDER")
    # Owner: agent-platform
    # Status: beta
    agent_real_llm_enabled: bool = Field(default=False, alias="AGENT_REAL_LLM_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_llm_streaming_enabled: bool = Field(default=False, alias="AGENT_LLM_STREAMING_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_marketplace_enabled: bool = Field(default=False, alias="AGENT_MARKETPLACE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_remote_marketplace_enabled: bool = Field(default=False, alias="AGENT_REMOTE_MARKETPLACE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_bundle_install_enabled: bool = Field(default=False, alias="AGENT_BUNDLE_INSTALL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_bundle_signature_required: bool = Field(default=False, alias="AGENT_BUNDLE_SIGNATURE_REQUIRED")

    # Owner: agent-platform
    # Status: beta
    agent_incident_response_enabled: bool = Field(default=True, alias="AGENT_INCIDENT_RESPONSE_ENABLED")

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
    rbac_admin_enabled: bool = Field(default=False, alias="RBAC_ADMIN_ENABLED")
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
    lmstudio_enabled: bool = Field(default=True, alias="LMSTUDIO_ENABLED")
    lmstudio_base_url: str = Field(default="http://192.168.101.1:1234/v1", alias="LMSTUDIO_BASE_URL")
    lmstudio_api_key: str = Field(default="", alias="LMSTUDIO_API_KEY")
    lmstudio_default_model: str = Field(default="nvidia/nemotron-3-nano-4b", alias="LMSTUDIO_DEFAULT_MODEL")
    data_plane_timeout_seconds: int = Field(default=120, alias="DATA_PLANE_TIMEOUT_SECONDS")
    request_timeout_seconds: int = Field(default=120, alias="REQUEST_TIMEOUT_SECONDS")
    queue_timeout_seconds: int = Field(default=30, alias="QUEUE_TIMEOUT_SECONDS")
    max_concurrent_generations: int = Field(default=1, alias="MAX_CONCURRENT_GENERATIONS")
    max_queue_size: int = Field(default=8, alias="MAX_QUEUE_SIZE")

    # QoS Phase 25
    commercial_qos_fairness_enabled: bool = Field(default=True, alias="COMMERCIAL_QOS_FAIRNESS_ENABLED")
    commercial_qos_fairness_collection_interval_seconds: int = Field(default=60, alias="COMMERCIAL_QOS_FAIRNESS_COLLECTION_INTERVAL_SECONDS")
    commercial_qos_starvation_threshold_seconds: int = Field(default=1800, alias="COMMERCIAL_QOS_STARVATION_THRESHOLD_SECONDS")
    commercial_qos_priority_inversion_alert: bool = Field(default=True, alias="COMMERCIAL_QOS_PRIORITY_INVERSION_ALERT")

    commercial_qos_chargeback_enabled: bool = Field(default=True, alias="COMMERCIAL_QOS_CHARGEBACK_ENABLED")
    commercial_qos_chargeback_mode: str = Field(default="report_only", alias="COMMERCIAL_QOS_CHARGEBACK_MODE")
    commercial_qos_priority_slot_cost_brl_per_second: float = Field(default=0.001, alias="COMMERCIAL_QOS_PRIORITY_SLOT_COST_BRL_PER_SECOND")

    # Commercial QoS Billing Phase 26
    commercial_qos_billing_enabled: bool = Field(default=False, alias="COMMERCIAL_QOS_BILLING_ENABLED")
    # disabled|report_only|invoice_line_item|wallet_debit_opt_in
    commercial_qos_billing_mode: str = Field(default="report_only", alias="COMMERCIAL_QOS_BILLING_MODE")
    commercial_qos_billing_debit_wallet: bool = Field(default=False, alias="COMMERCIAL_QOS_BILLING_DEBIT_WALLET")
    commercial_qos_billing_include_opportunity_cost: bool = Field(default=False, alias="COMMERCIAL_QOS_BILLING_INCLUDE_OPPORTUNITY_COST")
    commercial_qos_billing_min_amount_brl: float = Field(default=0.01, alias="COMMERCIAL_QOS_BILLING_MIN_AMOUNT_BRL")
    commercial_qos_billing_max_daily_debit_brl_per_client: float = Field(default=100.0, alias="COMMERCIAL_QOS_BILLING_MAX_DAILY_DEBIT_BRL_PER_CLIENT")
    commercial_qos_billing_invoice_line_item: bool = Field(default=True, alias="COMMERCIAL_QOS_BILLING_INVOICE_LINE_ITEM")

    # Phase 27: Financial Reconciliation + Dispute Management
    commercial_financial_reconciliation_enabled: bool = Field(default=True, alias="COMMERCIAL_FINANCIAL_RECONCILIATION_ENABLED")
    commercial_financial_reconciliation_threshold_percent: float = Field(default=2.0, alias="COMMERCIAL_FINANCIAL_RECONCILIATION_THRESHOLD_PERCENT")
    commercial_financial_dispute_enabled: bool = Field(default=True, alias="COMMERCIAL_FINANCIAL_DISPUTE_ENABLED")
    commercial_financial_audit_chain_enabled: bool = Field(default=True, alias="COMMERCIAL_FINANCIAL_AUDIT_CHAIN_ENABLED")
    commercial_financial_manual_credit_enabled: bool = Field(default=False, alias="COMMERCIAL_FINANCIAL_MANUAL_CREDIT_ENABLED")
    commercial_compliance_controls_enabled: bool = Field(default=True, alias="COMMERCIAL_COMPLIANCE_CONTROLS_ENABLED")
    commercial_compliance_mode: str = Field(default="report_only", alias="COMMERCIAL_COMPLIANCE_MODE")
    commercial_compliance_require_evidence: bool = Field(default=True, alias="COMMERCIAL_COMPLIANCE_REQUIRE_EVIDENCE")
    commercial_compliance_default_approver_count: int = Field(default=1, alias="COMMERCIAL_COMPLIANCE_DEFAULT_APPROVER_COUNT")
    commercial_compliance_segregation_required: bool = Field(default=True, alias="COMMERCIAL_COMPLIANCE_SEGREGATION_REQUIRED")
    commercial_enterprise_audit_portal_enabled: bool = Field(default=True, alias="COMMERCIAL_ENTERPRISE_AUDIT_PORTAL_ENABLED")
    commercial_enterprise_audit_export_pdf_enabled: bool = Field(default=False, alias="COMMERCIAL_ENTERPRISE_AUDIT_EXPORT_PDF_ENABLED")
    commercial_enterprise_audit_log_retention_days: int = Field(default=365, alias="COMMERCIAL_ENTERPRISE_AUDIT_LOG_RETENTION_DAYS")
    commercial_enterprise_audit_require_rbac: bool = Field(default=True, alias="COMMERCIAL_ENTERPRISE_AUDIT_REQUIRE_RBAC")
    commercial_operational_controls_enabled: bool = Field(default=True, alias="COMMERCIAL_OPERATIONAL_CONTROLS_ENABLED")
    commercial_operational_controls_mode: str = Field(default="report_only", alias="COMMERCIAL_OPERATIONAL_CONTROLS_MODE")
    commercial_operational_control_default_evidence_sla_days: int = Field(default=90, alias="COMMERCIAL_OPERATIONAL_CONTROL_DEFAULT_EVIDENCE_SLA_DAYS")
    commercial_operational_control_overdue_escalations_enabled: bool = Field(default=True, alias="COMMERCIAL_OPERATIONAL_CONTROL_OVERDUE_ESCALATIONS_ENABLED")

    # Phase 28: Revenue Forecasting + Financial Anomaly Detection
    commercial_revenue_forecasting_enabled: bool = Field(default=True, alias="COMMERCIAL_REVENUE_FORECASTING_ENABLED")
    commercial_revenue_forecast_method: str = Field(default="ewma", alias="COMMERCIAL_REVENUE_FORECAST_METHOD")
    commercial_revenue_forecast_window_days: int = Field(default=30, alias="COMMERCIAL_REVENUE_FORECAST_WINDOW_DAYS")
    commercial_revenue_forecast_min_samples: int = Field(default=7, alias="COMMERCIAL_REVENUE_FORECAST_MIN_SAMPLES")

    commercial_financial_anomaly_detection_enabled: bool = Field(default=True, alias="COMMERCIAL_FINANCIAL_ANOMALY_DETECTION_ENABLED")
    commercial_financial_anomaly_zscore_threshold: float = Field(default=3.0, alias="COMMERCIAL_FINANCIAL_ANOMALY_ZSCORE_THRESHOLD")
    commercial_financial_anomaly_percent_threshold: float = Field(default=30.0, alias="COMMERCIAL_FINANCIAL_ANOMALY_PERCENT_THRESHOLD")
    commercial_financial_anomaly_min_samples: int = Field(default=7, alias="COMMERCIAL_FINANCIAL_ANOMALY_MIN_SAMPLES")
    commercial_revenue_protection_enabled: bool = Field(default=True, alias="COMMERCIAL_REVENUE_PROTECTION_ENABLED")
    commercial_revenue_protection_mode: str = Field(default="report_only", alias="COMMERCIAL_REVENUE_PROTECTION_MODE")
    commercial_revenue_protection_allow_enforce: bool = Field(default=False, alias="COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE")
    commercial_revenue_protection_cooldown_minutes: int = Field(default=60, alias="COMMERCIAL_REVENUE_PROTECTION_COOLDOWN_MINUTES")
    commercial_revenue_protection_webhook_enabled: bool = Field(default=False, alias="COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_ENABLED")
    commercial_revenue_protection_webhook_url: str = Field(default="", alias="COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_URL")
    commercial_revenue_escalations_enabled: bool = Field(default=True, alias="COMMERCIAL_REVENUE_ESCALATIONS_ENABLED")
    commercial_revenue_escalations_mode: str = Field(default="dry_run", alias="COMMERCIAL_REVENUE_ESCALATIONS_MODE")
    commercial_revenue_webhook_enabled: bool = Field(default=False, alias="COMMERCIAL_REVENUE_WEBHOOK_ENABLED")
    commercial_revenue_webhook_url: str = Field(default="", alias="COMMERCIAL_REVENUE_WEBHOOK_URL")
    commercial_revenue_webhook_signing_secret: str = Field(default="", alias="COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET")
    commercial_revenue_slack_enabled: bool = Field(default=False, alias="COMMERCIAL_REVENUE_SLACK_ENABLED")
    commercial_revenue_slack_webhook_url: str = Field(default="", alias="COMMERCIAL_REVENUE_SLACK_WEBHOOK_URL")
    commercial_revenue_pagerduty_enabled: bool = Field(default=False, alias="COMMERCIAL_REVENUE_PAGERDUTY_ENABLED")
    commercial_revenue_pagerduty_routing_key: str = Field(default="", alias="COMMERCIAL_REVENUE_PAGERDUTY_ROUTING_KEY")
    commercial_revenue_email_escalation_enabled: bool = Field(default=False, alias="COMMERCIAL_REVENUE_EMAIL_ESCALATION_ENABLED")
    commercial_revenue_email_escalation_recipients: str = Field(default="", alias="COMMERCIAL_REVENUE_EMAIL_ESCALATION_RECIPIENTS")
    commercial_revenue_escalation_cooldown_minutes: int = Field(default=30, alias="COMMERCIAL_REVENUE_ESCALATION_COOLDOWN_MINUTES")
    commercial_revenue_escalation_max_retries: int = Field(default=3, alias="COMMERCIAL_REVENUE_ESCALATION_MAX_RETRIES")
    commercial_reproducibility_enabled: bool = Field(default=True, alias="COMMERCIAL_REPRODUCIBILITY_ENABLED")
    commercial_replay_allow_cross_backend: bool = Field(default=False, alias="COMMERCIAL_REPLAY_ALLOW_CROSS_BACKEND")
    commercial_replay_max_age_days: int = Field(default=30, alias="COMMERCIAL_REPLAY_MAX_AGE_DAYS")
    commercial_replay_capture_prompt_hash_only: bool = Field(default=True, alias="COMMERCIAL_REPLAY_CAPTURE_PROMPT_HASH_ONLY")
    commercial_replay_default_mode: str = Field(default="best_effort", alias="COMMERCIAL_REPLAY_DEFAULT_MODE")

    # Phase 60: Verifiable AI Execution Proofs + Merkle Audit Timelines
    commercial_merkle_timelines_enabled: bool = Field(default=True, alias="COMMERCIAL_MERKLE_TIMELINES_ENABLED")
    commercial_merkle_timeline_window_minutes: int = Field(default=60, alias="COMMERCIAL_MERKLE_TIMELINE_WINDOW_MINUTES")
    commercial_merkle_timeline_auto_seal: bool = Field(default=False, alias="COMMERCIAL_MERKLE_TIMELINE_AUTO_SEAL")
    commercial_execution_proofs_enabled: bool = Field(default=True, alias="COMMERCIAL_EXECUTION_PROOFS_ENABLED")
    commercial_execution_proofs_export_enabled: bool = Field(default=True, alias="COMMERCIAL_EXECUTION_PROOFS_EXPORT_ENABLED")

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
    jwt_secret: str = Field(default="change-me-at-all-costs", alias="JWT_SECRET")
    max_request_body_size_bytes: int = Field(default=1024 * 1024 * 5, alias="MAX_REQUEST_BODY_SIZE_BYTES") # 5MB
    max_tools_per_request: int = Field(default=16, alias="MAX_TOOLS_PER_REQUEST")
    max_tool_schema_bytes: int = Field(default=24 * 1024, alias="MAX_TOOL_SCHEMA_BYTES")
    max_tool_schema_depth: int = Field(default=16, alias="MAX_TOOL_SCHEMA_DEPTH")
    max_tool_schema_properties: int = Field(default=256, alias="MAX_TOOL_SCHEMA_PROPERTIES")
    max_tool_arguments_bytes: int = Field(default=16 * 1024, alias="MAX_TOOL_ARGUMENTS_BYTES")
    tool_argument_preview_chars: int = Field(default=160, alias="TOOL_ARGUMENT_PREVIEW_CHARS")
    abuse_detection_enabled: bool = Field(default=True, alias="ABUSE_DETECTION_ENABLED")
    abuse_auto_suspend_enabled: bool = Field(default=False, alias="ABUSE_AUTO_SUSPEND_ENABLED")
    abuse_dry_run: bool = Field(default=True, alias="ABUSE_DRY_RUN")

    # Tokenizer Settings
    tokenizer_mode: str = Field(default="auto", alias="TOKENIZER_MODE")
    tokenizer_model_path: str | None = Field(default=None, alias="TOKENIZER_MODEL_PATH")
    tokenizer_strict: bool = Field(default=False, alias="TOKENIZER_STRICT")
    tokenizer_cache_enabled: bool = Field(default=True, alias="TOKENIZER_CACHE_ENABLED")

    # Commercial QoS Phase 24
    commercial_qos_priority_queue_enabled: bool = Field(default=False, alias="COMMERCIAL_QOS_PRIORITY_QUEUE_ENABLED")
    commercial_qos_priority_queue_mode: str = Field(default="shadow", alias="COMMERCIAL_QOS_PRIORITY_QUEUE_MODE")
    commercial_qos_queue_aging_seconds: int = Field(default=300, alias="COMMERCIAL_QOS_QUEUE_AGING_SECONDS")
    commercial_qos_max_starvation_seconds: int = Field(default=1800, alias="COMMERCIAL_QOS_MAX_STARVATION_SECONDS")
    
    commercial_qos_rate_limiting_enabled: bool = Field(default=True, alias="COMMERCIAL_QOS_RATE_LIMITING_ENABLED")
    commercial_qos_rate_limit_mode: str = Field(default="report_only", alias="COMMERCIAL_QOS_RATE_LIMIT_MODE")
    commercial_qos_free_rpm: int = Field(default=10, alias="COMMERCIAL_QOS_FREE_RPM")
    commercial_qos_basic_rpm: int = Field(default=60, alias="COMMERCIAL_QOS_BASIC_RPM")
    commercial_qos_pro_rpm: int = Field(default=300, alias="COMMERCIAL_QOS_PRO_RPM")
    commercial_qos_premium_rpm: int = Field(default=1000, alias="COMMERCIAL_QOS_PREMIUM_RPM")
    commercial_qos_enterprise_rpm: int = Field(default=5000, alias="COMMERCIAL_QOS_ENTERPRISE_RPM")

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
    
    # Provider Settings
    providers_enabled: str = Field(default="local,lmstudio", alias="PROVIDERS_ENABLED")
    cloud_providers_enabled: bool = Field(default=False, alias="CLOUD_PROVIDERS_ENABLED")
    openai_provider_enabled: bool = Field(default=False, alias="OPENAI_PROVIDER_ENABLED")
    deepseek_provider_enabled: bool = Field(default=False, alias="DEEPSEEK_PROVIDER_ENABLED")
    anthropic_provider_enabled: bool = Field(default=False, alias="ANTHROPIC_PROVIDER_ENABLED")
    real_provider_validation_enabled: bool = Field(default=False, alias="REAL_PROVIDER_VALIDATION_ENABLED")
    real_provider_max_cost_brl: float = Field(default=2.00, alias="REAL_PROVIDER_MAX_COST_BRL")
    real_provider_log_prompts: bool = Field(default=False, alias="REAL_PROVIDER_LOG_PROMPTS")
    real_provider_store_responses: bool = Field(default=False, alias="REAL_PROVIDER_STORE_RESPONSES")

    # Commercial Guardrails
    commercial_guardrails_enabled: bool = Field(default=False, alias="COMMERCIAL_GUARDRAILS_ENABLED")
    max_global_provider_cost_per_day_brl: float = Field(default=0.0, alias="MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL")
    max_provider_cost_per_day_brl: float = Field(default=0.0, alias="MAX_PROVIDER_COST_PER_DAY_BRL")
    max_client_provider_cost_per_day_brl: float = Field(default=0.0, alias="MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL")
    margin_warning_percent: float = Field(default=20.0, alias="MARGIN_WARNING_PERCENT")
    negative_margin_block_mode: str = Field(default="report_only", alias="NEGATIVE_MARGIN_BLOCK_MODE")
    global_cloud_kill_switch: bool = Field(default=False, alias="GLOBAL_CLOUD_KILL_SWITCH")

    # Commercial Routing Phase 4
    commercial_routing_enabled: bool = Field(default=False, alias="COMMERCIAL_ROUTING_ENABLED")
    commercial_routing_default_policy: str = Field(default="disabled", alias="COMMERCIAL_ROUTING_DEFAULT_POLICY")
    commercial_min_margin_percent: float = Field(default=20.0, alias="COMMERCIAL_MIN_MARGIN_PERCENT")
    commercial_local_route_bonus: float = Field(default=10.0, alias="COMMERCIAL_LOCAL_ROUTE_BONUS")
    commercial_latency_weight: float = Field(default=0.15, alias="COMMERCIAL_LATENCY_WEIGHT")
    commercial_margin_weight: float = Field(default=0.60, alias="COMMERCIAL_MARGIN_WEIGHT")
    commercial_quality_weight: float = Field(default=0.25, alias="COMMERCIAL_QUALITY_WEIGHT")

    # Commercial Calibration Phase 6
    commercial_calibration_enabled: bool = Field(default=False, alias="COMMERCIAL_CALIBRATION_ENABLED")
    commercial_calibration_mode: str = Field(default="recommend_only", alias="COMMERCIAL_CALIBRATION_MODE")
    commercial_calibration_min_samples: int = Field(default=20, alias="COMMERCIAL_CALIBRATION_MIN_SAMPLES")
    commercial_calibration_lookback_days: int = Field(default=7, alias="COMMERCIAL_CALIBRATION_LOOKBACK_DAYS")
    commercial_calibration_max_multiplier: float = Field(default=3.0, alias="COMMERCIAL_CALIBRATION_MAX_MULTIPLIER")
    commercial_calibration_min_multiplier: float = Field(default=0.5, alias="COMMERCIAL_CALIBRATION_MIN_MULTIPLIER")
    commercial_calibration_use_trimmed_mean: bool = Field(default=True, alias="COMMERCIAL_CALIBRATION_USE_TRIMMED_MEAN")
    commercial_calibration_outlier_trim_percent: float = Field(default=5.0, alias="COMMERCIAL_CALIBRATION_OUTLIER_TRIM_PERCENT")
    commercial_calibration_max_recommended_change_percent: float = Field(default=25.0, alias="COMMERCIAL_CALIBRATION_MAX_RECOMMENDED_CHANGE_PERCENT")

    # Commercial Calibration Auto Apply Phase 8
    commercial_calibration_auto_apply: bool = Field(default=False, alias="COMMERCIAL_CALIBRATION_AUTO_APPLY")
    commercial_calibration_auto_apply_mode: str = Field(default="dry_run", alias="COMMERCIAL_CALIBRATION_AUTO_APPLY_MODE")
    commercial_calibration_auto_apply_max_change_percent: float = Field(default=10.0, alias="COMMERCIAL_CALIBRATION_AUTO_APPLY_MAX_CHANGE_PERCENT")
    commercial_calibration_auto_apply_min_confidence: str = Field(default="high", alias="COMMERCIAL_CALIBRATION_AUTO_APPLY_MIN_CONFIDENCE")
    commercial_calibration_auto_apply_min_recent_samples: int = Field(default=20, alias="COMMERCIAL_CALIBRATION_AUTO_APPLY_MIN_RECENT_SAMPLES")
    commercial_calibration_auto_apply_require_24h_data: bool = Field(default=True, alias="COMMERCIAL_CALIBRATION_AUTO_APPLY_REQUIRE_24H_DATA")
    commercial_calibration_auto_apply_rate_limit_minutes: int = Field(default=60, alias="COMMERCIAL_CALIBRATION_AUTO_APPLY_RATE_LIMIT_MINUTES")
    commercial_calibration_canary_default_percent: int = Field(default=5, alias="COMMERCIAL_CALIBRATION_CANARY_DEFAULT_PERCENT")
    commercial_calibration_canary_max_percent: int = Field(default=25, alias="COMMERCIAL_CALIBRATION_CANARY_MAX_PERCENT")

    # Commercial Canary Auto Promotion Phase 9
    commercial_canary_auto_promotion_enabled: bool = Field(default=False, alias="COMMERCIAL_CANARY_AUTO_PROMOTION_ENABLED")
    commercial_canary_auto_promotion_mode: str = Field(default="dry_run", alias="COMMERCIAL_CANARY_AUTO_PROMOTION_MODE")
    commercial_canary_promotion_steps: str = Field(default="5,10,25,50,100", alias="COMMERCIAL_CANARY_PROMOTION_STEPS")
    commercial_canary_min_observation_minutes: int = Field(default=60, alias="COMMERCIAL_CANARY_MIN_OBSERVATION_MINUTES")
    commercial_canary_min_requests_per_step: int = Field(default=100, alias="COMMERCIAL_CANARY_MIN_REQUESTS_PER_STEP")
    commercial_canary_min_margin_percent: float = Field(default=20.0, alias="COMMERCIAL_CANARY_MIN_MARGIN_PERCENT")
    commercial_canary_max_error_rate_percent: float = Field(default=2.0, alias="COMMERCIAL_CANARY_MAX_ERROR_RATE_PERCENT")
    commercial_canary_max_latency_regression_percent: float = Field(default=20.0, alias="COMMERCIAL_CANARY_MAX_LATENCY_REGRESSION_PERCENT")
    commercial_canary_max_estimation_error_percent: float = Field(default=15.0, alias="COMMERCIAL_CANARY_MAX_ESTIMATION_ERROR_PERCENT")
    commercial_canary_auto_rollback_enabled: bool = Field(default=True, alias="COMMERCIAL_CANARY_AUTO_ROLLBACK_ENABLED")

    # Commercial Executive Dashboard Phase 10
    commercial_executive_dashboard_enabled: bool = Field(default=True, alias="COMMERCIAL_EXECUTIVE_DASHBOARD_ENABLED")
    commercial_cost_drift_alert_percent: float = Field(default=20.0, alias="COMMERCIAL_COST_DRIFT_ALERT_PERCENT")
    commercial_margin_drift_alert_percent: float = Field(default=15.0, alias="COMMERCIAL_MARGIN_DRIFT_ALERT_PERCENT")
    commercial_latency_drift_alert_percent: float = Field(default=25.0, alias="COMMERCIAL_LATENCY_DRIFT_ALERT_PERCENT")
    commercial_negative_margin_alert: bool = Field(default=True, alias="COMMERCIAL_NEGATIVE_MARGIN_ALERT")
    commercial_anomaly_lookback_hours: int = Field(default=24, alias="COMMERCIAL_ANOMALY_LOOKBACK_HOURS")
    commercial_report_email_enabled: bool = Field(default=False, alias="COMMERCIAL_REPORT_EMAIL_ENABLED")
    commercial_report_email_mode: str = Field(default="disabled", alias="COMMERCIAL_REPORT_EMAIL_MODE")
    commercial_report_email_provider: str = Field(default="disabled", alias="COMMERCIAL_REPORT_EMAIL_PROVIDER")
    commercial_report_default_recipients: str = Field(default="", alias="COMMERCIAL_REPORT_DEFAULT_RECIPIENTS")
    commercial_report_send_real_email: bool = Field(default=False, alias="COMMERCIAL_REPORT_SEND_REAL_EMAIL")
    commercial_report_smtp_host: str = Field(default="", alias="COMMERCIAL_REPORT_SMTP_HOST")
    commercial_report_smtp_port: int = Field(default=587, alias="COMMERCIAL_REPORT_SMTP_PORT")
    commercial_report_smtp_username: str = Field(default="", alias="COMMERCIAL_REPORT_SMTP_USERNAME")
    commercial_report_smtp_password: str = Field(default="", alias="COMMERCIAL_REPORT_SMTP_PASSWORD")
    commercial_report_smtp_from: str = Field(default="", alias="COMMERCIAL_REPORT_SMTP_FROM")
    commercial_report_smtp_use_tls: bool = Field(default=True, alias="COMMERCIAL_REPORT_SMTP_USE_TLS")
    commercial_report_smtp_use_starttls: bool = Field(default=True, alias="COMMERCIAL_REPORT_SMTP_USE_STARTTLS")
    commercial_report_smtp_timeout_seconds: int = Field(default=15, alias="COMMERCIAL_REPORT_SMTP_TIMEOUT_SECONDS")
    commercial_report_email_allowlist: str = Field(default="", alias="COMMERCIAL_REPORT_EMAIL_ALLOWLIST")
    commercial_report_email_max_recipients: int = Field(default=10, alias="COMMERCIAL_REPORT_EMAIL_MAX_RECIPIENTS")
    commercial_report_email_retry_count: int = Field(default=3, alias="COMMERCIAL_REPORT_EMAIL_RETRY_COUNT")
    commercial_report_email_retry_backoff_seconds: int = Field(default=10, alias="COMMERCIAL_REPORT_EMAIL_RETRY_BACKOFF_SECONDS")
    commercial_distributed_analytics_enabled: bool = Field(default=False, alias="COMMERCIAL_DISTRIBUTED_ANALYTICS_ENABLED")
    node_id: str = Field(default="", alias="NODE_ID")
    node_role: str = Field(default="api", alias="NODE_ROLE")
    cluster_id: str = Field(default="local", alias="CLUSTER_ID")
    commercial_federation_enabled: bool = Field(default=False, alias="COMMERCIAL_FEDERATION_ENABLED")
    commercial_cluster_id: str = Field(default="local", alias="COMMERCIAL_CLUSTER_ID")
    commercial_cluster_region: str = Field(default="local", alias="COMMERCIAL_CLUSTER_REGION")
    commercial_cluster_environment: str = Field(default="local", alias="COMMERCIAL_CLUSTER_ENVIRONMENT")
    commercial_federation_mode: str = Field(default="disabled", alias="COMMERCIAL_FEDERATION_MODE")
    commercial_federation_sync_interval_seconds: int = Field(default=300, alias="COMMERCIAL_FEDERATION_SYNC_INTERVAL_SECONDS")
    commercial_federation_retention_days: int = Field(default=180, alias="COMMERCIAL_FEDERATION_RETENTION_DAYS")
    commercial_federation_allow_push: bool = Field(default=False, alias="COMMERCIAL_FEDERATION_ALLOW_PUSH")
    commercial_federation_require_token: bool = Field(default=True, alias="COMMERCIAL_FEDERATION_REQUIRE_TOKEN")
    commercial_federation_shared_token: str = Field(default="", alias="COMMERCIAL_FEDERATION_SHARED_TOKEN")
    commercial_leader_election_enabled: bool = Field(default=True, alias="COMMERCIAL_LEADER_ELECTION_ENABLED")
    commercial_lease_duration_seconds: int = Field(default=60, alias="COMMERCIAL_LEASE_DURATION_SECONDS")
    commercial_lease_heartbeat_seconds: int = Field(default=15, alias="COMMERCIAL_LEASE_HEARTBEAT_SECONDS")
    commercial_lease_renew_before_seconds: int = Field(default=20, alias="COMMERCIAL_LEASE_RENEW_BEFORE_SECONDS")
    commercial_lease_max_clock_skew_seconds: int = Field(default=5, alias="COMMERCIAL_LEASE_MAX_CLOCK_SKEW_SECONDS")
    commercial_leader_fencing_enabled: bool = Field(default=True, alias="COMMERCIAL_LEADER_FENCING_ENABLED")
    commercial_node_heartbeat_interval_seconds: int = Field(default=30, alias="COMMERCIAL_NODE_HEARTBEAT_INTERVAL_SECONDS")
    commercial_node_offline_after_seconds: int = Field(default=120, alias="COMMERCIAL_NODE_OFFLINE_AFTER_SECONDS")
    commercial_analytics_retention_days: int = Field(default=90, alias="COMMERCIAL_ANALYTICS_RETENTION_DAYS")
    commercial_analytics_aggregation_bucket_minutes: int = Field(default=5, alias="COMMERCIAL_ANALYTICS_AGGREGATION_BUCKET_MINUTES")
    commercial_analytics_dedupe_enabled: bool = Field(default=True, alias="COMMERCIAL_ANALYTICS_DEDUPE_ENABLED")

    # Commercial Global Routing Phase 16
    commercial_global_routing_enabled: bool = Field(default=False, alias="COMMERCIAL_GLOBAL_ROUTING_ENABLED")
    commercial_global_routing_mode: str = Field(default="disabled", alias="COMMERCIAL_GLOBAL_ROUTING_MODE")
    commercial_global_routing_margin_weight: float = Field(default=0.40, alias="COMMERCIAL_GLOBAL_ROUTING_MARGIN_WEIGHT")
    commercial_global_routing_latency_weight: float = Field(default=0.25, alias="COMMERCIAL_GLOBAL_ROUTING_LATENCY_WEIGHT")
    commercial_global_routing_health_weight: float = Field(default=0.15, alias="COMMERCIAL_GLOBAL_ROUTING_HEALTH_WEIGHT")
    commercial_global_routing_region_weight: float = Field(default=0.10, alias="COMMERCIAL_GLOBAL_ROUTING_REGION_WEIGHT")
    commercial_global_routing_priority_weight: float = Field(default=0.10, alias="COMMERCIAL_GLOBAL_ROUTING_PRIORITY_WEIGHT")
    commercial_global_routing_require_healthy_cluster: bool = Field(default=True, alias="COMMERCIAL_GLOBAL_ROUTING_REQUIRE_HEALTHY_CLUSTER")
    commercial_global_routing_allow_cross_region: bool = Field(default=False, alias="COMMERCIAL_GLOBAL_ROUTING_ALLOW_CROSS_REGION")
    commercial_global_routing_max_latency_ms: int = Field(default=5000, alias="COMMERCIAL_GLOBAL_ROUTING_MAX_LATENCY_MS")

    # Commercial Global Traffic Shifting Phase 17
    commercial_global_traffic_shifting_enabled: bool = Field(default=False, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_ENABLED")
    commercial_global_traffic_shifting_mode: str = Field(default="dry_run", alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MODE")
    commercial_global_traffic_shifting_max_canary_percent: int = Field(default=10, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_CANARY_PERCENT")
    commercial_global_traffic_shifting_default_canary_percent: int = Field(default=1, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_DEFAULT_CANARY_PERCENT")
    commercial_global_traffic_shifting_require_healthy_target: bool = Field(default=True, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_REQUIRE_HEALTHY_TARGET")
    commercial_global_traffic_shifting_require_admin_approval: bool = Field(default=True, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_REQUIRE_ADMIN_APPROVAL")
    commercial_global_traffic_shifting_auto_rollback: bool = Field(default=True, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_AUTO_ROLLBACK")
    commercial_global_traffic_shifting_max_error_rate_percent: float = Field(default=2.0, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_ERROR_RATE_PERCENT")
    commercial_global_traffic_shifting_min_margin_percent: float = Field(default=20.0, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MIN_MARGIN_PERCENT")
    commercial_global_traffic_shifting_max_latency_regression_percent: float = Field(default=20.0, alias="COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_LATENCY_REGRESSION_PERCENT")

    # Commercial Cross-Cluster Forwarding Phase 18
    commercial_cross_cluster_forwarding_enabled: bool = Field(default=False, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_ENABLED")
    commercial_cross_cluster_forwarding_mode: str = Field(default="disabled", alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_MODE")
    commercial_cross_cluster_forwarding_timeout_seconds: int = Field(default=2, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_TIMEOUT_SECONDS")
    commercial_cross_cluster_forwarding_stream_timeout_seconds: int = Field(default=30, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_STREAM_TIMEOUT_SECONDS")
    commercial_cross_cluster_forwarding_max_retries: int = Field(default=1, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_MAX_RETRIES")
    commercial_cross_cluster_forwarding_require_mtls: bool = Field(default=False, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_REQUIRE_MTLS")
    commercial_cross_cluster_forwarding_require_jwt: bool = Field(default=True, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_REQUIRE_JWT")
    commercial_cross_cluster_forwarding_circuit_breaker_enabled: bool = Field(default=True, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_ENABLED")
    commercial_cross_cluster_forwarding_circuit_breaker_failure_threshold: int = Field(default=5, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    commercial_cross_cluster_forwarding_circuit_breaker_reset_seconds: int = Field(default=60, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_RESET_SECONDS")
    commercial_cross_cluster_forwarding_max_shifted_percent: int = Field(default=10, alias="COMMERCIAL_CROSS_CLUSTER_FORWARDING_MAX_SHIFTED_PERCENT")

    # Commercial Geo Routing Phase 19
    commercial_geo_routing_enabled: bool = Field(default=False, alias="COMMERCIAL_GEO_ROUTING_ENABLED")
    commercial_geo_routing_mode: str = Field(default="dry_run", alias="COMMERCIAL_GEO_ROUTING_MODE")
    commercial_geo_routing_latency_penalty_weight: float = Field(default=0.35, alias="COMMERCIAL_GEO_ROUTING_LATENCY_PENALTY_WEIGHT")
    commercial_geo_routing_margin_weight: float = Field(default=0.35, alias="COMMERCIAL_GEO_ROUTING_MARGIN_WEIGHT")
    commercial_geo_routing_health_weight: float = Field(default=0.15, alias="COMMERCIAL_GEO_ROUTING_HEALTH_WEIGHT")
    commercial_geo_routing_region_weight: float = Field(default=0.15, alias="COMMERCIAL_GEO_ROUTING_REGION_WEIGHT")
    commercial_geo_routing_allow_cross_ocean: bool = Field(default=False, alias="COMMERCIAL_GEO_ROUTING_ALLOW_CROSS_OCEAN")
    commercial_geo_routing_max_region_distance_km: int = Field(default=5000, alias="COMMERCIAL_GEO_ROUTING_MAX_REGION_DISTANCE_KM")

    # Commercial Live Balancing Phase 19
    commercial_live_balancing_enabled: bool = Field(default=False, alias="COMMERCIAL_LIVE_BALANCING_ENABLED")
    commercial_live_balancing_mode: str = Field(default="dry_run", alias="COMMERCIAL_LIVE_BALANCING_MODE")
    commercial_live_balancing_rebalance_interval_seconds: int = Field(default=300, alias="COMMERCIAL_LIVE_BALANCING_REBALANCE_INTERVAL_SECONDS")
    commercial_live_balancing_max_traffic_change_percent: int = Field(default=5, alias="COMMERCIAL_LIVE_BALANCING_MAX_TRAFFIC_CHANGE_PERCENT")
    commercial_live_balancing_min_margin_percent: float = Field(default=20.0, alias="COMMERCIAL_LIVE_BALANCING_MIN_MARGIN_PERCENT")
    commercial_live_balancing_max_latency_ms: int = Field(default=5000, alias="COMMERCIAL_LIVE_BALANCING_MAX_LATENCY_MS")
    commercial_live_balancing_hysteresis_percent: float = Field(default=10.0, alias="COMMERCIAL_LIVE_BALANCING_HYSTERESIS_PERCENT")
    commercial_live_balancing_min_stable_minutes: int = Field(default=30, alias="COMMERCIAL_LIVE_BALANCING_MIN_STABLE_MINUTES")

    # Commercial Capacity Planning Phase 21
    commercial_capacity_planning_enabled: bool = Field(default=True, alias="COMMERCIAL_CAPACITY_PLANNING_ENABLED")
    commercial_autoscaling_mode: str = Field(default="dry_run", alias="COMMERCIAL_AUTOSCALING_MODE")
    commercial_capacity_forecast_window_minutes: int = Field(default=60, alias="COMMERCIAL_CAPACITY_FORECAST_WINDOW_MINUTES")
    commercial_capacity_snapshot_interval_seconds: int = Field(default=30, alias="COMMERCIAL_CAPACITY_SNAPSHOT_INTERVAL_SECONDS")
    commercial_capacity_retention_days: int = Field(default=30, alias="COMMERCIAL_CAPACITY_RETENTION_DAYS")

    # Commercial Infra Simulation Phase 21.1
    commercial_infra_simulation_enabled: bool = Field(default=True, alias="COMMERCIAL_INFRA_SIMULATION_ENABLED")
    # simulation_only|approval_required|execute_opt_in
    commercial_infra_execution_mode: str = Field(default="simulation_only", alias="COMMERCIAL_INFRA_EXECUTION_MODE")
    commercial_safety_gates_enabled: bool = Field(default=True, alias="COMMERCIAL_SAFETY_GATES_ENABLED")
    
    # Commercial Infra Execution Phase 22
    commercial_infra_execution_enabled: bool = Field(default=False, alias="COMMERCIAL_INFRA_EXECUTION_ENABLED")
    commercial_infra_require_approval: bool = Field(default=True, alias="COMMERCIAL_INFRA_REQUIRE_APPROVAL")
    commercial_infra_require_leader: bool = Field(default=True, alias="COMMERCIAL_INFRA_REQUIRE_LEADER")
    commercial_infra_require_fencing: bool = Field(default=True, alias="COMMERCIAL_INFRA_REQUIRE_FENCING")
    
    # kubernetes,nomad,mock
    commercial_infra_adapters_enabled: str = Field(default="mock", alias="COMMERCIAL_INFRA_ADAPTERS_ENABLED")
    
    commercial_k8s_execution_enabled: bool = Field(default=False, alias="COMMERCIAL_K8S_EXECUTION_ENABLED")
    commercial_k8s_namespace: str = Field(default="default", alias="COMMERCIAL_K8S_NAMESPACE")
    commercial_k8s_context: str = Field(default="", alias="COMMERCIAL_K8S_CONTEXT")
    commercial_k8s_dry_run: bool = Field(default=True, alias="COMMERCIAL_K8S_DRY_RUN")
    
    commercial_nomad_execution_enabled: bool = Field(default=False, alias="COMMERCIAL_NOMAD_EXECUTION_ENABLED")
    commercial_nomad_addr: str = Field(default="", alias="COMMERCIAL_NOMAD_ADDR")
    commercial_nomad_token: str = Field(default="", alias="COMMERCIAL_NOMAD_TOKEN")
    commercial_nomad_dry_run: bool = Field(default=True, alias="COMMERCIAL_NOMAD_DRY_RUN")

    # Proxmox Phase 23
    commercial_proxmox_execution_enabled: bool = Field(default=False, alias="COMMERCIAL_PROXMOX_EXECUTION_ENABLED")
    commercial_proxmox_api_url: str = Field(default="", alias="COMMERCIAL_PROXMOX_API_URL")
    commercial_proxmox_node: str = Field(default="", alias="COMMERCIAL_PROXMOX_NODE")
    commercial_proxmox_token_id: str = Field(default="", alias="COMMERCIAL_PROXMOX_TOKEN_ID")
    commercial_proxmox_token_secret: str = Field(default="", alias="COMMERCIAL_PROXMOX_TOKEN_SECRET")
    commercial_proxmox_verify_tls: bool = Field(default=True, alias="COMMERCIAL_PROXMOX_VERIFY_TLS")
    commercial_proxmox_dry_run: bool = Field(default=True, alias="COMMERCIAL_PROXMOX_DRY_RUN")
    commercial_proxmox_allowed_vm_ids: str = Field(default="", alias="COMMERCIAL_PROXMOX_ALLOWED_VM_IDS")
    commercial_proxmox_allowed_ct_ids: str = Field(default="", alias="COMMERCIAL_PROXMOX_ALLOWED_CT_IDS")

    # Local GPU Phase 23
    commercial_local_gpu_execution_enabled: bool = Field(default=False, alias="COMMERCIAL_LOCAL_GPU_EXECUTION_ENABLED")
    commercial_local_gpu_dry_run: bool = Field(default=True, alias="COMMERCIAL_LOCAL_GPU_DRY_RUN")
    commercial_local_gpu_allowed_actions: str = Field(default="inspect,metrics", alias="COMMERCIAL_LOCAL_GPU_ALLOWED_ACTIONS")
    commercial_local_gpu_allow_power_limit: bool = Field(default=False, alias="COMMERCIAL_LOCAL_GPU_ALLOW_POWER_LIMIT")
    commercial_local_gpu_allow_process_kill: bool = Field(default=False, alias="COMMERCIAL_LOCAL_GPU_ALLOW_PROCESS_KILL")
    commercial_local_gpu_allow_service_restart: bool = Field(default=False, alias="COMMERCIAL_LOCAL_GPU_ALLOW_SERVICE_RESTART")

    # Phase 35: Enterprise Multi-Region Governance Federation
    commercial_governance_federation_enabled: bool = Field(default=False, alias="COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED")
    commercial_governance_federation_mode: str = Field(default="disabled", alias="COMMERCIAL_GOVERNANCE_FEDERATION_MODE")
    commercial_governance_federation_cluster_id: str = Field(default="local", alias="COMMERCIAL_GOVERNANCE_FEDERATION_CLUSTER_ID")
    commercial_governance_federation_region: str = Field(default="local", alias="COMMERCIAL_GOVERNANCE_FEDERATION_REGION")
    commercial_governance_federation_require_signature: bool = Field(default=True, alias="COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_SIGNATURE")
    commercial_governance_federation_require_token: bool = Field(default=True, alias="COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_TOKEN")
    commercial_governance_federation_shared_token: str = Field(default="", alias="COMMERCIAL_GOVERNANCE_FEDERATION_SHARED_TOKEN")
    commercial_governance_federation_sync_interval_seconds: int = Field(default=300, alias="COMMERCIAL_GOVERNANCE_FEDERATION_SYNC_INTERVAL_SECONDS")

    commercial_tenant_encryption_enabled: bool = Field(default=True, alias="COMMERCIAL_TENANT_ENCRYPTION_ENABLED")
    commercial_tenant_encryption_mode: str = Field(default="report_only", alias="COMMERCIAL_TENANT_ENCRYPTION_MODE")
    commercial_tenant_encryption_require_encrypted_exports: bool = Field(default=False, alias="COMMERCIAL_TENANT_ENCRYPTION_REQUIRE_ENCRYPTED_EXPORTS")
    commercial_tenant_encryption_auto_rotation_days: int = Field(default=90, alias="COMMERCIAL_TENANT_ENCRYPTION_AUTO_ROTATION_DAYS")
    commercial_tenant_encryption_block_restricted_exports: bool = Field(default=True, alias="COMMERCIAL_TENANT_ENCRYPTION_BLOCK_RESTRICTED_EXPORTS")
    commercial_tenant_encryption_master_key: str = Field(default="dev-master-key-must-be-32-chars-long!!", alias="COMMERCIAL_TENANT_ENCRYPTION_MASTER_KEY")
    commercial_sovereign_governance_enabled: bool = Field(default=True, alias="COMMERCIAL_SOVEREIGN_GOVERNANCE_ENABLED")
    commercial_airgap_sync_enabled: bool = Field(default=True, alias="COMMERCIAL_AIRGAP_SYNC_ENABLED")
    commercial_airgap_sync_mode: str = Field(default="dry_run", alias="COMMERCIAL_AIRGAP_SYNC_MODE")
    commercial_airgap_require_signature: bool = Field(default=True, alias="COMMERCIAL_AIRGAP_REQUIRE_SIGNATURE")
    commercial_airgap_require_encryption: bool = Field(default=True, alias="COMMERCIAL_AIRGAP_REQUIRE_ENCRYPTION")
    commercial_offline_crl_enabled: bool = Field(default=True, alias="COMMERCIAL_OFFLINE_CRL_ENABLED")
    commercial_hardware_attestation_enabled: bool = Field(default=False, alias="COMMERCIAL_HARDWARE_ATTESTATION_ENABLED")
    commercial_hardware_attestation_mode: str = Field(default="report_only", alias="COMMERCIAL_HARDWARE_ATTESTATION_MODE")

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

    # Phase 58: Hardware-backed Attestation Runtime
    commercial_runtime_attestation_enabled: bool = Field(default=False, alias="COMMERCIAL_RUNTIME_ATTESTATION_ENABLED")
    commercial_runtime_attestation_mode: str = Field(default="report_only", alias="COMMERCIAL_RUNTIME_ATTESTATION_MODE")
    commercial_runtime_attestation_enclave_type: str = Field(default="software_attested", alias="COMMERCIAL_RUNTIME_ATTESTATION_ENCLAVE_TYPE")
    commercial_runtime_attestation_platform_type: str = Field(default="linux_x86_64", alias="COMMERCIAL_RUNTIME_ATTESTATION_PLATFORM_TYPE")
    commercial_runtime_attestation_require_for_sovereign: bool = Field(default=False, alias="COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SOVEREIGN")
    commercial_runtime_attestation_require_for_sensitive_tenants: bool = Field(default=False, alias="COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SENSITIVE_TENANTS")
    commercial_runtime_attestation_min_trust_score: float = Field(default=0.0, alias="COMMERCIAL_RUNTIME_ATTESTATION_MIN_TRUST_SCORE")
    commercial_runtime_attestation_challenge_ttl_seconds: int = Field(default=60, alias="COMMERCIAL_RUNTIME_ATTESTATION_CHALLENGE_TTL_SECONDS")
    commercial_runtime_attestation_evidence_ttl_seconds: int = Field(default=3600, alias="COMMERCIAL_RUNTIME_ATTESTATION_EVIDENCE_TTL_SECONDS")
    commercial_runtime_attestation_max_drift_threshold: float = Field(default=0.1, alias="COMMERCIAL_RUNTIME_ATTESTATION_MAX_DRIFT_THRESHOLD")
    commercial_runtime_attestation_block_untrusted: bool = Field(default=False, alias="COMMERCIAL_RUNTIME_ATTESTATION_BLOCK_UNTRUSTED")
    commercial_runtime_attestation_enforce_on_startup: bool = Field(default=False, alias="COMMERCIAL_RUNTIME_ATTESTATION_ENFORCE_ON_STARTUP")
    commercial_model_supply_chain_enabled: bool = Field(default=True, alias="COMMERCIAL_MODEL_SUPPLY_CHAIN_ENABLED")
    commercial_model_trust_enforcement_mode: str = Field(default="report_only", alias="COMMERCIAL_MODEL_TRUST_ENFORCEMENT_MODE")
    commercial_model_require_trusted_for_routing: bool = Field(default=False, alias="COMMERCIAL_MODEL_REQUIRE_TRUSTED_FOR_ROUTING")
    commercial_model_require_checksum_for_local: bool = Field(default=True, alias="COMMERCIAL_MODEL_REQUIRE_CHECKSUM_FOR_LOCAL")
    commercial_model_quarantine_on_checksum_mismatch: bool = Field(default=True, alias="COMMERCIAL_MODEL_QUARANTINE_ON_CHECKSUM_MISMATCH")
    commercial_model_integrity_monitor_enabled: bool = Field(default=True, alias="COMMERCIAL_MODEL_INTEGRITY_MONITOR_ENABLED")
    commercial_model_integrity_scan_interval_seconds: int = Field(default=3600, alias="COMMERCIAL_MODEL_INTEGRITY_SCAN_INTERVAL_SECONDS")

    # Phase 41: Cryptographic Inference Receipts
    commercial_receipts_enabled: bool = Field(default=True, alias="COMMERCIAL_RECEIPTS_ENABLED")
    commercial_receipts_chaining_enabled: bool = Field(default=True, alias="COMMERCIAL_RECEIPTS_CHAINING_ENABLED")
    commercial_receipts_timestamp_mode: str = Field(default="local", alias="COMMERCIAL_RECEIPTS_TIMESTAMP_MODE")
    commercial_receipts_export_enabled: bool = Field(default=True, alias="COMMERCIAL_RECEIPTS_EXPORT_ENABLED")
    commercial_receipts_signature_required: bool = Field(default=False, alias="COMMERCIAL_RECEIPTS_SIGNATURE_REQUIRED")
    commercial_receipt_signature_algorithm: str = Field(default="ed25519_placeholder", alias="COMMERCIAL_RECEIPT_SIGNATURE_ALGORITHM")
    commercial_model_integrity_auto_quarantine: bool = Field(default=False, alias="COMMERCIAL_MODEL_INTEGRITY_AUTO_QUARANTINE")
    commercial_model_integrity_boot_scan_enabled: bool = Field(default=True, alias="COMMERCIAL_MODEL_INTEGRITY_BOOT_SCAN_ENABLED")

    # Phase 59: Offline Sovereign Model Lifecycle Management
    commercial_model_lifecycle_enabled: bool = Field(default=True, alias="COMMERCIAL_MODEL_LIFECYCLE_ENABLED")
    commercial_model_lifecycle_mode: str = Field(default="report_only", alias="COMMERCIAL_MODEL_LIFECYCLE_MODE")
    commercial_model_lifecycle_require_approval: bool = Field(default=True, alias="COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_APPROVAL")
    commercial_model_lifecycle_require_lineage: bool = Field(default=True, alias="COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_LINEAGE")
    commercial_model_lifecycle_require_checksum: bool = Field(default=True, alias="COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_CHECKSUM")
    commercial_model_lifecycle_auto_quarantine: bool = Field(default=False, alias="COMMERCIAL_MODEL_LIFECYCLE_AUTO_QUARANTINE")
    commercial_model_lifecycle_offline_verification_strict: bool = Field(default=True, alias="COMMERCIAL_MODEL_LIFECYCLE_OFFLINE_VERIFICATION_STRICT")
    commercial_sovereign_lifecycle_enforce: bool = Field(default=False, alias="COMMERCIAL_SOVEREIGN_LIFECYCLE_ENFORCE")
    commercial_sovereign_lifecycle_block_unapproved: bool = Field(default=False, alias="COMMERCIAL_SOVEREIGN_LIFECYCLE_BLOCK_UNAPPROVED")

    # low|medium|high|critical
    commercial_max_blast_radius: str = Field(default="medium", alias="COMMERCIAL_MAX_BLAST_RADIUS")
    commercial_require_approval_for_critical: bool = Field(default=True, alias="COMMERCIAL_REQUIRE_APPROVAL_FOR_CRITICAL")
    commercial_max_autoscaling_cost_increase_percent: float = Field(default=20.0, alias="COMMERCIAL_MAX_AUTOSCALING_COST_INCREASE_PERCENT")
    commercial_max_autoscaling_margin_drop_percent: float = Field(default=10.0, alias="COMMERCIAL_MAX_AUTOSCALING_MARGIN_DROP_PERCENT")
    commercial_max_autoscaling_sla_risk_percent: float = Field(default=5.0, alias="COMMERCIAL_MAX_AUTOSCALING_SLA_RISK_PERCENT")

    commercial_sla_risk_alert_percent: float = Field(default=5.0, alias="COMMERCIAL_SLA_RISK_ALERT_PERCENT")
    commercial_queue_depth_alert: int = Field(default=100, alias="COMMERCIAL_QUEUE_DEPTH_ALERT")
    commercial_p95_latency_alert_ms: int = Field(default=5000, alias="COMMERCIAL_P95_LATENCY_ALERT_MS")
    commercial_gpu_utilization_alert_percent: float = Field(default=90.0, alias="COMMERCIAL_GPU_UTILIZATION_ALERT_PERCENT")

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
    provider_timeout_seconds: int = Field(
        default=30,
        validation_alias=AliasChoices("PROVIDER_TIMEOUT_SECONDS", "REAL_PROVIDER_TIMEOUT_SECONDS"),
    )
    provider_max_retries: int = Field(default=2, alias="PROVIDER_MAX_RETRIES")
    provider_fail_closed: bool = Field(default=True, alias="PROVIDER_FAIL_CLOSED")
    routing_test_force_local_failure: bool = Field(default=False, alias="ROUTING_TEST_FORCE_LOCAL_FAILURE")

    # Optional payment adapters for wallet top-ups. Disabled by default to keep local/offline mode independent of PSPs.
    payment_provider: str = Field(default="disabled", alias="PAYMENT_PROVIDER")
    payment_webhook_secret: str = Field(default="", alias="PAYMENT_WEBHOOK_SECRET")
    payment_real_enabled: bool = Field(default=False, alias="PAYMENT_REAL_ENABLED")

    # RAG Settings
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    rag_storage_dir: str = Field(default="./data/rag_uploads", alias="RAG_STORAGE_DIR")
    rag_max_file_mb: int = Field(default=25, alias="RAG_MAX_FILE_MB")
    rag_chunk_size: int = Field(default=1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, alias="RAG_CHUNK_OVERLAP")
    rag_top_k_default: int = Field(default=5, alias="RAG_TOP_K_DEFAULT")
    rag_embedding_provider: str = Field(default="local", alias="RAG_EMBEDDING_PROVIDER")
    rag_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="RAG_EMBEDDING_MODEL")
    commercial_rag_vault_enabled: bool = Field(default=False, alias="COMMERCIAL_RAG_VAULT_ENABLED")
    commercial_rag_policy_mode: str = Field(default="report_only", alias="COMMERCIAL_RAG_POLICY_MODE")
    commercial_rag_require_confidential_runtime: bool = Field(default=False, alias="COMMERCIAL_RAG_REQUIRE_CONFIDENTIAL_RUNTIME")
    commercial_rag_require_signed_documents: bool = Field(default=False, alias="COMMERCIAL_RAG_REQUIRE_SIGNED_DOCUMENTS")
    commercial_rag_max_context_chunks: int = Field(default=20, alias="COMMERCIAL_RAG_MAX_CONTEXT_CHUNKS")
    commercial_rag_enable_poison_detection: bool = Field(default=True, alias="COMMERCIAL_RAG_ENABLE_POISON_DETECTION")
    commercial_rag_enable_immutable_audit: bool = Field(default=True, alias="COMMERCIAL_RAG_ENABLE_IMMUTABLE_AUDIT")

    @model_validator(mode="after")
    def validate_appliance_mode(self) -> "Settings":
        valid_report_email_modes = {"disabled", "dry_run", "smtp"}
        if self.commercial_report_email_mode not in valid_report_email_modes:
            self.commercial_report_email_mode = "disabled"
        if self.commercial_report_smtp_port <= 0:
            self.commercial_report_smtp_port = 587
        if self.commercial_report_smtp_timeout_seconds <= 0:
            self.commercial_report_smtp_timeout_seconds = 15
        if self.commercial_report_email_max_recipients <= 0:
            self.commercial_report_email_max_recipients = 10
        if self.commercial_report_email_retry_count < 0:
            self.commercial_report_email_retry_count = 3
        if self.commercial_report_email_retry_backoff_seconds < 0:
            self.commercial_report_email_retry_backoff_seconds = 10
        if self.commercial_node_heartbeat_interval_seconds <= 0:
            self.commercial_node_heartbeat_interval_seconds = 30
        if self.commercial_lease_duration_seconds <= 0:
            self.commercial_lease_duration_seconds = 60
        if self.commercial_lease_heartbeat_seconds <= 0:
            self.commercial_lease_heartbeat_seconds = min(15, self.commercial_lease_duration_seconds)
        if self.commercial_lease_renew_before_seconds <= 0:
            self.commercial_lease_renew_before_seconds = min(20, self.commercial_lease_duration_seconds // 2 or 1)
        if self.commercial_lease_renew_before_seconds >= self.commercial_lease_duration_seconds:
            self.commercial_lease_renew_before_seconds = max(1, self.commercial_lease_duration_seconds // 3)
        if self.commercial_lease_max_clock_skew_seconds < 0:
            self.commercial_lease_max_clock_skew_seconds = 5
        if self.commercial_node_offline_after_seconds <= 0:
            self.commercial_node_offline_after_seconds = 120
        if self.commercial_analytics_retention_days <= 0:
            self.commercial_analytics_retention_days = 90
        if self.commercial_analytics_aggregation_bucket_minutes <= 0:
            self.commercial_analytics_aggregation_bucket_minutes = 5
        if self.commercial_federation_sync_interval_seconds <= 0:
            self.commercial_federation_sync_interval_seconds = 300
        if self.commercial_federation_retention_days <= 0:
            self.commercial_federation_retention_days = 180
        valid_node_roles = {"api", "worker", "scheduler", "router", "unknown"}
        if self.node_role not in valid_node_roles:
            self.node_role = "unknown"
        if not self.cluster_id.strip():
            self.cluster_id = "local"
        if not self.commercial_cluster_id.strip():
            self.commercial_cluster_id = "local"
        valid_cluster_envs = {"local", "staging", "production", "edge"}
        if self.commercial_cluster_environment not in valid_cluster_envs:
            self.commercial_cluster_environment = "local"
        valid_federation_modes = {"disabled", "local_only", "pull", "push", "hybrid"}
        if self.commercial_federation_mode not in valid_federation_modes:
            self.commercial_federation_mode = "disabled"
        if not self.commercial_federation_enabled:
            self.commercial_federation_mode = "disabled"
        if self.commercial_federation_mode in {"disabled", "local_only"}:
            self.commercial_federation_allow_push = False

        valid_global_routing_modes = {"disabled", "dry_run"}
        if self.commercial_global_routing_mode not in valid_global_routing_modes:
            self.commercial_global_routing_mode = "disabled"
        if not self.commercial_global_routing_enabled:
            self.commercial_global_routing_mode = "disabled"

        valid_geo_routing_modes = {"disabled", "dry_run", "recommend_only", "balancing"}
        if self.commercial_geo_routing_mode not in valid_geo_routing_modes:
            self.commercial_geo_routing_mode = "dry_run"
        if not self.commercial_geo_routing_enabled:
            self.commercial_geo_routing_mode = "disabled"

        valid_live_balancing_modes = {"disabled", "dry_run", "recommend_only", "balancing"}
        if self.commercial_live_balancing_mode not in valid_live_balancing_modes:
            self.commercial_live_balancing_mode = "dry_run"
        if not self.commercial_live_balancing_enabled:
            self.commercial_live_balancing_mode = "disabled"

        valid_autoscaling_modes = {"disabled", "recommend_only", "dry_run"}
        if self.commercial_autoscaling_mode not in valid_autoscaling_modes:
            self.commercial_autoscaling_mode = "dry_run"
        if not self.commercial_capacity_planning_enabled:
            self.commercial_autoscaling_mode = "disabled"

        valid_infra_execution_modes = {"simulation_only", "approval_required", "execute_opt_in"}
        if self.commercial_infra_execution_mode not in valid_infra_execution_modes:
            self.commercial_infra_execution_mode = "simulation_only"
        
        if not self.commercial_infra_execution_enabled:
            self.commercial_infra_execution_mode = "simulation_only"

        valid_qos_billing_modes = {"disabled", "report_only", "invoice_line_item", "wallet_debit_opt_in"}
        if self.commercial_qos_billing_mode not in valid_qos_billing_modes:
            self.commercial_qos_billing_mode = "report_only"
        
        if not self.commercial_qos_billing_enabled:
            self.commercial_qos_billing_mode = "disabled"

        valid_revenue_protection_modes = {"disabled", "report_only", "approval_required", "enforce"}
        if self.commercial_revenue_protection_mode not in valid_revenue_protection_modes:
            self.commercial_revenue_protection_mode = "report_only"
        if not self.commercial_revenue_protection_enabled:
            self.commercial_revenue_protection_mode = "disabled"
        if self.commercial_revenue_protection_cooldown_minutes <= 0:
            self.commercial_revenue_protection_cooldown_minutes = 60
        valid_compliance_modes = {"disabled", "report_only", "enforce"}
        if self.commercial_compliance_mode not in valid_compliance_modes:
            self.commercial_compliance_mode = "report_only"
        if not self.commercial_compliance_controls_enabled:
            self.commercial_compliance_mode = "disabled"
        if self.commercial_compliance_default_approver_count <= 0:
            self.commercial_compliance_default_approver_count = 1
        valid_revenue_escalation_modes = {"disabled", "dry_run", "enabled"}
        if self.commercial_revenue_escalations_mode not in valid_revenue_escalation_modes:
            self.commercial_revenue_escalations_mode = "dry_run"
        if not self.commercial_revenue_escalations_enabled:
            self.commercial_revenue_escalations_mode = "disabled"
        if self.commercial_revenue_escalation_cooldown_minutes <= 0:
            self.commercial_revenue_escalation_cooldown_minutes = 30
        if self.commercial_revenue_escalation_max_retries < 0:
            self.commercial_revenue_escalation_max_retries = 0

        valid_gov_federation_modes = {"disabled", "manual", "pull", "push", "hybrid"}
        if self.commercial_governance_federation_mode not in valid_gov_federation_modes:
            self.commercial_governance_federation_mode = "disabled"
        if not self.commercial_governance_federation_enabled:
            self.commercial_governance_federation_mode = "disabled"
        if self.commercial_governance_federation_sync_interval_seconds <= 0:
            self.commercial_governance_federation_sync_interval_seconds = 300
        if not self.commercial_governance_federation_cluster_id.strip():
            self.commercial_governance_federation_cluster_id = "local"
        valid_sovereign_modes = {"disabled", "dry_run", "enforce", "report_only"}
        if self.commercial_airgap_sync_mode not in valid_sovereign_modes:
            self.commercial_airgap_sync_mode = "dry_run"
        if not self.commercial_airgap_sync_enabled:
            self.commercial_airgap_sync_mode = "disabled"
        if self.commercial_hardware_attestation_mode not in valid_sovereign_modes:
            self.commercial_hardware_attestation_mode = "report_only"
        if not self.commercial_hardware_attestation_enabled:
            self.commercial_hardware_attestation_mode = "report_only"

        valid_runtime_attestation_modes = {"disabled", "report_only", "enforce", "audit_only"}
        if self.commercial_runtime_attestation_mode not in valid_runtime_attestation_modes:
            self.commercial_runtime_attestation_mode = "report_only"
        if not self.commercial_runtime_attestation_enabled:
            self.commercial_runtime_attestation_mode = "disabled"
        valid_enclave_types = {"software_attested", "tpm_placeholder", "sev_placeholder", "sgx_placeholder", "vbs_placeholder"}
        if self.commercial_runtime_attestation_enclave_type not in valid_enclave_types:
            self.commercial_runtime_attestation_enclave_type = "software_attested"
        if self.commercial_runtime_attestation_min_trust_score < 0:
            self.commercial_runtime_attestation_min_trust_score = 0.0
        if self.commercial_runtime_attestation_min_trust_score > 1:
            self.commercial_runtime_attestation_min_trust_score = 1.0
        if self.commercial_runtime_attestation_challenge_ttl_seconds <= 0:
            self.commercial_runtime_attestation_challenge_ttl_seconds = 60
        if self.commercial_runtime_attestation_evidence_ttl_seconds <= 0:
            self.commercial_runtime_attestation_evidence_ttl_seconds = 3600
        if self.commercial_runtime_attestation_max_drift_threshold < 0:
            self.commercial_runtime_attestation_max_drift_threshold = 0.1
        valid_model_supply_chain_modes = {"disabled", "report_only", "enforce"}
        if self.commercial_model_trust_enforcement_mode not in valid_model_supply_chain_modes:
            self.commercial_model_trust_enforcement_mode = "report_only"
        if not self.commercial_model_supply_chain_enabled:
            self.commercial_model_trust_enforcement_mode = "disabled"
        if self.commercial_model_integrity_scan_interval_seconds <= 0:
            self.commercial_model_integrity_scan_interval_seconds = 3600
        if not self.commercial_model_supply_chain_enabled:
            self.commercial_model_integrity_monitor_enabled = False

        valid_lifecycle_modes = {"disabled", "report_only", "enforce"}
        if self.commercial_model_lifecycle_mode not in valid_lifecycle_modes:
            self.commercial_model_lifecycle_mode = "report_only"
        if not self.commercial_model_lifecycle_enabled:
            self.commercial_model_lifecycle_mode = "disabled"

        if self.commercial_capacity_forecast_window_minutes <= 0:
            self.commercial_capacity_forecast_window_minutes = 60
        if self.commercial_capacity_snapshot_interval_seconds <= 0:
            self.commercial_capacity_snapshot_interval_seconds = 30
        if self.commercial_capacity_retention_days <= 0:
            self.commercial_capacity_retention_days = 30

        valid_negative_margin_modes = {"disabled", "report_only", "enforce_cloud_only", "enforcing_ready"}
        if self.negative_margin_block_mode == "enforcing_ready":
            self.negative_margin_block_mode = "enforce_cloud_only"
        elif self.negative_margin_block_mode not in valid_negative_margin_modes:
            self.negative_margin_block_mode = "report_only"

        valid_deployment_modes = {"appliance", "saas", "managed_control_plane", "hybrid"}
        if self.deployment_mode not in valid_deployment_modes:
            self.deployment_mode = "appliance"
        if not self.distributed_runtime_enabled:
            self.gpu_autoscaling_enabled = False
        if self.deployment_mode == "appliance":
            self.managed_control_plane_enabled = False

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
            
        valid_witness_modes = {"disabled", "dry_run", "enforce"}
        if self.commercial_witness_mode not in valid_witness_modes:
            self.commercial_witness_mode = "dry_run"
        if not self.commercial_witness_federation_enabled:
            self.commercial_witness_mode = "disabled"
        if self.commercial_witness_min_signatures < 0:
            self.commercial_witness_min_signatures = 1

        valid_transparency_modes = {"disabled", "dry_run", "enforce"}
        if self.commercial_transparency_gossip_mode not in valid_transparency_modes:
            self.commercial_transparency_gossip_mode = "dry_run"
        if not self.commercial_transparency_gossip_enabled:
            self.commercial_transparency_gossip_mode = "disabled"
        if self.commercial_transparency_checkpoint_interval_minutes <= 0:
            self.commercial_transparency_checkpoint_interval_minutes = 60

        valid_attestation_modes = {"disabled", "local_only", "authenticated", "public_readonly"}
        if self.commercial_public_attestation_mode not in valid_attestation_modes:
            self.commercial_public_attestation_mode = "local_only"
        if not self.commercial_public_attestation_gateway_enabled:
            self.commercial_public_attestation_mode = "disabled"
        if self.commercial_public_attestation_rate_limit_rpm <= 0:
            self.commercial_public_attestation_rate_limit_rpm = 60

        valid_confidential_modes = {"disabled", "report_only", "enforce"}
        if self.commercial_confidential_runtime_mode not in valid_confidential_modes:
            self.commercial_confidential_runtime_mode = "report_only"
        if not self.commercial_confidential_runtime_enabled:
            self.commercial_confidential_runtime_mode = "disabled"
        if self.commercial_confidential_default_retention_seconds < 0:
            self.commercial_confidential_default_retention_seconds = 0

        valid_agent_modes = {"disabled", "audit_only", "enforce"}
        if self.commercial_agent_governance_mode not in valid_agent_modes:
            self.commercial_agent_governance_mode = "audit_only"
        if not self.commercial_agent_governance_enabled:
            self.commercial_agent_governance_mode = "disabled"
        if self.commercial_agent_default_delegation_limit < 0:
            self.commercial_agent_default_delegation_limit = 3

        if self.commercial_workflow_checkpoint_frequency < 1:
            self.commercial_workflow_checkpoint_frequency = 1
        if self.commercial_workflow_drift_threshold < 0:
            self.commercial_workflow_drift_threshold = 0.01

        valid_tiers = {"airgap", "government", "defense", "regulated"}
        if self.commercial_appliance_deployment_tier not in valid_tiers:
            self.commercial_appliance_deployment_tier = "regulated"
        if not self.commercial_appliance_id:
            self.commercial_appliance_id = "appliance-000"

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
