from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Owner: agent-platform
    # Status: beta
    agent_bundle_signature_required: bool = Field(default=True, alias="AGENT_BUNDLE_SIGNATURE_REQUIRED")
    agent_internal_bundle_signature_required_in_production: bool = Field(default=True, alias="AGENT_INTERNAL_BUNDLE_SIGNATURE_REQUIRED_IN_PRODUCTION")
    allow_unsigned_internal_bundles: bool = Field(default=False, alias="ALLOW_UNSIGNED_INTERNAL_BUNDLES")
    # Owner: agent-platform
    # Status: beta
    agent_optimizer_enabled: bool = Field(default=False, alias="AGENT_OPTIMIZER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_cognitive_loopback_enabled: bool = Field(default=True, alias="AGENT_COGNITIVE_LOOPBACK_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_fewshot_auto_curator_enabled: bool = Field(default=False, alias="AGENT_FEWSHOT_AUTO_CURATOR_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_feedback_learning_enabled: bool = Field(default=False, alias="AGENT_FEEDBACK_LEARNING_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_auto_apply_learnings: bool = Field(default=True, alias="AGENT_AUTO_APPLY_LEARNINGS")
    # Owner: agent-platform
    # Status: beta
    agent_uncertainty_detection_enabled: bool = Field(default=True, alias="AGENT_UNCERTAINTY_DETECTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_uncertainty_auto_research_enabled: bool = Field(default=False, alias="AGENT_UNCERTAINTY_AUTO_RESEARCH_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_uncertainty_hitl_enabled: bool = Field(default=True, alias="AGENT_UNCERTAINTY_HITL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_meta_reviewer_enabled: bool = Field(default=False, alias="AGENT_META_REVIEWER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_meta_reviewer_blocking_mode: bool = Field(default=False, alias="AGENT_META_REVIEWER_BLOCKING_MODE")
    # Owner: agent-platform
    # Status: beta
    agent_meta_reviewer_parallel_enabled: bool = Field(default=False, alias="AGENT_META_REVIEWER_PARALLEL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_studio_ga_enabled: bool = Field(default=True, alias="AGENT_STUDIO_GA_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_visual_flow_editor_enabled: bool = Field(default=False, alias="AGENT_VISUAL_FLOW_EDITOR_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_flow_compiler_enabled: bool = Field(default=False, alias="AGENT_FLOW_COMPILER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_time_travel_debugger_enabled: bool = Field(default=False, alias="AGENT_TIME_TRAVEL_DEBUGGER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_replay_enabled: bool = Field(default=False, alias="AGENT_REPLAY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_replay_from_step_enabled: bool = Field(default=False, alias="AGENT_REPLAY_FROM_STEP_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_debug_state_editing_enabled: bool = Field(default=False, alias="AGENT_DEBUG_STATE_EDITING_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_shadow_mode_enabled: bool = Field(default=False, alias="AGENT_SHADOW_MODE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_canary_agents_enabled: bool = Field(default=True, alias="AGENT_CANARY_AGENTS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_canary_auto_promote: bool = Field(default=False, alias="AGENT_CANARY_AUTO_PROMOTE")
    # Owner: agent-platform
    # Status: beta
    agent_wallets_enabled: bool = Field(default=True, alias="AGENT_WALLETS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_wallet_stripe_enabled: bool = Field(default=False, alias="AGENT_WALLET_STRIPE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_wallet_web3_enabled: bool = Field(default=False, alias="AGENT_WALLET_WEB3_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_wallet_external_spend_enabled: bool = Field(default=False, alias="AGENT_WALLET_EXTERNAL_SPEND_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_digital_twins_enabled: bool = Field(default=False, alias="AGENT_DIGITAL_TWINS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_iot_connectors_enabled: bool = Field(default=False, alias="AGENT_IOT_CONNECTORS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_physical_actuation_enabled: bool = Field(default=False, alias="AGENT_PHYSICAL_ACTUATION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_sab_enabled: bool = Field(default=True, alias="AGENT_SAB_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_sab_import_enabled: bool = Field(default=False, alias="AGENT_SAB_IMPORT_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_sab_export_enabled: bool = Field(default=False, alias="AGENT_SAB_EXPORT_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_planner_real_execution_enabled: bool = Field(default=False, alias="AGENT_PLANNER_REAL_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_task_mock_mode: bool = Field(default=False, alias="AGENT_TASK_MOCK_MODE")
    # Owner: agent-platform
    # Status: beta
    agent_task_dry_run_mode: bool = Field(default=False, alias="AGENT_TASK_DRY_RUN_MODE")
    # Owner: agent-platform
    # Status: beta
    agent_task_simulation_mode: bool = Field(default=False, alias="AGENT_TASK_SIMULATION_MODE")
    # Owner: agent-platform
    # Status: beta
    agent_federated_memory_enabled: bool = Field(default=False, alias="AGENT_FEDERATED_MEMORY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_federated_memory_sync_enabled: bool = Field(default=False, alias="AGENT_FEDERATED_MEMORY_SYNC_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_federated_memory_raw_data_sync: bool = Field(default=False, alias="AGENT_FEDERATED_MEMORY_RAW_DATA_SYNC")
    # Owner: agent-platform
    # Status: experimental
    agent_mcts_reasoning_enabled: bool = Field(default=False, alias="AGENT_MCTS_REASONING_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_mcts_sandbox_simulation_enabled: bool = Field(default=False, alias="AGENT_MCTS_SANDBOX_SIMULATION_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_constraint_reasoning_enabled: bool = Field(default=False, alias="AGENT_CONSTRAINT_REASONING_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_z3_solver_enabled: bool = Field(default=False, alias="AGENT_Z3_SOLVER_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_glpk_solver_enabled: bool = Field(default=False, alias="AGENT_GLPK_SOLVER_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_optimizer_tournaments_enabled: bool = Field(default=False, alias="AGENT_OPTIMIZER_TOURNAMENTS_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_optimizer_parallel_evals_enabled: bool = Field(default=False, alias="AGENT_OPTIMIZER_PARALLEL_EVALS_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_optimizer_apply_winner_enabled: bool = Field(default=False, alias="AGENT_OPTIMIZER_APPLY_WINNER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_auto_optimization_enabled: bool = Field(default=False, alias="AGENT_AUTO_OPTIMIZATION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_optimization_apply_enabled: bool = Field(default=False, alias="AGENT_OPTIMIZATION_APPLY_ENABLED")


    agent_memory_enabled: bool = Field(default=False, alias="AGENT_MEMORY_ENABLED")

    multimodal_enabled: bool = Field(default=False, alias="MULTIMODAL_ENABLED")
    vision_input_enabled: bool = Field(default=False, alias="VISION_INPUT_ENABLED")
    image_generation_enabled: bool = Field(default=False, alias="IMAGE_GENERATION_ENABLED")
    speech_to_text_enabled: bool = Field(default=False, alias="SPEECH_TO_TEXT_ENABLED")
    realtime_audio_enabled: bool = Field(default=False, alias="REALTIME_AUDIO_ENABLED")
    document_vision_enabled: bool = Field(default=False, alias="DOCUMENT_VISION_ENABLED")

    agent_web_search_enabled: bool = Field(default=False, alias="AGENT_WEB_SEARCH_ENABLED")
    agent_web_search_external_network_enabled: bool = Field(default=False, alias="AGENT_WEB_SEARCH_EXTERNAL_NETWORK_ENABLED")
    agent_web_search_allowlist_enabled: bool = Field(default=True, alias="AGENT_WEB_SEARCH_ALLOWLIST_ENABLED")

    mlops_enabled: bool = Field(default=False, alias="MLOPS_ENABLED")
    fine_tuning_enabled: bool = Field(default=False, alias="FINE_TUNING_ENABLED")
    experiment_tracking_enabled: bool = Field(default=False, alias="EXPERIMENT_TRACKING_ENABLED")
    mlflow_integration_enabled: bool = Field(default=False, alias="MLFLOW_INTEGRATION_ENABLED")
    wandb_integration_enabled: bool = Field(default=False, alias="WANDB_INTEGRATION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_cognitive_memory_enabled: bool = Field(default=False, alias="AGENT_COGNITIVE_MEMORY_ENABLED")
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
    agent_semantic_memory_enabled: bool = Field(default=False, alias="AGENT_SEMANTIC_MEMORY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_memory_vector_provider: str = Field(default="mock", alias="AGENT_MEMORY_VECTOR_PROVIDER")
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-east-1-aws", alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="agent-memory", alias="PINECONE_INDEX_NAME")
    # Owner: agent-platform
    # Status: beta
    agent_memory_embeddings_provider: str = Field(default="mock", alias="AGENT_MEMORY_EMBEDDINGS_PROVIDER")
    # Owner: agent-platform
    # Status: beta
    agent_memory_context_injection_enabled: bool = Field(default=False, alias="AGENT_MEMORY_CONTEXT_INJECTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_saas_connectors_enabled: bool = Field(default=False, alias="AGENT_SAAS_CONNECTORS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_connector_mode: str = Field(default="mock", alias="AGENT_CONNECTOR_MODE")
    # Owner: agent-platform
    # Status: beta
    agent_connector_write_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_WRITE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_connector_external_network_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_connector_real_http_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_REAL_HTTP_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_github_connector_enabled: bool = Field(default=False, alias="AGENT_GITHUB_CONNECTOR_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_human_approval_enabled: bool = Field(default=False, alias="AGENT_HUMAN_APPROVAL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_iam_enabled: bool = Field(default=False, alias="AGENT_IAM_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_assistants_api_enabled: bool = Field(default=False, alias="AGENT_ASSISTANTS_API_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_batch_api_enabled: bool = Field(default=False, alias="AGENT_BATCH_API_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_planning_enabled: bool = Field(default=False, alias="AGENT_PLANNING_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_plan_execution_enabled: bool = Field(default=False, alias="AGENT_PLAN_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_runtime_enabled: bool = Field(default=False, alias="AGENT_RUNTIME_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_execution_enabled: bool = Field(default=False, alias="AGENT_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_worker_enabled: bool = Field(default=False, alias="AGENT_WORKER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_embedded_worker_enabled: bool = Field(default=False, alias="AGENT_EMBEDDED_WORKER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_tool_adapters_enabled: bool = Field(default=False, alias="AGENT_TOOL_ADAPTERS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_evals_enabled: bool = Field(default=False, alias="AGENT_EVALS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_eval_provider: str = Field(default="mock", alias="AGENT_EVAL_PROVIDER")
    # Owner: agent-platform
    # Status: beta
    agent_eval_allow_mock_for_promotion: bool = Field(default=False, alias="AGENT_EVAL_ALLOW_MOCK_FOR_PROMOTION")
    # Owner: agent-platform
    # Status: beta
    agent_eval_real_provider_enabled: bool = Field(default=False, alias="AGENT_EVAL_REAL_PROVIDER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_eval_gate_strict: bool = Field(default=True, alias="AGENT_EVAL_GATE_STRICT")
    # Owner: agent-platform
    # Status: beta
    agent_production_requires_eval_baseline: bool = Field(default=True, alias="AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE")
    # Owner: agent-platform
    # Status: beta
    agent_promotion_requires_evals: bool = Field(default=False, alias="AGENT_PROMOTION_REQUIRES_EVALS")
    # Owner: agent-platform
    # Status: beta
    agent_eval_regression_gate_enabled: bool = Field(default=True, alias="AGENT_EVAL_REGRESSION_GATE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_real_provider_validation_enabled: bool = Field(default=False, alias="AGENT_REAL_PROVIDER_VALIDATION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agentic_router_v2_enabled: bool = Field(default=False, alias="AGENTIC_ROUTER_V2_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_reasoning_loop_enabled: bool = Field(default=False, alias="AGENT_REASONING_LOOP_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_plan_and_solve_enabled: bool = Field(default=False, alias="AGENT_PLAN_AND_SOLVE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_react_loop_enabled: bool = Field(default=False, alias="AGENT_REACT_LOOP_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_tool_execution_enabled: bool = Field(default=False, alias="AGENT_TOOL_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_destructive_tools_enabled: bool = Field(default=False, alias="AGENT_DESTRUCTIVE_TOOLS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_async_execution_enabled: bool = Field(default=False, alias="AGENT_ASYNC_EXECUTION_ENABLED")
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
    agent_tool_registry_enabled: bool = Field(default=False, alias="AGENT_TOOL_REGISTRY_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_execution_plane_enabled: bool = Field(default=False, alias="AGENT_EXECUTION_PLANE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_queue_backpressure_enabled: bool = Field(default=False, alias="AGENT_QUEUE_BACKPRESSURE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_context_compression_enabled: bool = Field(default=False, alias="AGENT_CONTEXT_COMPRESSION_ENABLED")
    
    agent_task_simulation_mode: bool = Field(default=False, alias="AGENT_TASK_SIMULATION_MODE")
    agent_task_mock_mode: bool = Field(default=False, alias="AGENT_TASK_MOCK_MODE")
    agent_task_dry_run_mode: bool = Field(default=False, alias="AGENT_TASK_DRY_RUN_MODE")
    agent_executor_mock_mode: bool = Field(default=False, alias="AGENT_EXECUTOR_MOCK_MODE")
    agent_executor_allow_simulation: bool = Field(default=False, alias="AGENT_EXECUTOR_ALLOW_SIMULATION")
    agent_executor_dry_run_mode: bool = Field(default=False, alias="AGENT_EXECUTOR_DRY_RUN_MODE")

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
    agent_multi_agent_arbitration_enabled: bool = Field(default=False, alias="AGENT_MULTI_AGENT_ARBITRATION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_multi_agent_critic_review_enabled: bool = Field(default=False, alias="AGENT_MULTI_AGENT_CRITIC_REVIEW_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_multi_agent_mock_arbitration: bool = Field(default=False, alias="AGENT_MULTI_AGENT_MOCK_ARBITRATION")
    # Owner: agent-platform
    # Status: beta
    agent_event_driven_enabled: bool = Field(default=False, alias="AGENT_EVENT_DRIVEN_ENABLED")
    nats_url: str = Field(default="nats://localhost:4222", alias="NATS_URL")
    nats_trigger_enabled: bool = Field(default=False, alias="NATS_TRIGGER_ENABLED")
    pulsar_url: str = Field(default="pulsar://localhost:6650", alias="PULSAR_URL")
    pulsar_trigger_enabled: bool = Field(default=False, alias="PULSAR_TRIGGER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_cron_triggers_enabled: bool = Field(default=False, alias="AGENT_CRON_TRIGGERS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_pubsub_triggers_enabled: bool = Field(default=False, alias="AGENT_PUBSUB_TRIGGERS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_iam_enabled: bool = Field(default=False, alias="AGENT_IAM_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_saas_connectors_enabled: bool = Field(default=False, alias="AGENT_SAAS_CONNECTORS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_stateful_workflows_enabled: bool = Field(default=False, alias="AGENT_STATEFUL_WORKFLOWS_ENABLED")

    # Owner: agent-platform
    # Status: active
    agent_llm_provider: str = Field(default="mock", alias="AGENT_LLM_PROVIDER")
    # Owner: agent-platform
    # Status: active
    agent_allow_mock_llm_in_production: bool = Field(default=False, alias="AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION")
    # Owner: agent-platform
    # Status: active
    agent_require_real_llm_for_production: bool = Field(default=True, alias="AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION")
    # Owner: agent-platform
    # Status: beta
    agent_real_llm_enabled: bool = Field(default=False, alias="AGENT_REAL_LLM_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_llm_streaming_enabled: bool = Field(default=False, alias="AGENT_LLM_STREAMING_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_marketplace_enabled: bool = Field(default=True, alias="AGENT_MARKETPLACE_ENABLED")
    agent_distributed_runtime_enabled: bool = Field(default=False, alias="AGENT_DISTRIBUTED_RUNTIME_ENABLED")
    multi_cluster_enabled: bool = Field(default=False, alias="MULTI_CLUSTER_ENABLED")
    agent_cluster_federation_enabled: bool = Field(default=False, alias="AGENT_CLUSTER_FEDERATION_ENABLED")

    # Owner: agent-platform
    # Status: beta
    agent_remote_marketplace_enabled: bool = Field(default=False, alias="AGENT_REMOTE_MARKETPLACE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_bundle_install_enabled: bool = Field(default=True, alias="AGENT_BUNDLE_INSTALL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_bundle_signature_required: bool = Field(default=False, alias="AGENT_BUNDLE_SIGNATURE_REQUIRED")

    # Owner: agent-platform
    # Status: beta
    agent_incident_response_enabled: bool = Field(default=True, alias="AGENT_INCIDENT_RESPONSE_ENABLED")

    # Owner: agent-platform
    # Status: active
    agent_telemetry_backpressure_enabled: bool = Field(default=True, alias="AGENT_TELEMETRY_BACKPRESSURE_ENABLED")
    # Owner: agent-platform
    # Status: active
    agent_telemetry_drop_debug_spans_enabled: bool = Field(default=True, alias="AGENT_TELEMETRY_DROP_DEBUG_SPANS_ENABLED")
    # Owner: agent-platform
    # Status: active
    agent_telemetry_strict_export: bool = Field(default=False, alias="AGENT_TELEMETRY_STRICT_EXPORT")
    # Owner: agent-platform
    # Status: production
    agent_observability_enabled: bool = Field(default=True, alias="AGENT_OBSERVABILITY_ENABLED")
    agent_otel_tracing_enabled: bool = Field(default=True, alias="AGENT_OTEL_TRACING_ENABLED")
    otlp_export_enabled: bool = Field(default=False, alias="OTLP_EXPORT_ENABLED")
    jaeger_export_enabled: bool = Field(default=False, alias="JAEGER_EXPORT_ENABLED")
    zipkin_export_enabled: bool = Field(default=False, alias="ZIPKIN_EXPORT_ENABLED")
    agent_anomaly_detection_enabled: bool = Field(default=False, alias="AGENT_ANOMALY_DETECTION_ENABLED")
    agent_trace_export_enabled: bool = Field(default=True, alias="AGENT_TRACE_EXPORT_ENABLED")

    # Owner: agent-platform
    # Status: active
    agent_strict_budgets: bool = Field(default=False, alias="AGENT_STRICT_BUDGETS")
    # Owner: agent-platform
    # Status: active
    agent_worker_autoscaling_enabled: bool = Field(default=False, alias="AGENT_WORKER_AUTOSCALING_ENABLED")
    # Owner: agent-platform
    # Status: active
    agent_slo_enforcement_enabled: bool = Field(default=False, alias="AGENT_SLO_ENFORCEMENT_ENABLED")
    # Owner: agent-platform
    # Status: active
    agent_enterprise_observability_enabled: bool = Field(default=False, alias="AGENT_ENTERPRISE_OBSERVABILITY_ENABLED")
    # Owner: agent-platform
    # Status: active
    platform_profile: str = Field(default="appliance", alias="PLATFORM_PROFILE")
    # Owner: platform-ops
    # Owner: agent-platform
    # Status: beta
    agent_studio_enabled: bool = Field(default=True, alias="AGENT_STUDIO_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_debugger_enabled: bool = Field(default=False, alias="AGENT_DEBUGGER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_live_stepping_enabled: bool = Field(default=False, alias="AGENT_LIVE_STEPPING_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_breakpoints_enabled: bool = Field(default=False, alias="AGENT_BREAKPOINTS_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_approval_portal_enabled: bool = Field(default=False, alias="AGENT_APPROVAL_PORTAL_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_human_approval_enabled: bool = Field(default=True, alias="AGENT_HUMAN_APPROVAL_ENABLED")
    agent_approval_required_for_high_risk: bool = Field(default=True, alias="AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK")
    agent_approval_timeout_seconds: int = Field(default=3600, alias="AGENT_APPROVAL_TIMEOUT_SECONDS")
    agent_trace_export_enabled: bool = Field(default=False, alias="AGENT_TRACE_EXPORT_ENABLED")
    agent_a2a_enabled: bool = Field(default=False, alias="AGENT_A2A_ENABLED")
    agent_a2a_external_enabled: bool = Field(default=False, alias="AGENT_A2A_EXTERNAL_ENABLED")
    agent_websocket_streaming_enabled: bool = Field(default=False, alias="AGENT_WEBSOCKET_STREAMING_ENABLED")

    agent_email_notifications_enabled: bool = Field(default=False, alias="AGENT_EMAIL_NOTIFICATIONS_ENABLED")
    agent_push_notifications_enabled: bool = Field(default=False, alias="AGENT_PUSH_NOTIFICATIONS_ENABLED")
    email_provider: str = Field(default="mock", alias="EMAIL_PROVIDER")
    push_provider: str = Field(default="mock", alias="PUSH_PROVIDER")

    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    sendgrid_api_key: str = Field(default="", alias="SENDGRID_API_KEY")
    fcm_api_key: str = Field(default="", alias="FCM_API_KEY")
    apns_key_id: str = Field(default="", alias="APNS_KEY_ID")

    agent_distributed_rate_limiting_enabled: bool = Field(default=False, alias="AGENT_DISTRIBUTED_RATE_LIMITING_ENABLED")
    agent_hard_cost_cap_enabled: bool = Field(default=True, alias="AGENT_HARD_COST_CAP_ENABLED")



    # Owner: agent-platform
    # Status: beta
    agent_code_interpreter_enabled: bool = Field(default=False, alias="AGENT_CODE_INTERPRETER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_code_sandbox_provider: str = Field(default="gvisor", alias="AGENT_CODE_SANDBOX_PROVIDER")
    # Owner: agent-platform
    # Status: production-ready
    # Set to False to block any mock/simulated sandbox path in production.
    agent_sandbox_allow_simulated_provider: bool = Field(default=False, alias="AGENT_SANDBOX_ALLOW_SIMULATED_PROVIDER")
    # Owner: agent-platform
    # Status: production-ready
    # If True, every sandbox execution must have a valid cryptographical or behavioral attestation.
    agent_sandbox_production_requires_attestation: bool = Field(default=False, alias="AGENT_SANDBOX_PRODUCTION_REQUIRES_ATTESTATION")
    # Owner: agent-platform
    # Status: beta
    agent_code_sandbox_docker_enabled: bool = Field(default=False, alias="AGENT_CODE_SANDBOX_DOCKER_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_code_sandbox_firecracker_enabled: bool = Field(default=False, alias="AGENT_CODE_SANDBOX_FIRECRACKER_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_code_sandbox_gvisor_enabled: bool = Field(default=False, alias="AGENT_CODE_SANDBOX_GVISOR_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_code_sandbox_microvm_required: bool = Field(default=False, alias="AGENT_CODE_SANDBOX_MICROVM_REQUIRED")
    # Owner: agent-platform
    # Status: experimental
    agent_code_sandbox_wasm_enabled: bool = Field(default=False, alias="AGENT_CODE_SANDBOX_WASM_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_code_sandbox_network_enabled: bool = Field(default=False, alias="AGENT_CODE_SANDBOX_NETWORK_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_code_sandbox_write_enabled: bool = Field(default=False, alias="AGENT_CODE_SANDBOX_WRITE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_dynamic_tool_execution_enabled: bool = Field(default=False, alias="AGENT_DYNAMIC_TOOL_EXECUTION_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_mcp_enabled: bool = Field(default=False, alias="AGENT_MCP_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_mcp_client_enabled: bool = Field(default=False, alias="AGENT_MCP_CLIENT_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_mcp_server_enabled: bool = Field(default=False, alias="AGENT_MCP_SERVER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_mcp_external_network_enabled: bool = Field(default=False, alias="AGENT_MCP_EXTERNAL_NETWORK_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_mcp_sampling_enabled: bool = Field(default=False, alias="AGENT_MCP_SAMPLING_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_mcp_oauth_token_exchange_enabled: bool = Field(default=False, alias="AGENT_MCP_OAUTH_TOKEN_EXCHANGE_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_mcp_user_delegation_required: bool = Field(default=False, alias="AGENT_MCP_USER_DELEGATION_REQUIRED")
    # Owner: agent-platform
    # Status: experimental
    agent_mcp_global_credentials_allowed: bool = Field(default=False, alias="AGENT_MCP_GLOBAL_CREDENTIALS_ALLOWED")
    # Owner: agent-platform
    # Status: experimental
    # Allow mock-only discovery (ONLY in test/staging). Production must be false.
    agent_mcp_mock_mode: bool = Field(default=False, alias="AGENT_MCP_MOCK_MODE")
    # Owner: agent-platform
    # Status: experimental
    # Enable real MCP server discovery (tools/resources/prompts via MCP protocol).
    agent_mcp_real_discovery_enabled: bool = Field(default=False, alias="AGENT_MCP_REAL_DISCOVERY_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    # Timeout in ms for MCP transport calls (initialize, list_tools, call_tool).
    agent_mcp_call_timeout_ms: int = Field(default=10000, alias="AGENT_MCP_CALL_TIMEOUT_MS")
    # Owner: agent-platform
    # Status: experimental
    # Max retries for transient MCP transport errors.
    agent_mcp_call_max_retries: int = Field(default=2, alias="AGENT_MCP_CALL_MAX_RETRIES")
    # Owner: agent-platform
    # Status: production-ready
    agent_connector_catalog_enabled: bool = Field(default=False, alias="AGENT_CONNECTOR_CATALOG_ENABLED")
    # Owner: agent-platform
    # Status: production-ready
    agent_mcp_catalog_enabled: bool = Field(default=False, alias="AGENT_MCP_CATALOG_ENABLED")
    # Owner: agent-platform
    # Status: production-ready
    plugin_runtime_enabled: bool = Field(default=False, alias="PLUGIN_RUNTIME_ENABLED")
    # Owner: agent-platform
    # Status: production-ready
    plugin_signature_required: bool = Field(default=False, alias="PLUGIN_SIGNATURE_REQUIRED")
    # Owner: agent-platform
    # Status: production-ready
    agent_plugin_supply_chain_enabled: bool = Field(default=False, alias="AGENT_PLUGIN_SUPPLY_CHAIN_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_knowledge_graph_enabled: bool = Field(default=False, alias="AGENT_KNOWLEDGE_GRAPH_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_graph_rag_enabled: bool = Field(default=False, alias="AGENT_GRAPH_RAG_ENABLED")
    # Owner: agent-platform
    # Status: beta
    prompt_templates_enabled: bool = Field(default=False, alias="PROMPT_TEMPLATES_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    prompt_template_playground_enabled: bool = Field(default=False, alias="PROMPT_TEMPLATE_PLAYGROUND_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_graph_write_enabled: bool = Field(default=False, alias="AGENT_GRAPH_WRITE_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_graph_external_db_enabled: bool = Field(default=False, alias="AGENT_GRAPH_EXTERNAL_DB_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_kg_provider: str = Field(default="internal_sql", alias="AGENT_KG_PROVIDER")
    # Owner: agent-platform
    # Status: beta
    agent_kg_external_provider_enabled: bool = Field(default=False, alias="AGENT_KG_EXTERNAL_PROVIDER_ENABLED")
    # Owner: agent-platform
    # Status: beta
    agent_kg_write_enabled: bool = Field(default=False, alias="AGENT_KG_WRITE_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_kg_adjacency_cache_enabled: bool = Field(default=False, alias="AGENT_KG_ADJACENCY_CACHE_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_kg_postgres_graph_enabled: bool = Field(default=True, alias="AGENT_KG_POSTGRES_GRAPH_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_kg_pgvector_enabled: bool = Field(default=False, alias="AGENT_KG_PGVECTOR_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    agent_kg_pgrouting_enabled: bool = Field(default=False, alias="AGENT_KG_PGROUTING_ENABLED")
    # Owner: agent-platform
    # Status: experimental
    # Set to true ONLY in test/staging environments to allow mock path returns.
    # Production must keep this false so empty paths mean "no path found", not "not implemented".
    agent_kg_mock_mode: bool = Field(default=False, alias="AGENT_KG_MOCK_MODE")
    # Owner: agent-platform
    # Status: experimental
    agent_kg_pathfinding_max_depth: int = Field(default=6, alias="AGENT_KG_PATHFINDING_MAX_DEPTH")
    # Owner: agent-platform
    # Status: experimental
    agent_kg_pathfinding_max_nodes: int = Field(default=500, alias="AGENT_KG_PATHFINDING_MAX_NODES")
    # Owner: agent-platform
    # Status: experimental
    agent_kg_pathfinding_timeout_ms: int = Field(default=5000, alias="AGENT_KG_PATHFINDING_TIMEOUT_MS")

    # Owner: agent-platform
    agent_shell_tool_enabled: bool = Field(default=False, alias="AGENT_SHELL_TOOL_ENABLED")
    agent_http_tool_enabled: bool = Field(default=False, alias="AGENT_HTTP_TOOL_ENABLED")
    agent_db_read_tool_enabled: bool = Field(default=False, alias="AGENT_DB_READ_TOOL_ENABLED")
    agent_file_tools_enabled: bool = Field(default=False, alias="AGENT_FILE_TOOLS_ENABLED")
    agent_file_write_enabled: bool = Field(default=False, alias="AGENT_FILE_WRITE_ENABLED")
    agent_file_delete_enabled: bool = Field(default=False, alias="AGENT_FILE_DELETE_ENABLED")
    agent_browser_tool_enabled: bool = Field(default=False, alias="AGENT_BROWSER_TOOL_ENABLED")
    agent_browser_external_network_enabled: bool = Field(default=False, alias="AGENT_BROWSER_EXTERNAL_NETWORK_ENABLED")
    agent_browser_screenshot_enabled: bool = Field(default=False, alias="AGENT_BROWSER_SCREENSHOT_ENABLED")
    agent_browser_allowlist: str = Field(default="example.com,wikipedia.org", alias="AGENT_BROWSER_ALLOWLIST")
