---
owner: platform-ops
status: reference-generated
generated_from:
  - control_plane.app.services.config_service.BaseAppConfig
generated_by: scripts/docs/generate_reference_docs.py
---

# Configuration Reference

This document is generated from `BaseAppConfig`. Required values are marked as `required`.

## `a2a`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| A2A_API_KEY | a2a_api_key | str | <empty> | yes |
| A2A_BASE_URL | a2a_base_url | str | - | no |
| A2A_ENABLED | a2a_enabled | bool | false | no |

## `abuse`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ABUSE_AUTO_SUSPEND_ENABLED | abuse_auto_suspend_enabled | bool | false | no |
| ABUSE_DETECTION_ENABLED | abuse_detection_enabled | bool | true | no |
| ABUSE_DRY_RUN | abuse_dry_run | bool | true | no |

## `admin`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ADMIN_BASE_URL | admin_base_url | str | - | no |
| ADMIN_READ_TOKEN | admin_read_token | str \| None | <empty> | yes |
| ADMIN_SUPER_TOKEN | admin_super_token | str \| None | <empty> | yes |
| ADMIN_TESTS_RATE_LIMIT_ENABLED | admin_tests_rate_limit_enabled | bool | true | no |
| ADMIN_TOKEN | admin_token | str | required | yes |
| ADMIN_WRITE_TOKEN | admin_write_token | str \| None | <empty> | yes |

## `agent`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| AGENT_A2A_ENABLED | agent_a2a_enabled | bool | false | no |
| AGENT_A2A_EXTERNAL_ENABLED | agent_a2a_external_enabled | bool | false | no |
| AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION | agent_allow_mock_llm_in_production | bool | false | no |
| AGENT_ANOMALY_DETECTION_ENABLED | agent_anomaly_detection_enabled | bool | false | no |
| AGENT_APPROVAL_PORTAL_ENABLED | agent_approval_portal_enabled | bool | false | no |
| AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK | agent_approval_required_for_high_risk | bool | true | no |
| AGENT_APPROVAL_TIMEOUT_SECONDS | agent_approval_timeout_seconds | int | 3600 | no |
| AGENT_ASSISTANTS_API_ENABLED | agent_assistants_api_enabled | bool | false | no |
| AGENT_ASYNC_EXECUTION_ENABLED | agent_async_execution_enabled | bool | false | no |
| AGENT_AUTO_APPLY_LEARNINGS | agent_auto_apply_learnings | bool | true | no |
| AGENT_AUTO_OPTIMIZATION_ENABLED | agent_auto_optimization_enabled | bool | false | no |
| AGENT_AUTO_RETRY_ENABLED | agent_auto_retry_enabled | bool | true | no |
| AGENT_BATCH_API_ENABLED | agent_batch_api_enabled | bool | false | no |
| AGENT_BREAKPOINTS_ENABLED | agent_breakpoints_enabled | bool | false | no |
| AGENT_BROWSER_ALLOWLIST | agent_browser_allowlist | str | example.com,wikipedia.org | no |
| AGENT_BROWSER_EXTERNAL_NETWORK_ENABLED | agent_browser_external_network_enabled | bool | false | no |
| AGENT_BROWSER_SCREENSHOT_ENABLED | agent_browser_screenshot_enabled | bool | false | no |
| AGENT_BROWSER_TOOL_ENABLED | agent_browser_tool_enabled | bool | false | no |
| AGENT_BUNDLE_INSTALL_ENABLED | agent_bundle_install_enabled | bool | true | no |
| AGENT_BUNDLE_SIGNATURE_REQUIRED | agent_bundle_signature_required | bool | false | no |
| AGENT_CANARY_AGENTS_ENABLED | agent_canary_agents_enabled | bool | true | no |
| AGENT_CANARY_AUTO_PROMOTE | agent_canary_auto_promote | bool | false | no |
| AGENT_CLUSTER_FEDERATION_ENABLED | agent_cluster_federation_enabled | bool | false | no |
| AGENT_CODE_INTERPRETER_ENABLED | agent_code_interpreter_enabled | bool | false | no |
| AGENT_CODE_SANDBOX_DOCKER_ENABLED | agent_code_sandbox_docker_enabled | bool | false | no |
| AGENT_CODE_SANDBOX_FIRECRACKER_ENABLED | agent_code_sandbox_firecracker_enabled | bool | false | no |
| AGENT_CODE_SANDBOX_GVISOR_ENABLED | agent_code_sandbox_gvisor_enabled | bool | false | no |
| AGENT_CODE_SANDBOX_MICROVM_REQUIRED | agent_code_sandbox_microvm_required | bool | false | no |
| AGENT_CODE_SANDBOX_NETWORK_ENABLED | agent_code_sandbox_network_enabled | bool | false | no |
| AGENT_CODE_SANDBOX_PROVIDER | agent_code_sandbox_provider | str | gvisor | no |
| AGENT_CODE_SANDBOX_WASM_ENABLED | agent_code_sandbox_wasm_enabled | bool | false | no |
| AGENT_CODE_SANDBOX_WRITE_ENABLED | agent_code_sandbox_write_enabled | bool | false | no |
| AGENT_COGNITIVE_LOOPBACK_ENABLED | agent_cognitive_loopback_enabled | bool | true | no |
| AGENT_COGNITIVE_MEMORY_ENABLED | agent_cognitive_memory_enabled | bool | false | no |
| AGENT_CONNECTOR_CATALOG_ENABLED | agent_connector_catalog_enabled | bool | false | no |
| AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED | agent_connector_external_network_enabled | bool | false | no |
| AGENT_CONNECTOR_MODE | agent_connector_mode | str | mock | no |
| AGENT_CONNECTOR_REAL_HTTP_ENABLED | agent_connector_real_http_enabled | bool | false | no |
| AGENT_CONNECTOR_WRITE_ENABLED | agent_connector_write_enabled | bool | false | no |
| AGENT_CONSTRAINT_REASONING_ENABLED | agent_constraint_reasoning_enabled | bool | false | no |
| AGENT_CONTEXT_COMPRESSION_ENABLED | agent_context_compression_enabled | bool | false | no |
| AGENT_CRON_TRIGGERS_ENABLED | agent_cron_triggers_enabled | bool | false | no |
| AGENT_DB_READ_TOOL_ENABLED | agent_db_read_tool_enabled | bool | false | no |
| AGENT_DEBUG_STATE_EDITING_ENABLED | agent_debug_state_editing_enabled | bool | false | no |
| AGENT_DEBUGGER_ENABLED | agent_debugger_enabled | bool | false | no |
| AGENT_DESTRUCTIVE_TOOLS_ENABLED | agent_destructive_tools_enabled | bool | false | no |
| AGENT_DIGITAL_TWINS_ENABLED | agent_digital_twins_enabled | bool | false | no |
| AGENT_DISTRIBUTED_RATE_LIMITING_ENABLED | agent_distributed_rate_limiting_enabled | bool | false | no |
| AGENT_DISTRIBUTED_RUNTIME_ENABLED | agent_distributed_runtime_enabled | bool | false | no |
| AGENT_DYNAMIC_TOOL_EXECUTION_ENABLED | agent_dynamic_tool_execution_enabled | bool | false | no |
| AGENT_EMAIL_NOTIFICATIONS_ENABLED | agent_email_notifications_enabled | bool | false | no |
| AGENT_EMBEDDED_WORKER_ENABLED | agent_embedded_worker_enabled | bool | false | no |
| AGENT_ENTERPRISE_OBSERVABILITY_ENABLED | agent_enterprise_observability_enabled | bool | false | no |
| AGENT_EVAL_ALLOW_MOCK_FOR_PROMOTION | agent_eval_allow_mock_for_promotion | bool | false | no |
| AGENT_EVAL_GATE_STRICT | agent_eval_gate_strict | bool | true | no |
| AGENT_EVAL_PROVIDER | agent_eval_provider | str | mock | no |
| AGENT_EVAL_REAL_PROVIDER_ENABLED | agent_eval_real_provider_enabled | bool | false | no |
| AGENT_EVAL_REGRESSION_GATE_ENABLED | agent_eval_regression_gate_enabled | bool | true | no |
| AGENT_EVALS_ENABLED | agent_evals_enabled | bool | false | no |
| AGENT_EVENT_DRIVEN_ENABLED | agent_event_driven_enabled | bool | false | no |
| AGENT_EXECUTION_ENABLED | agent_execution_enabled | bool | false | no |
| AGENT_EXECUTION_PLANE_ENABLED | agent_execution_plane_enabled | bool | false | no |
| AGENT_EXECUTOR_ALLOW_SIMULATION | agent_executor_allow_simulation | bool | false | no |
| AGENT_EXECUTOR_DRY_RUN_MODE | agent_executor_dry_run_mode | bool | false | no |
| AGENT_EXECUTOR_MOCK_MODE | agent_executor_mock_mode | bool | false | no |
| AGENT_FEDERATED_MEMORY_ENABLED | agent_federated_memory_enabled | bool | false | no |
| AGENT_FEDERATED_MEMORY_RAW_DATA_SYNC | agent_federated_memory_raw_data_sync | bool | false | no |
| AGENT_FEDERATED_MEMORY_SYNC_ENABLED | agent_federated_memory_sync_enabled | bool | false | no |
| AGENT_FEEDBACK_LEARNING_ENABLED | agent_feedback_learning_enabled | bool | false | no |
| AGENT_FEWSHOT_AUTO_CURATOR_ENABLED | agent_fewshot_auto_curator_enabled | bool | false | no |
| AGENT_FILE_DELETE_ENABLED | agent_file_delete_enabled | bool | false | no |
| AGENT_FILE_TOOLS_ENABLED | agent_file_tools_enabled | bool | false | no |
| AGENT_FILE_WRITE_ENABLED | agent_file_write_enabled | bool | false | no |
| AGENT_FLOW_COMPILER_ENABLED | agent_flow_compiler_enabled | bool | false | no |
| AGENT_GITHUB_CONNECTOR_ENABLED | agent_github_connector_enabled | bool | false | no |
| AGENT_GLPK_SOLVER_ENABLED | agent_glpk_solver_enabled | bool | false | no |
| AGENT_GRAPH_EXTERNAL_DB_ENABLED | agent_graph_external_db_enabled | bool | false | no |
| AGENT_GRAPH_RAG_ENABLED | agent_graph_rag_enabled | bool | false | no |
| AGENT_GRAPH_WRITE_ENABLED | agent_graph_write_enabled | bool | false | no |
| AGENT_HANDOFFS_ENABLED | agent_handoffs_enabled | bool | false | no |
| AGENT_HARD_COST_CAP_ENABLED | agent_hard_cost_cap_enabled | bool | true | no |
| AGENT_HTTP_TOOL_ENABLED | agent_http_tool_enabled | bool | false | no |
| AGENT_HUMAN_APPROVAL_ENABLED | agent_human_approval_enabled | bool | true | no |
| AGENT_IAM_ENABLED | agent_iam_enabled | bool | false | no |
| AGENT_INCIDENT_RESPONSE_ENABLED | agent_incident_response_enabled | bool | true | no |
| AGENT_INTERNAL_BUNDLE_SIGNATURE_REQUIRED_IN_PRODUCTION | agent_internal_bundle_signature_required_in_production | bool | true | no |
| AGENT_IOT_CONNECTORS_ENABLED | agent_iot_connectors_enabled | bool | false | no |
| AGENT_KG_ADJACENCY_CACHE_ENABLED | agent_kg_adjacency_cache_enabled | bool | false | no |
| AGENT_KG_EXTERNAL_PROVIDER_ENABLED | agent_kg_external_provider_enabled | bool | false | no |
| AGENT_KG_MOCK_MODE | agent_kg_mock_mode | bool | false | no |
| AGENT_KG_PATHFINDING_MAX_DEPTH | agent_kg_pathfinding_max_depth | int | 6 | no |
| AGENT_KG_PATHFINDING_MAX_NODES | agent_kg_pathfinding_max_nodes | int | 500 | no |
| AGENT_KG_PATHFINDING_TIMEOUT_MS | agent_kg_pathfinding_timeout_ms | int | 5000 | no |
| AGENT_KG_PGROUTING_ENABLED | agent_kg_pgrouting_enabled | bool | false | no |
| AGENT_KG_PGVECTOR_ENABLED | agent_kg_pgvector_enabled | bool | false | no |
| AGENT_KG_POSTGRES_GRAPH_ENABLED | agent_kg_postgres_graph_enabled | bool | true | no |
| AGENT_KG_PROVIDER | agent_kg_provider | str | internal_sql | no |
| AGENT_KG_WRITE_ENABLED | agent_kg_write_enabled | bool | false | no |
| AGENT_KNOWLEDGE_GRAPH_ENABLED | agent_knowledge_graph_enabled | bool | false | no |
| AGENT_LIVE_STEPPING_ENABLED | agent_live_stepping_enabled | bool | false | no |
| AGENT_LLM_PROVIDER | agent_llm_provider | str | mock | no |
| AGENT_LLM_STREAMING_ENABLED | agent_llm_streaming_enabled | bool | false | no |
| AGENT_LONG_TERM_MEMORY_ENABLED | agent_long_term_memory_enabled | bool | false | no |
| AGENT_MARKETPLACE_ENABLED | agent_marketplace_enabled | bool | true | no |
| AGENT_MCP_CALL_MAX_RETRIES | agent_mcp_call_max_retries | int | 2 | no |
| AGENT_MCP_CALL_TIMEOUT_MS | agent_mcp_call_timeout_ms | int | 10000 | no |
| AGENT_MCP_CATALOG_ENABLED | agent_mcp_catalog_enabled | bool | false | no |
| AGENT_MCP_CLIENT_ENABLED | agent_mcp_client_enabled | bool | false | no |
| AGENT_MCP_ENABLED | agent_mcp_enabled | bool | false | no |
| AGENT_MCP_EXTERNAL_NETWORK_ENABLED | agent_mcp_external_network_enabled | bool | false | no |
| AGENT_MCP_GLOBAL_CREDENTIALS_ALLOWED | agent_mcp_global_credentials_allowed | bool | false | no |
| AGENT_MCP_MOCK_MODE | agent_mcp_mock_mode | bool | false | no |
| AGENT_MCP_OAUTH_TOKEN_EXCHANGE_ENABLED | agent_mcp_oauth_token_exchange_enabled | bool | false | yes |
| AGENT_MCP_REAL_DISCOVERY_ENABLED | agent_mcp_real_discovery_enabled | bool | false | no |
| AGENT_MCP_SAMPLING_ENABLED | agent_mcp_sampling_enabled | bool | false | no |
| AGENT_MCP_SERVER_ENABLED | agent_mcp_server_enabled | bool | false | no |
| AGENT_MCP_USER_DELEGATION_REQUIRED | agent_mcp_user_delegation_required | bool | false | no |
| AGENT_MCTS_REASONING_ENABLED | agent_mcts_reasoning_enabled | bool | false | no |
| AGENT_MCTS_SANDBOX_SIMULATION_ENABLED | agent_mcts_sandbox_simulation_enabled | bool | false | no |
| AGENT_MEMORY_CONSENT_REQUIRED | agent_memory_consent_required | bool | true | no |
| AGENT_MEMORY_CONTEXT_INJECTION_ENABLED | agent_memory_context_injection_enabled | bool | false | no |
| AGENT_MEMORY_EMBEDDINGS_PROVIDER | agent_memory_embeddings_provider | str | mock | no |
| AGENT_MEMORY_ENABLED | agent_memory_enabled | bool | false | no |
| AGENT_MEMORY_ENCRYPTION_ENABLED | agent_memory_encryption_enabled | bool | false | no |
| AGENT_MEMORY_EXPORT_ENABLED | agent_memory_export_enabled | bool | false | no |
| AGENT_MEMORY_SEARCH_ENABLED | agent_memory_search_enabled | bool | false | no |
| AGENT_MEMORY_SEMANTIC_SEARCH_ENABLED | agent_memory_semantic_search_enabled | bool | false | no |
| AGENT_MEMORY_VECTOR_PROVIDER | agent_memory_vector_provider | str | mock | no |
| AGENT_MEMORY_WRITE_ENABLED | agent_memory_write_enabled | bool | false | no |
| AGENT_META_REVIEWER_BLOCKING_MODE | agent_meta_reviewer_blocking_mode | bool | false | no |
| AGENT_META_REVIEWER_ENABLED | agent_meta_reviewer_enabled | bool | false | no |
| AGENT_META_REVIEWER_PARALLEL_ENABLED | agent_meta_reviewer_parallel_enabled | bool | false | no |
| AGENT_MULTI_AGENT_ARBITRATION_ENABLED | agent_multi_agent_arbitration_enabled | bool | false | no |
| AGENT_MULTI_AGENT_CRITIC_REVIEW_ENABLED | agent_multi_agent_critic_review_enabled | bool | false | no |
| AGENT_MULTI_AGENT_ENABLED | agent_multi_agent_enabled | bool | false | no |
| AGENT_MULTI_AGENT_MOCK_ARBITRATION | agent_multi_agent_mock_arbitration | bool | false | no |
| AGENT_OBSERVABILITY_ENABLED | agent_observability_enabled | bool | true | no |
| AGENT_OPTIMIZATION_APPLY_ENABLED | agent_optimization_apply_enabled | bool | false | no |
| AGENT_OPTIMIZER_APPLY_WINNER_ENABLED | agent_optimizer_apply_winner_enabled | bool | false | no |
| AGENT_OPTIMIZER_ENABLED | agent_optimizer_enabled | bool | false | no |
| AGENT_OPTIMIZER_PARALLEL_EVALS_ENABLED | agent_optimizer_parallel_evals_enabled | bool | false | no |
| AGENT_OPTIMIZER_TOURNAMENTS_ENABLED | agent_optimizer_tournaments_enabled | bool | false | no |
| AGENT_OTEL_TRACING_ENABLED | agent_otel_tracing_enabled | bool | true | no |
| AGENT_PHYSICAL_ACTUATION_ENABLED | agent_physical_actuation_enabled | bool | false | no |
| AGENT_PLAN_AND_SOLVE_ENABLED | agent_plan_and_solve_enabled | bool | false | no |
| AGENT_PLAN_EXECUTION_ENABLED | agent_plan_execution_enabled | bool | false | no |
| AGENT_PLANNER_REAL_EXECUTION_ENABLED | agent_planner_real_execution_enabled | bool | false | no |
| AGENT_PLANNING_ENABLED | agent_planning_enabled | bool | false | no |
| AGENT_PLUGIN_SUPPLY_CHAIN_ENABLED | agent_plugin_supply_chain_enabled | bool | false | no |
| AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE | agent_production_requires_eval_baseline | bool | true | no |
| AGENT_PROMOTION_REQUIRES_EVALS | agent_promotion_requires_evals | bool | false | no |
| AGENT_PUBSUB_TRIGGERS_ENABLED | agent_pubsub_triggers_enabled | bool | false | no |
| AGENT_PUSH_NOTIFICATIONS_ENABLED | agent_push_notifications_enabled | bool | false | no |
| AGENT_QUEUE_BACKPRESSURE_ENABLED | agent_queue_backpressure_enabled | bool | false | no |
| AGENT_REACT_LOOP_ENABLED | agent_react_loop_enabled | bool | false | no |
| AGENT_REAL_LLM_ENABLED | agent_real_llm_enabled | bool | false | no |
| AGENT_REAL_PROVIDER_VALIDATION_ENABLED | agent_real_provider_validation_enabled | bool | false | no |
| AGENT_REASONING_LOOP_ENABLED | agent_reasoning_loop_enabled | bool | false | no |
| AGENT_REMOTE_MARKETPLACE_ENABLED | agent_remote_marketplace_enabled | bool | false | no |
| AGENT_REPLAY_ENABLED | agent_replay_enabled | bool | false | no |
| AGENT_REPLAY_FROM_STEP_ENABLED | agent_replay_from_step_enabled | bool | false | no |
| AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION | agent_require_real_llm_for_production | bool | true | no |
| AGENT_RUNTIME_ENABLED | agent_runtime_enabled | bool | false | no |
| AGENT_SAAS_CONNECTORS_ENABLED | agent_saas_connectors_enabled | bool | false | no |
| AGENT_SAB_ENABLED | agent_sab_enabled | bool | true | no |
| AGENT_SAB_EXPORT_ENABLED | agent_sab_export_enabled | bool | false | no |
| AGENT_SAB_IMPORT_ENABLED | agent_sab_import_enabled | bool | false | no |
| AGENT_SANDBOX_ALLOW_SIMULATED_PROVIDER | agent_sandbox_allow_simulated_provider | bool | false | no |
| AGENT_SANDBOX_PRODUCTION_REQUIRES_ATTESTATION | agent_sandbox_production_requires_attestation | bool | false | no |
| AGENT_SEMANTIC_MEMORY_ENABLED | agent_semantic_memory_enabled | bool | false | no |
| AGENT_SHADOW_MODE_ENABLED | agent_shadow_mode_enabled | bool | false | no |
| AGENT_SHELL_TOOL_ENABLED | agent_shell_tool_enabled | bool | false | no |
| AGENT_SLO_ENFORCEMENT_ENABLED | agent_slo_enforcement_enabled | bool | false | no |
| AGENT_STATEFUL_WORKFLOWS_ENABLED | agent_stateful_workflows_enabled | bool | false | no |
| AGENT_STRICT_BUDGETS | agent_strict_budgets | bool | false | no |
| AGENT_STUDIO_ENABLED | agent_studio_enabled | bool | true | no |
| AGENT_STUDIO_GA_ENABLED | agent_studio_ga_enabled | bool | true | no |
| AGENT_TASK_DRY_RUN_MODE | agent_task_dry_run_mode | bool | false | no |
| AGENT_TASK_MOCK_MODE | agent_task_mock_mode | bool | false | no |
| AGENT_TASK_SIMULATION_MODE | agent_task_simulation_mode | bool | false | no |
| AGENT_TELEMETRY_BACKPRESSURE_ENABLED | agent_telemetry_backpressure_enabled | bool | true | no |
| AGENT_TELEMETRY_DROP_DEBUG_SPANS_ENABLED | agent_telemetry_drop_debug_spans_enabled | bool | true | no |
| AGENT_TELEMETRY_STRICT_EXPORT | agent_telemetry_strict_export | bool | false | no |
| AGENT_TIME_TRAVEL_DEBUGGER_ENABLED | agent_time_travel_debugger_enabled | bool | false | no |
| AGENT_TOOL_ADAPTERS_ENABLED | agent_tool_adapters_enabled | bool | false | no |
| AGENT_TOOL_CREDENTIAL_DELEGATION_ENABLED | agent_tool_credential_delegation_enabled | bool | false | no |
| AGENT_TOOL_EXECUTION_ENABLED | agent_tool_execution_enabled | bool | false | no |
| AGENT_TOOL_REGISTRY_ENABLED | agent_tool_registry_enabled | bool | false | no |
| AGENT_TOOL_ROLLBACK_ENABLED | agent_tool_rollback_enabled | bool | true | no |
| AGENT_TOOL_SANDBOX_ENABLED | agent_tool_sandbox_enabled | bool | true | no |
| AGENT_TRACE_EXPORT_ENABLED | agent_trace_export_enabled | bool | false | no |
| AGENT_UNCERTAINTY_AUTO_RESEARCH_ENABLED | agent_uncertainty_auto_research_enabled | bool | false | no |
| AGENT_UNCERTAINTY_DETECTION_ENABLED | agent_uncertainty_detection_enabled | bool | true | no |
| AGENT_UNCERTAINTY_HITL_ENABLED | agent_uncertainty_hitl_enabled | bool | true | no |
| AGENT_VISUAL_FLOW_EDITOR_ENABLED | agent_visual_flow_editor_enabled | bool | false | no |
| AGENT_WALLET_EXTERNAL_SPEND_ENABLED | agent_wallet_external_spend_enabled | bool | false | no |
| AGENT_WALLET_STRIPE_ENABLED | agent_wallet_stripe_enabled | bool | false | no |
| AGENT_WALLET_WEB3_ENABLED | agent_wallet_web3_enabled | bool | false | no |
| AGENT_WALLETS_ENABLED | agent_wallets_enabled | bool | true | no |
| AGENT_WEB_SEARCH_ALLOWLIST_ENABLED | agent_web_search_allowlist_enabled | bool | true | no |
| AGENT_WEB_SEARCH_ENABLED | agent_web_search_enabled | bool | false | no |
| AGENT_WEB_SEARCH_EXTERNAL_NETWORK_ENABLED | agent_web_search_external_network_enabled | bool | false | no |
| AGENT_WEBSOCKET_STREAMING_ENABLED | agent_websocket_streaming_enabled | bool | false | no |
| AGENT_WORKER_AUTOSCALING_ENABLED | agent_worker_autoscaling_enabled | bool | false | no |
| AGENT_WORKER_ENABLED | agent_worker_enabled | bool | false | no |
| AGENT_Z3_SOLVER_ENABLED | agent_z3_solver_enabled | bool | false | no |

## `agentic`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| AGENTIC_ROUTER_V2_ENABLED | agentic_router_v2_enabled | bool | false | no |

## `ai21`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| AI21_API_KEY | ai21_api_key | str | <empty> | yes |
| AI21_PROVIDER_ENABLED | ai21_provider_enabled | bool | true | no |

## `allow`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ALLOW_UNSIGNED_INTERNAL_BUNDLES | allow_unsigned_internal_bundles | bool | false | no |

## `anthropic`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ANTHROPIC_API_KEY | anthropic_api_key | str | <empty> | yes |
| ANTHROPIC_BASE_URL | anthropic_base_url | str | - | no |
| ANTHROPIC_MODEL | anthropic_model | str | - | no |
| ANTHROPIC_PROVIDER_ENABLED | anthropic_provider_enabled | bool | true | no |

## `api`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| API_BASE_URL | api_base_url | str | - | no |

## `apns`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| APNS_KEY_ID | apns_key_id | str | <empty> | yes |

## `app`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| APP_ENV | app_env | str | local | no |
| APP_PUBLIC_URL | app_public_url | str | http://localhost:18080 | no |

## `asaas`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ASAAS_API_KEY | asaas_api_key | str | <empty> | yes |

## `async`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ASYNC_JOB_QUEUE_NAME | async_job_queue_name | str | generation_jobs:queue | no |
| ASYNC_WORKER_BLOCK_SECONDS | async_worker_block_seconds | int | 5 | no |

## `attestation`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ATTESTATION_MODE | attestation_mode | str | advisory | no |

## `aws`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| AWS_ACCESS_KEY_ID | aws_access_key_id | str | <empty> | yes |
| AWS_REGION | aws_region | str | us-east-1 | no |
| AWS_SECRET_ACCESS_KEY | aws_secret_access_key | str | <empty> | yes |

## `azure`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| AZURE_OPENAI_API_KEY | azure_openai_api_key | str | <empty> | yes |
| AZURE_OPENAI_API_VERSION | azure_openai_api_version | str | 2024-10-21 | no |
| AZURE_OPENAI_DEPLOYMENT | azure_openai_deployment | str | - | no |
| AZURE_OPENAI_ENDPOINT | azure_openai_endpoint | str | - | no |
| AZURE_OPENAI_PROVIDER_ENABLED | azure_openai_provider_enabled | bool | true | no |

## `bedrock`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| BEDROCK_PROVIDER_ENABLED | bedrock_provider_enabled | bool | true | no |

## `billing`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| BILLING_DUE_DAYS | billing_due_days | int | 7 | no |
| BILLING_INVOICE_DAY | billing_invoice_day | int | 1 | no |
| BILLING_SUSPEND_AFTER_DAYS | billing_suspend_after_days | int | 15 | no |

## `card`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CARD_PAYMENT_ENABLED | card_payment_enabled | bool | false | no |

## `circuit`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CIRCUIT_BREAKER_FAILURE_THRESHOLD | circuit_breaker_failure_threshold | int | 3 | no |
| CIRCUIT_BREAKER_RECOVERY_SECONDS | circuit_breaker_recovery_seconds | int | 20 | no |

## `client`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CLIENT_PORTAL_BASE_URL | client_portal_base_url | str | - | no |

## `cloud`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CLOUD_PROVIDERS_ENABLED | cloud_providers_enabled | bool | false | no |

## `cluster`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CLUSTER_ID | cluster_id | str | local | no |
| CLUSTER_REGION | cluster_region | str | default | no |

## `cohere`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| COHERE_API_KEY | cohere_api_key | str | <empty> | yes |
| COHERE_PROVIDER_ENABLED | cohere_provider_enabled | bool | true | no |

## `collab`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| COLLAB_CHAT_ENABLED | collab_chat_enabled | bool | false | no |
| COLLAB_CHAT_WEBSOCKET_ENABLED | collab_chat_websocket_enabled | bool | false | no |

## `commercial`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| COMMERCIAL_AGENT_DEFAULT_DELEGATION_LIMIT | commercial_agent_default_delegation_limit | int | 3 | no |
| COMMERCIAL_AGENT_GOVERNANCE_ENABLED | commercial_agent_governance_enabled | bool | false | no |
| COMMERCIAL_AGENT_GOVERNANCE_MODE | commercial_agent_governance_mode | str | audit_only | no |
| COMMERCIAL_AGENT_MEMORY_ISOLATION_LEVEL | commercial_agent_memory_isolation_level | str | strict | no |
| COMMERCIAL_AGENT_TOOL_APPROVAL_REQUIRED | commercial_agent_tool_approval_required | bool | true | no |
| COMMERCIAL_AIRGAP_REQUIRE_ENCRYPTION | commercial_airgap_require_encryption | bool | true | no |
| COMMERCIAL_AIRGAP_REQUIRE_SIGNATURE | commercial_airgap_require_signature | bool | true | no |
| COMMERCIAL_AIRGAP_SYNC_ENABLED | commercial_airgap_sync_enabled | bool | true | no |
| COMMERCIAL_AIRGAP_SYNC_MODE | commercial_airgap_sync_mode | str | dry_run | no |
| COMMERCIAL_ANALYTICS_AGGREGATION_BUCKET_MINUTES | commercial_analytics_aggregation_bucket_minutes | int | 5 | no |
| COMMERCIAL_ANALYTICS_DEDUPE_ENABLED | commercial_analytics_dedupe_enabled | bool | true | no |
| COMMERCIAL_ANALYTICS_RETENTION_DAYS | commercial_analytics_retention_days | int | 90 | no |
| COMMERCIAL_ANOMALY_LOOKBACK_HOURS | commercial_anomaly_lookback_hours | int | 24 | no |
| COMMERCIAL_APPLIANCE_DEPLOYMENT_TIER | commercial_appliance_deployment_tier | str | regulated | no |
| COMMERCIAL_APPLIANCE_ID | commercial_appliance_id | str | appliance-000 | no |
| COMMERCIAL_APPLIANCE_MODE_ENABLED | commercial_appliance_mode_enabled | bool | false | no |
| COMMERCIAL_APPLIANCE_REQUIRE_REMOVABLE_MEDIA | commercial_appliance_require_removable_media | bool | false | no |
| COMMERCIAL_AUTOSCALING_MODE | commercial_autoscaling_mode | str | dry_run | no |
| COMMERCIAL_CALIBRATION_AUTO_APPLY | commercial_calibration_auto_apply | bool | false | no |
| COMMERCIAL_CALIBRATION_AUTO_APPLY_MAX_CHANGE_PERCENT | commercial_calibration_auto_apply_max_change_percent | float | 10.0 | no |
| COMMERCIAL_CALIBRATION_AUTO_APPLY_MIN_CONFIDENCE | commercial_calibration_auto_apply_min_confidence | str | high | no |
| COMMERCIAL_CALIBRATION_AUTO_APPLY_MIN_RECENT_SAMPLES | commercial_calibration_auto_apply_min_recent_samples | int | 20 | no |
| COMMERCIAL_CALIBRATION_AUTO_APPLY_MODE | commercial_calibration_auto_apply_mode | str | dry_run | no |
| COMMERCIAL_CALIBRATION_AUTO_APPLY_RATE_LIMIT_MINUTES | commercial_calibration_auto_apply_rate_limit_minutes | int | 60 | no |
| COMMERCIAL_CALIBRATION_AUTO_APPLY_REQUIRE_24H_DATA | commercial_calibration_auto_apply_require_24h_data | bool | true | no |
| COMMERCIAL_CALIBRATION_CANARY_DEFAULT_PERCENT | commercial_calibration_canary_default_percent | int | 5 | no |
| COMMERCIAL_CALIBRATION_CANARY_MAX_PERCENT | commercial_calibration_canary_max_percent | int | 25 | no |
| COMMERCIAL_CALIBRATION_ENABLED | commercial_calibration_enabled | bool | false | no |
| COMMERCIAL_CALIBRATION_LOOKBACK_DAYS | commercial_calibration_lookback_days | int | 7 | no |
| COMMERCIAL_CALIBRATION_MAX_MULTIPLIER | commercial_calibration_max_multiplier | float | 3.0 | no |
| COMMERCIAL_CALIBRATION_MAX_RECOMMENDED_CHANGE_PERCENT | commercial_calibration_max_recommended_change_percent | float | 25.0 | no |
| COMMERCIAL_CALIBRATION_MIN_MULTIPLIER | commercial_calibration_min_multiplier | float | 0.5 | no |
| COMMERCIAL_CALIBRATION_MIN_SAMPLES | commercial_calibration_min_samples | int | 20 | no |
| COMMERCIAL_CALIBRATION_MODE | commercial_calibration_mode | str | recommend_only | no |
| COMMERCIAL_CALIBRATION_OUTLIER_TRIM_PERCENT | commercial_calibration_outlier_trim_percent | float | 5.0 | no |
| COMMERCIAL_CALIBRATION_USE_TRIMMED_MEAN | commercial_calibration_use_trimmed_mean | bool | true | no |
| COMMERCIAL_CANARY_AUTO_PROMOTION_ENABLED | commercial_canary_auto_promotion_enabled | bool | false | no |
| COMMERCIAL_CANARY_AUTO_PROMOTION_MODE | commercial_canary_auto_promotion_mode | str | dry_run | no |
| COMMERCIAL_CANARY_AUTO_ROLLBACK_ENABLED | commercial_canary_auto_rollback_enabled | bool | true | no |
| COMMERCIAL_CANARY_MAX_ERROR_RATE_PERCENT | commercial_canary_max_error_rate_percent | float | 2.0 | no |
| COMMERCIAL_CANARY_MAX_ESTIMATION_ERROR_PERCENT | commercial_canary_max_estimation_error_percent | float | 15.0 | no |
| COMMERCIAL_CANARY_MAX_LATENCY_REGRESSION_PERCENT | commercial_canary_max_latency_regression_percent | float | 20.0 | no |
| COMMERCIAL_CANARY_MIN_MARGIN_PERCENT | commercial_canary_min_margin_percent | float | 20.0 | no |
| COMMERCIAL_CANARY_MIN_OBSERVATION_MINUTES | commercial_canary_min_observation_minutes | int | 60 | no |
| COMMERCIAL_CANARY_MIN_REQUESTS_PER_STEP | commercial_canary_min_requests_per_step | int | 100 | no |
| COMMERCIAL_CANARY_PROMOTION_STEPS | commercial_canary_promotion_steps | str | 5,10,25,50,100 | no |
| COMMERCIAL_CAPACITY_FORECAST_WINDOW_MINUTES | commercial_capacity_forecast_window_minutes | int | 60 | no |
| COMMERCIAL_CAPACITY_PLANNING_ENABLED | commercial_capacity_planning_enabled | bool | true | no |
| COMMERCIAL_CAPACITY_RETENTION_DAYS | commercial_capacity_retention_days | int | 30 | no |
| COMMERCIAL_CAPACITY_SNAPSHOT_INTERVAL_SECONDS | commercial_capacity_snapshot_interval_seconds | int | 30 | no |
| COMMERCIAL_CLUSTER_ENVIRONMENT | commercial_cluster_environment | str | local | no |
| COMMERCIAL_CLUSTER_ID | commercial_cluster_id | str | local | no |
| COMMERCIAL_CLUSTER_REGION | commercial_cluster_region | str | local | no |
| COMMERCIAL_COMPLIANCE_CONTROLS_ENABLED | commercial_compliance_controls_enabled | bool | true | no |
| COMMERCIAL_COMPLIANCE_DEFAULT_APPROVER_COUNT | commercial_compliance_default_approver_count | int | 1 | no |
| COMMERCIAL_COMPLIANCE_MODE | commercial_compliance_mode | str | report_only | no |
| COMMERCIAL_COMPLIANCE_REQUIRE_EVIDENCE | commercial_compliance_require_evidence | bool | true | no |
| COMMERCIAL_COMPLIANCE_SEGREGATION_REQUIRED | commercial_compliance_segregation_required | bool | true | no |
| COMMERCIAL_CONFIDENTIAL_DEFAULT_RETENTION_SECONDS | commercial_confidential_default_retention_seconds | int | 0 | no |
| COMMERCIAL_CONFIDENTIAL_PROHIBIT_PLAINTEXT_LOGGING | commercial_confidential_prohibit_plaintext_logging | bool | true | no |
| COMMERCIAL_CONFIDENTIAL_REQUIRE_MODEL_TRUST | commercial_confidential_require_model_trust | bool | true | no |
| COMMERCIAL_CONFIDENTIAL_RUNTIME_ENABLED | commercial_confidential_runtime_enabled | bool | false | no |
| COMMERCIAL_CONFIDENTIAL_RUNTIME_MODE | commercial_confidential_runtime_mode | str | report_only | no |
| COMMERCIAL_COST_DRIFT_ALERT_PERCENT | commercial_cost_drift_alert_percent | float | 20.0 | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_ENABLED | commercial_cross_cluster_forwarding_circuit_breaker_enabled | bool | true | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_FAILURE_THRESHOLD | commercial_cross_cluster_forwarding_circuit_breaker_failure_threshold | int | 5 | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_RESET_SECONDS | commercial_cross_cluster_forwarding_circuit_breaker_reset_seconds | int | 60 | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_ENABLED | commercial_cross_cluster_forwarding_enabled | bool | false | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_MAX_RETRIES | commercial_cross_cluster_forwarding_max_retries | int | 1 | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_MAX_SHIFTED_PERCENT | commercial_cross_cluster_forwarding_max_shifted_percent | int | 10 | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_MODE | commercial_cross_cluster_forwarding_mode | str | disabled | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_REQUIRE_JWT | commercial_cross_cluster_forwarding_require_jwt | bool | true | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_REQUIRE_MTLS | commercial_cross_cluster_forwarding_require_mtls | bool | false | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_STREAM_TIMEOUT_SECONDS | commercial_cross_cluster_forwarding_stream_timeout_seconds | int | 30 | no |
| COMMERCIAL_CROSS_CLUSTER_FORWARDING_TIMEOUT_SECONDS | commercial_cross_cluster_forwarding_timeout_seconds | int | 2 | no |
| COMMERCIAL_DISTRIBUTED_ANALYTICS_ENABLED | commercial_distributed_analytics_enabled | bool | false | no |
| COMMERCIAL_ENTERPRISE_AUDIT_EXPORT_PDF_ENABLED | commercial_enterprise_audit_export_pdf_enabled | bool | false | no |
| COMMERCIAL_ENTERPRISE_AUDIT_LOG_RETENTION_DAYS | commercial_enterprise_audit_log_retention_days | int | 365 | no |
| COMMERCIAL_ENTERPRISE_AUDIT_PORTAL_ENABLED | commercial_enterprise_audit_portal_enabled | bool | true | no |
| COMMERCIAL_ENTERPRISE_AUDIT_REQUIRE_RBAC | commercial_enterprise_audit_require_rbac | bool | true | no |
| COMMERCIAL_EXECUTION_PROOFS_ENABLED | commercial_execution_proofs_enabled | bool | true | no |
| COMMERCIAL_EXECUTION_PROOFS_EXPORT_ENABLED | commercial_execution_proofs_export_enabled | bool | true | no |
| COMMERCIAL_EXECUTIVE_DASHBOARD_ENABLED | commercial_executive_dashboard_enabled | bool | true | no |
| COMMERCIAL_FEDERATION_ALLOW_PUSH | commercial_federation_allow_push | bool | false | no |
| COMMERCIAL_FEDERATION_ENABLED | commercial_federation_enabled | bool | false | no |
| COMMERCIAL_FEDERATION_MODE | commercial_federation_mode | str | disabled | no |
| COMMERCIAL_FEDERATION_REQUIRE_TOKEN | commercial_federation_require_token | bool | <redacted> | yes |
| COMMERCIAL_FEDERATION_RETENTION_DAYS | commercial_federation_retention_days | int | 180 | no |
| COMMERCIAL_FEDERATION_SHARED_TOKEN | commercial_federation_shared_token | str | <empty> | yes |
| COMMERCIAL_FEDERATION_SYNC_INTERVAL_SECONDS | commercial_federation_sync_interval_seconds | int | 300 | no |
| COMMERCIAL_FINANCIAL_ANOMALY_DETECTION_ENABLED | commercial_financial_anomaly_detection_enabled | bool | true | no |
| COMMERCIAL_FINANCIAL_ANOMALY_MIN_SAMPLES | commercial_financial_anomaly_min_samples | int | 7 | no |
| COMMERCIAL_FINANCIAL_ANOMALY_PERCENT_THRESHOLD | commercial_financial_anomaly_percent_threshold | float | 30.0 | no |
| COMMERCIAL_FINANCIAL_ANOMALY_ZSCORE_THRESHOLD | commercial_financial_anomaly_zscore_threshold | float | 3.0 | no |
| COMMERCIAL_FINANCIAL_AUDIT_CHAIN_ENABLED | commercial_financial_audit_chain_enabled | bool | true | no |
| COMMERCIAL_FINANCIAL_DISPUTE_ENABLED | commercial_financial_dispute_enabled | bool | true | no |
| COMMERCIAL_FINANCIAL_MANUAL_CREDIT_ENABLED | commercial_financial_manual_credit_enabled | bool | false | no |
| COMMERCIAL_FINANCIAL_RECONCILIATION_ENABLED | commercial_financial_reconciliation_enabled | bool | true | no |
| COMMERCIAL_FINANCIAL_RECONCILIATION_THRESHOLD_PERCENT | commercial_financial_reconciliation_threshold_percent | float | 2.0 | no |
| COMMERCIAL_GEO_ROUTING_ALLOW_CROSS_OCEAN | commercial_geo_routing_allow_cross_ocean | bool | false | no |
| COMMERCIAL_GEO_ROUTING_ENABLED | commercial_geo_routing_enabled | bool | false | no |
| COMMERCIAL_GEO_ROUTING_HEALTH_WEIGHT | commercial_geo_routing_health_weight | float | 0.15 | no |
| COMMERCIAL_GEO_ROUTING_LATENCY_PENALTY_WEIGHT | commercial_geo_routing_latency_penalty_weight | float | 0.35 | no |
| COMMERCIAL_GEO_ROUTING_MARGIN_WEIGHT | commercial_geo_routing_margin_weight | float | 0.35 | no |
| COMMERCIAL_GEO_ROUTING_MAX_REGION_DISTANCE_KM | commercial_geo_routing_max_region_distance_km | int | 5000 | no |
| COMMERCIAL_GEO_ROUTING_MODE | commercial_geo_routing_mode | str | dry_run | no |
| COMMERCIAL_GEO_ROUTING_REGION_WEIGHT | commercial_geo_routing_region_weight | float | 0.15 | no |
| COMMERCIAL_GLOBAL_ROUTING_ALLOW_CROSS_REGION | commercial_global_routing_allow_cross_region | bool | false | no |
| COMMERCIAL_GLOBAL_ROUTING_ENABLED | commercial_global_routing_enabled | bool | false | no |
| COMMERCIAL_GLOBAL_ROUTING_HEALTH_WEIGHT | commercial_global_routing_health_weight | float | 0.15 | no |
| COMMERCIAL_GLOBAL_ROUTING_LATENCY_WEIGHT | commercial_global_routing_latency_weight | float | 0.25 | no |
| COMMERCIAL_GLOBAL_ROUTING_MARGIN_WEIGHT | commercial_global_routing_margin_weight | float | 0.4 | no |
| COMMERCIAL_GLOBAL_ROUTING_MAX_LATENCY_MS | commercial_global_routing_max_latency_ms | int | 5000 | no |
| COMMERCIAL_GLOBAL_ROUTING_MODE | commercial_global_routing_mode | str | disabled | no |
| COMMERCIAL_GLOBAL_ROUTING_PRIORITY_WEIGHT | commercial_global_routing_priority_weight | float | 0.1 | no |
| COMMERCIAL_GLOBAL_ROUTING_REGION_WEIGHT | commercial_global_routing_region_weight | float | 0.1 | no |
| COMMERCIAL_GLOBAL_ROUTING_REQUIRE_HEALTHY_CLUSTER | commercial_global_routing_require_healthy_cluster | bool | true | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_AUTO_ROLLBACK | commercial_global_traffic_shifting_auto_rollback | bool | true | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_DEFAULT_CANARY_PERCENT | commercial_global_traffic_shifting_default_canary_percent | int | 1 | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_ENABLED | commercial_global_traffic_shifting_enabled | bool | false | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_CANARY_PERCENT | commercial_global_traffic_shifting_max_canary_percent | int | 10 | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_ERROR_RATE_PERCENT | commercial_global_traffic_shifting_max_error_rate_percent | float | 2.0 | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_LATENCY_REGRESSION_PERCENT | commercial_global_traffic_shifting_max_latency_regression_percent | float | 20.0 | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MIN_MARGIN_PERCENT | commercial_global_traffic_shifting_min_margin_percent | float | 20.0 | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MODE | commercial_global_traffic_shifting_mode | str | dry_run | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_REQUIRE_ADMIN_APPROVAL | commercial_global_traffic_shifting_require_admin_approval | bool | true | no |
| COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_REQUIRE_HEALTHY_TARGET | commercial_global_traffic_shifting_require_healthy_target | bool | true | no |
| COMMERCIAL_GOVERNANCE_FEDERATION_CLUSTER_ID | commercial_governance_federation_cluster_id | str | local | no |
| COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED | commercial_governance_federation_enabled | bool | false | no |
| COMMERCIAL_GOVERNANCE_FEDERATION_MODE | commercial_governance_federation_mode | str | disabled | no |
| COMMERCIAL_GOVERNANCE_FEDERATION_REGION | commercial_governance_federation_region | str | local | no |
| COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_SIGNATURE | commercial_governance_federation_require_signature | bool | true | no |
| COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_TOKEN | commercial_governance_federation_require_token | bool | <redacted> | yes |
| COMMERCIAL_GOVERNANCE_FEDERATION_SHARED_TOKEN | commercial_governance_federation_shared_token | str | <empty> | yes |
| COMMERCIAL_GOVERNANCE_FEDERATION_SYNC_INTERVAL_SECONDS | commercial_governance_federation_sync_interval_seconds | int | 300 | no |
| COMMERCIAL_GPU_UTILIZATION_ALERT_PERCENT | commercial_gpu_utilization_alert_percent | float | 90.0 | no |
| COMMERCIAL_GUARDRAILS_ENABLED | commercial_guardrails_enabled | bool | false | no |
| COMMERCIAL_HARDWARE_ATTESTATION_ENABLED | commercial_hardware_attestation_enabled | bool | false | no |
| COMMERCIAL_HARDWARE_ATTESTATION_MODE | commercial_hardware_attestation_mode | str | report_only | no |
| COMMERCIAL_INFRA_ADAPTERS_ENABLED | commercial_infra_adapters_enabled | str | mock | no |
| COMMERCIAL_INFRA_EXECUTION_ENABLED | commercial_infra_execution_enabled | bool | false | no |
| COMMERCIAL_INFRA_EXECUTION_MODE | commercial_infra_execution_mode | str | simulation_only | no |
| COMMERCIAL_INFRA_REQUIRE_APPROVAL | commercial_infra_require_approval | bool | true | no |
| COMMERCIAL_INFRA_REQUIRE_FENCING | commercial_infra_require_fencing | bool | true | no |
| COMMERCIAL_INFRA_REQUIRE_LEADER | commercial_infra_require_leader | bool | true | no |
| COMMERCIAL_INFRA_SIMULATION_ENABLED | commercial_infra_simulation_enabled | bool | true | no |
| COMMERCIAL_K8S_CONTEXT | commercial_k8s_context | str | - | no |
| COMMERCIAL_K8S_DRY_RUN | commercial_k8s_dry_run | bool | true | no |
| COMMERCIAL_K8S_EXECUTION_ENABLED | commercial_k8s_execution_enabled | bool | false | no |
| COMMERCIAL_K8S_NAMESPACE | commercial_k8s_namespace | str | default | no |
| COMMERCIAL_LATENCY_DRIFT_ALERT_PERCENT | commercial_latency_drift_alert_percent | float | 25.0 | no |
| COMMERCIAL_LATENCY_WEIGHT | commercial_latency_weight | float | 0.15 | no |
| COMMERCIAL_LEADER_ELECTION_ENABLED | commercial_leader_election_enabled | bool | true | no |
| COMMERCIAL_LEADER_FENCING_ENABLED | commercial_leader_fencing_enabled | bool | true | no |
| COMMERCIAL_LEASE_DURATION_SECONDS | commercial_lease_duration_seconds | int | 60 | no |
| COMMERCIAL_LEASE_HEARTBEAT_SECONDS | commercial_lease_heartbeat_seconds | int | 15 | no |
| COMMERCIAL_LEASE_MAX_CLOCK_SKEW_SECONDS | commercial_lease_max_clock_skew_seconds | int | 5 | no |
| COMMERCIAL_LEASE_RENEW_BEFORE_SECONDS | commercial_lease_renew_before_seconds | int | 20 | no |
| COMMERCIAL_LIVE_BALANCING_ENABLED | commercial_live_balancing_enabled | bool | false | no |
| COMMERCIAL_LIVE_BALANCING_HYSTERESIS_PERCENT | commercial_live_balancing_hysteresis_percent | float | 10.0 | no |
| COMMERCIAL_LIVE_BALANCING_MAX_LATENCY_MS | commercial_live_balancing_max_latency_ms | int | 5000 | no |
| COMMERCIAL_LIVE_BALANCING_MAX_TRAFFIC_CHANGE_PERCENT | commercial_live_balancing_max_traffic_change_percent | int | 5 | no |
| COMMERCIAL_LIVE_BALANCING_MIN_MARGIN_PERCENT | commercial_live_balancing_min_margin_percent | float | 20.0 | no |
| COMMERCIAL_LIVE_BALANCING_MIN_STABLE_MINUTES | commercial_live_balancing_min_stable_minutes | int | 30 | no |
| COMMERCIAL_LIVE_BALANCING_MODE | commercial_live_balancing_mode | str | dry_run | no |
| COMMERCIAL_LIVE_BALANCING_REBALANCE_INTERVAL_SECONDS | commercial_live_balancing_rebalance_interval_seconds | int | 300 | no |
| COMMERCIAL_LOCAL_GPU_ALLOW_POWER_LIMIT | commercial_local_gpu_allow_power_limit | bool | false | no |
| COMMERCIAL_LOCAL_GPU_ALLOW_PROCESS_KILL | commercial_local_gpu_allow_process_kill | bool | false | no |
| COMMERCIAL_LOCAL_GPU_ALLOW_SERVICE_RESTART | commercial_local_gpu_allow_service_restart | bool | false | no |
| COMMERCIAL_LOCAL_GPU_ALLOWED_ACTIONS | commercial_local_gpu_allowed_actions | str | inspect,metrics | no |
| COMMERCIAL_LOCAL_GPU_DRY_RUN | commercial_local_gpu_dry_run | bool | true | no |
| COMMERCIAL_LOCAL_GPU_EXECUTION_ENABLED | commercial_local_gpu_execution_enabled | bool | false | no |
| COMMERCIAL_LOCAL_ROUTE_BONUS | commercial_local_route_bonus | float | 10.0 | no |
| COMMERCIAL_MARGIN_DRIFT_ALERT_PERCENT | commercial_margin_drift_alert_percent | float | 15.0 | no |
| COMMERCIAL_MARGIN_WEIGHT | commercial_margin_weight | float | 0.6 | no |
| COMMERCIAL_MAX_AUTOSCALING_COST_INCREASE_PERCENT | commercial_max_autoscaling_cost_increase_percent | float | 20.0 | no |
| COMMERCIAL_MAX_AUTOSCALING_MARGIN_DROP_PERCENT | commercial_max_autoscaling_margin_drop_percent | float | 10.0 | no |
| COMMERCIAL_MAX_AUTOSCALING_SLA_RISK_PERCENT | commercial_max_autoscaling_sla_risk_percent | float | 5.0 | no |
| COMMERCIAL_MAX_BLAST_RADIUS | commercial_max_blast_radius | str | medium | no |
| COMMERCIAL_MERKLE_TIMELINE_AUTO_SEAL | commercial_merkle_timeline_auto_seal | bool | false | no |
| COMMERCIAL_MERKLE_TIMELINE_WINDOW_MINUTES | commercial_merkle_timeline_window_minutes | int | 60 | no |
| COMMERCIAL_MERKLE_TIMELINES_ENABLED | commercial_merkle_timelines_enabled | bool | true | no |
| COMMERCIAL_MIN_MARGIN_PERCENT | commercial_min_margin_percent | float | 20.0 | no |
| COMMERCIAL_MODEL_INTEGRITY_AUTO_QUARANTINE | commercial_model_integrity_auto_quarantine | bool | false | no |
| COMMERCIAL_MODEL_INTEGRITY_BOOT_SCAN_ENABLED | commercial_model_integrity_boot_scan_enabled | bool | true | no |
| COMMERCIAL_MODEL_INTEGRITY_MONITOR_ENABLED | commercial_model_integrity_monitor_enabled | bool | true | no |
| COMMERCIAL_MODEL_INTEGRITY_SCAN_INTERVAL_SECONDS | commercial_model_integrity_scan_interval_seconds | int | 3600 | no |
| COMMERCIAL_MODEL_LIFECYCLE_AUTO_QUARANTINE | commercial_model_lifecycle_auto_quarantine | bool | false | no |
| COMMERCIAL_MODEL_LIFECYCLE_ENABLED | commercial_model_lifecycle_enabled | bool | true | no |
| COMMERCIAL_MODEL_LIFECYCLE_MODE | commercial_model_lifecycle_mode | str | report_only | no |
| COMMERCIAL_MODEL_LIFECYCLE_OFFLINE_VERIFICATION_STRICT | commercial_model_lifecycle_offline_verification_strict | bool | true | no |
| COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_APPROVAL | commercial_model_lifecycle_require_approval | bool | true | no |
| COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_CHECKSUM | commercial_model_lifecycle_require_checksum | bool | true | no |
| COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_LINEAGE | commercial_model_lifecycle_require_lineage | bool | true | no |
| COMMERCIAL_MODEL_QUARANTINE_ON_CHECKSUM_MISMATCH | commercial_model_quarantine_on_checksum_mismatch | bool | true | no |
| COMMERCIAL_MODEL_REQUIRE_CHECKSUM_FOR_LOCAL | commercial_model_require_checksum_for_local | bool | true | no |
| COMMERCIAL_MODEL_REQUIRE_TRUSTED_FOR_ROUTING | commercial_model_require_trusted_for_routing | bool | false | no |
| COMMERCIAL_MODEL_SUPPLY_CHAIN_ENABLED | commercial_model_supply_chain_enabled | bool | true | no |
| COMMERCIAL_MODEL_TRUST_ENFORCEMENT_MODE | commercial_model_trust_enforcement_mode | str | report_only | no |
| COMMERCIAL_NEGATIVE_MARGIN_ALERT | commercial_negative_margin_alert | bool | true | no |
| COMMERCIAL_NODE_HEARTBEAT_INTERVAL_SECONDS | commercial_node_heartbeat_interval_seconds | int | 30 | no |
| COMMERCIAL_NODE_OFFLINE_AFTER_SECONDS | commercial_node_offline_after_seconds | int | 120 | no |
| COMMERCIAL_NOMAD_ADDR | commercial_nomad_addr | str | - | no |
| COMMERCIAL_NOMAD_DRY_RUN | commercial_nomad_dry_run | bool | true | no |
| COMMERCIAL_NOMAD_EXECUTION_ENABLED | commercial_nomad_execution_enabled | bool | false | no |
| COMMERCIAL_NOMAD_TOKEN | commercial_nomad_token | str | <empty> | yes |
| COMMERCIAL_OFFLINE_CRL_ENABLED | commercial_offline_crl_enabled | bool | true | no |
| COMMERCIAL_OPERATIONAL_CONTROL_DEFAULT_EVIDENCE_SLA_DAYS | commercial_operational_control_default_evidence_sla_days | int | 90 | no |
| COMMERCIAL_OPERATIONAL_CONTROL_OVERDUE_ESCALATIONS_ENABLED | commercial_operational_control_overdue_escalations_enabled | bool | true | no |
| COMMERCIAL_OPERATIONAL_CONTROLS_ENABLED | commercial_operational_controls_enabled | bool | true | no |
| COMMERCIAL_OPERATIONAL_CONTROLS_MODE | commercial_operational_controls_mode | str | report_only | no |
| COMMERCIAL_P95_LATENCY_ALERT_MS | commercial_p95_latency_alert_ms | int | 5000 | no |
| COMMERCIAL_PROXMOX_ALLOWED_CT_IDS | commercial_proxmox_allowed_ct_ids | str | - | no |
| COMMERCIAL_PROXMOX_ALLOWED_VM_IDS | commercial_proxmox_allowed_vm_ids | str | - | no |
| COMMERCIAL_PROXMOX_API_URL | commercial_proxmox_api_url | str | - | no |
| COMMERCIAL_PROXMOX_DRY_RUN | commercial_proxmox_dry_run | bool | true | no |
| COMMERCIAL_PROXMOX_EXECUTION_ENABLED | commercial_proxmox_execution_enabled | bool | false | no |
| COMMERCIAL_PROXMOX_NODE | commercial_proxmox_node | str | - | no |
| COMMERCIAL_PROXMOX_TOKEN_ID | commercial_proxmox_token_id | str | <empty> | yes |
| COMMERCIAL_PROXMOX_TOKEN_SECRET | commercial_proxmox_token_secret | str | <empty> | yes |
| COMMERCIAL_PROXMOX_VERIFY_TLS | commercial_proxmox_verify_tls | bool | true | no |
| COMMERCIAL_PUBLIC_ATTESTATION_ALLOW_ANONYMOUS | commercial_public_attestation_allow_anonymous | bool | false | no |
| COMMERCIAL_PUBLIC_ATTESTATION_GATEWAY_ENABLED | commercial_public_attestation_gateway_enabled | bool | false | no |
| COMMERCIAL_PUBLIC_ATTESTATION_MAX_PAYLOAD_KB | commercial_public_attestation_max_payload_kb | int | 512 | no |
| COMMERCIAL_PUBLIC_ATTESTATION_MODE | commercial_public_attestation_mode | str | local_only | no |
| COMMERCIAL_PUBLIC_ATTESTATION_RATE_LIMIT_RPM | commercial_public_attestation_rate_limit_rpm | int | 60 | no |
| COMMERCIAL_QOS_BASIC_RPM | commercial_qos_basic_rpm | int | 60 | no |
| COMMERCIAL_QOS_BILLING_DEBIT_WALLET | commercial_qos_billing_debit_wallet | bool | false | no |
| COMMERCIAL_QOS_BILLING_ENABLED | commercial_qos_billing_enabled | bool | false | no |
| COMMERCIAL_QOS_BILLING_INCLUDE_OPPORTUNITY_COST | commercial_qos_billing_include_opportunity_cost | bool | false | no |
| COMMERCIAL_QOS_BILLING_INVOICE_LINE_ITEM | commercial_qos_billing_invoice_line_item | bool | true | no |
| COMMERCIAL_QOS_BILLING_MAX_DAILY_DEBIT_BRL_PER_CLIENT | commercial_qos_billing_max_daily_debit_brl_per_client | float | 100.0 | no |
| COMMERCIAL_QOS_BILLING_MIN_AMOUNT_BRL | commercial_qos_billing_min_amount_brl | float | 0.01 | no |
| COMMERCIAL_QOS_BILLING_MODE | commercial_qos_billing_mode | str | report_only | no |
| COMMERCIAL_QOS_CHARGEBACK_ENABLED | commercial_qos_chargeback_enabled | bool | true | no |
| COMMERCIAL_QOS_CHARGEBACK_MODE | commercial_qos_chargeback_mode | str | report_only | no |
| COMMERCIAL_QOS_ENTERPRISE_RPM | commercial_qos_enterprise_rpm | int | 5000 | no |
| COMMERCIAL_QOS_FAIRNESS_COLLECTION_INTERVAL_SECONDS | commercial_qos_fairness_collection_interval_seconds | int | 60 | no |
| COMMERCIAL_QOS_FAIRNESS_ENABLED | commercial_qos_fairness_enabled | bool | true | no |
| COMMERCIAL_QOS_FREE_RPM | commercial_qos_free_rpm | int | 10 | no |
| COMMERCIAL_QOS_MAX_STARVATION_SECONDS | commercial_qos_max_starvation_seconds | int | 1800 | no |
| COMMERCIAL_QOS_PREMIUM_RPM | commercial_qos_premium_rpm | int | 1000 | no |
| COMMERCIAL_QOS_PRIORITY_INVERSION_ALERT | commercial_qos_priority_inversion_alert | bool | true | no |
| COMMERCIAL_QOS_PRIORITY_QUEUE_ENABLED | commercial_qos_priority_queue_enabled | bool | false | no |
| COMMERCIAL_QOS_PRIORITY_QUEUE_MODE | commercial_qos_priority_queue_mode | str | shadow | no |
| COMMERCIAL_QOS_PRIORITY_SLOT_COST_BRL_PER_SECOND | commercial_qos_priority_slot_cost_brl_per_second | float | 0.001 | no |
| COMMERCIAL_QOS_PRO_RPM | commercial_qos_pro_rpm | int | 300 | no |
| COMMERCIAL_QOS_QUEUE_AGING_SECONDS | commercial_qos_queue_aging_seconds | int | 300 | no |
| COMMERCIAL_QOS_RATE_LIMIT_MODE | commercial_qos_rate_limit_mode | str | report_only | no |
| COMMERCIAL_QOS_RATE_LIMITING_ENABLED | commercial_qos_rate_limiting_enabled | bool | true | no |
| COMMERCIAL_QOS_STARVATION_THRESHOLD_SECONDS | commercial_qos_starvation_threshold_seconds | int | 1800 | no |
| COMMERCIAL_QUALITY_WEIGHT | commercial_quality_weight | float | 0.25 | no |
| COMMERCIAL_QUEUE_DEPTH_ALERT | commercial_queue_depth_alert | int | 100 | no |
| COMMERCIAL_RAG_VAULT_ENABLE_IMMUTABLE_AUDIT | commercial_rag_vault_enable_immutable_audit | bool | true | no |
| COMMERCIAL_RAG_VAULT_ENABLE_POISON_DETECTION | commercial_rag_vault_enable_poison_detection | bool | true | no |
| COMMERCIAL_RAG_VAULT_ENABLED | commercial_rag_vault_enabled | bool | false | no |
| COMMERCIAL_RAG_VAULT_MAX_CONTEXT_CHUNKS | commercial_rag_vault_max_context_chunks | int | 20 | no |
| COMMERCIAL_RAG_VAULT_POLICY_MODE | commercial_rag_vault_policy_mode | str | report_only | no |
| COMMERCIAL_RAG_VAULT_REQUIRE_CONFIDENTIAL_RUNTIME | commercial_rag_vault_require_confidential_runtime | bool | false | no |
| COMMERCIAL_RAG_VAULT_REQUIRE_SIGNED_DOCUMENTS | commercial_rag_vault_require_signed_documents | bool | false | no |
| COMMERCIAL_RECEIPT_SIGNATURE_ALGORITHM | commercial_receipt_signature_algorithm | str | ed25519 | no |
| COMMERCIAL_RECEIPTS_CHAINING_ENABLED | commercial_receipts_chaining_enabled | bool | true | no |
| COMMERCIAL_RECEIPTS_ENABLED | commercial_receipts_enabled | bool | true | no |
| COMMERCIAL_RECEIPTS_EXPORT_ENABLED | commercial_receipts_export_enabled | bool | true | no |
| COMMERCIAL_RECEIPTS_SIGNATURE_REQUIRED | commercial_receipts_signature_required | bool | false | no |
| COMMERCIAL_RECEIPTS_TIMESTAMP_MODE | commercial_receipts_timestamp_mode | str | local | no |
| COMMERCIAL_REPLAY_ALLOW_CROSS_BACKEND | commercial_replay_allow_cross_backend | bool | false | no |
| COMMERCIAL_REPLAY_CAPTURE_PROMPT_HASH_ONLY | commercial_replay_capture_prompt_hash_only | bool | true | no |
| COMMERCIAL_REPLAY_DEFAULT_MODE | commercial_replay_default_mode | str | best_effort | no |
| COMMERCIAL_REPLAY_MAX_AGE_DAYS | commercial_replay_max_age_days | int | 30 | no |
| COMMERCIAL_REPORT_DEFAULT_RECIPIENTS | commercial_report_default_recipients | str | - | no |
| COMMERCIAL_REPORT_EMAIL_ALLOWLIST | commercial_report_email_allowlist | str | - | no |
| COMMERCIAL_REPORT_EMAIL_ENABLED | commercial_report_email_enabled | bool | false | no |
| COMMERCIAL_REPORT_EMAIL_MAX_RECIPIENTS | commercial_report_email_max_recipients | int | 10 | no |
| COMMERCIAL_REPORT_EMAIL_MODE | commercial_report_email_mode | str | disabled | no |
| COMMERCIAL_REPORT_EMAIL_PROVIDER | commercial_report_email_provider | str | disabled | no |
| COMMERCIAL_REPORT_EMAIL_RETRY_BACKOFF_SECONDS | commercial_report_email_retry_backoff_seconds | int | 10 | no |
| COMMERCIAL_REPORT_EMAIL_RETRY_COUNT | commercial_report_email_retry_count | int | 3 | no |
| COMMERCIAL_REPORT_SEND_REAL_EMAIL | commercial_report_send_real_email | bool | false | no |
| COMMERCIAL_REPORT_SMTP_FROM | commercial_report_smtp_from | str | - | no |
| COMMERCIAL_REPORT_SMTP_HOST | commercial_report_smtp_host | str | - | no |
| COMMERCIAL_REPORT_SMTP_PASSWORD | commercial_report_smtp_password | str | <empty> | yes |
| COMMERCIAL_REPORT_SMTP_PORT | commercial_report_smtp_port | int | 587 | no |
| COMMERCIAL_REPORT_SMTP_TIMEOUT_SECONDS | commercial_report_smtp_timeout_seconds | int | 15 | no |
| COMMERCIAL_REPORT_SMTP_USE_STARTTLS | commercial_report_smtp_use_starttls | bool | true | no |
| COMMERCIAL_REPORT_SMTP_USE_TLS | commercial_report_smtp_use_tls | bool | true | no |
| COMMERCIAL_REPORT_SMTP_USERNAME | commercial_report_smtp_username | str | - | no |
| COMMERCIAL_REPRODUCIBILITY_ENABLED | commercial_reproducibility_enabled | bool | true | no |
| COMMERCIAL_REQUIRE_APPROVAL_FOR_CRITICAL | commercial_require_approval_for_critical | bool | true | no |
| COMMERCIAL_REVENUE_EMAIL_ESCALATION_ENABLED | commercial_revenue_email_escalation_enabled | bool | false | no |
| COMMERCIAL_REVENUE_EMAIL_ESCALATION_RECIPIENTS | commercial_revenue_email_escalation_recipients | str | - | no |
| COMMERCIAL_REVENUE_ESCALATION_COOLDOWN_MINUTES | commercial_revenue_escalation_cooldown_minutes | int | 30 | no |
| COMMERCIAL_REVENUE_ESCALATION_MAX_RETRIES | commercial_revenue_escalation_max_retries | int | 3 | no |
| COMMERCIAL_REVENUE_ESCALATIONS_ENABLED | commercial_revenue_escalations_enabled | bool | true | no |
| COMMERCIAL_REVENUE_ESCALATIONS_MODE | commercial_revenue_escalations_mode | str | dry_run | no |
| COMMERCIAL_REVENUE_FORECAST_METHOD | commercial_revenue_forecast_method | str | ewma | no |
| COMMERCIAL_REVENUE_FORECAST_MIN_SAMPLES | commercial_revenue_forecast_min_samples | int | 7 | no |
| COMMERCIAL_REVENUE_FORECAST_WINDOW_DAYS | commercial_revenue_forecast_window_days | int | 30 | no |
| COMMERCIAL_REVENUE_FORECASTING_ENABLED | commercial_revenue_forecasting_enabled | bool | true | no |
| COMMERCIAL_REVENUE_PAGERDUTY_ENABLED | commercial_revenue_pagerduty_enabled | bool | false | no |
| COMMERCIAL_REVENUE_PAGERDUTY_ROUTING_KEY | commercial_revenue_pagerduty_routing_key | str | <empty> | yes |
| COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE | commercial_revenue_protection_allow_enforce | bool | false | no |
| COMMERCIAL_REVENUE_PROTECTION_COOLDOWN_MINUTES | commercial_revenue_protection_cooldown_minutes | int | 60 | no |
| COMMERCIAL_REVENUE_PROTECTION_ENABLED | commercial_revenue_protection_enabled | bool | true | no |
| COMMERCIAL_REVENUE_PROTECTION_MODE | commercial_revenue_protection_mode | str | report_only | no |
| COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_ENABLED | commercial_revenue_protection_webhook_enabled | bool | false | no |
| COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_URL | commercial_revenue_protection_webhook_url | str | - | no |
| COMMERCIAL_REVENUE_SLACK_ENABLED | commercial_revenue_slack_enabled | bool | false | no |
| COMMERCIAL_REVENUE_SLACK_WEBHOOK_URL | commercial_revenue_slack_webhook_url | str | - | no |
| COMMERCIAL_REVENUE_WEBHOOK_ENABLED | commercial_revenue_webhook_enabled | bool | false | no |
| COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET | commercial_revenue_webhook_signing_secret | str | <empty> | yes |
| COMMERCIAL_REVENUE_WEBHOOK_URL | commercial_revenue_webhook_url | str | - | no |
| COMMERCIAL_ROUTING_DEFAULT_POLICY | commercial_routing_default_policy | str | disabled | no |
| COMMERCIAL_ROUTING_ENABLED | commercial_routing_enabled | bool | false | no |
| COMMERCIAL_RUNTIME_ATTESTATION_BLOCK_UNTRUSTED | commercial_runtime_attestation_block_untrusted | bool | false | no |
| COMMERCIAL_RUNTIME_ATTESTATION_CHALLENGE_TTL_SECONDS | commercial_runtime_attestation_challenge_ttl_seconds | int | 60 | no |
| COMMERCIAL_RUNTIME_ATTESTATION_ENABLED | commercial_runtime_attestation_enabled | bool | false | no |
| COMMERCIAL_RUNTIME_ATTESTATION_ENCLAVE_TYPE | commercial_runtime_attestation_enclave_type | str | software_attested | no |
| COMMERCIAL_RUNTIME_ATTESTATION_ENFORCE_ON_STARTUP | commercial_runtime_attestation_enforce_on_startup | bool | false | no |
| COMMERCIAL_RUNTIME_ATTESTATION_EVIDENCE_TTL_SECONDS | commercial_runtime_attestation_evidence_ttl_seconds | int | 3600 | no |
| COMMERCIAL_RUNTIME_ATTESTATION_MAX_DRIFT_THRESHOLD | commercial_runtime_attestation_max_drift_threshold | float | 0.1 | no |
| COMMERCIAL_RUNTIME_ATTESTATION_MIN_TRUST_SCORE | commercial_runtime_attestation_min_trust_score | float | 0.0 | no |
| COMMERCIAL_RUNTIME_ATTESTATION_MODE | commercial_runtime_attestation_mode | str | report_only | no |
| COMMERCIAL_RUNTIME_ATTESTATION_PLATFORM_TYPE | commercial_runtime_attestation_platform_type | str | linux_x86_64 | no |
| COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SENSITIVE_TENANTS | commercial_runtime_attestation_require_for_sensitive_tenants | bool | false | no |
| COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SOVEREIGN | commercial_runtime_attestation_require_for_sovereign | bool | false | no |
| COMMERCIAL_SAFETY_GATES_ENABLED | commercial_safety_gates_enabled | bool | true | no |
| COMMERCIAL_SLA_RISK_ALERT_PERCENT | commercial_sla_risk_alert_percent | float | 5.0 | no |
| COMMERCIAL_SOVEREIGN_GOVERNANCE_ENABLED | commercial_sovereign_governance_enabled | bool | true | no |
| COMMERCIAL_SOVEREIGN_LIFECYCLE_BLOCK_UNAPPROVED | commercial_sovereign_lifecycle_block_unapproved | bool | false | no |
| COMMERCIAL_SOVEREIGN_LIFECYCLE_ENFORCE | commercial_sovereign_lifecycle_enforce | bool | false | no |
| COMMERCIAL_TENANT_ENCRYPTION_AUTO_ROTATION_DAYS | commercial_tenant_encryption_auto_rotation_days | int | 90 | no |
| COMMERCIAL_TENANT_ENCRYPTION_BLOCK_RESTRICTED_EXPORTS | commercial_tenant_encryption_block_restricted_exports | bool | true | no |
| COMMERCIAL_TENANT_ENCRYPTION_ENABLED | commercial_tenant_encryption_enabled | bool | true | no |
| COMMERCIAL_TENANT_ENCRYPTION_MASTER_KEY | commercial_tenant_encryption_master_key | str | <redacted> | yes |
| COMMERCIAL_TENANT_ENCRYPTION_MODE | commercial_tenant_encryption_mode | str | report_only | no |
| COMMERCIAL_TENANT_ENCRYPTION_REQUIRE_ENCRYPTED_EXPORTS | commercial_tenant_encryption_require_encrypted_exports | bool | false | no |
| COMMERCIAL_TRANSPARENCY_CHECKPOINT_INTERVAL_MINUTES | commercial_transparency_checkpoint_interval_minutes | int | 60 | no |
| COMMERCIAL_TRANSPARENCY_GOSSIP_ENABLED | commercial_transparency_gossip_enabled | bool | false | no |
| COMMERCIAL_TRANSPARENCY_GOSSIP_MODE | commercial_transparency_gossip_mode | str | dry_run | no |
| COMMERCIAL_TRANSPARENCY_REQUIRE_WITNESS_QUORUM | commercial_transparency_require_witness_quorum | bool | false | no |
| COMMERCIAL_TRANSPARENCY_SPLIT_VIEW_ALERTS | commercial_transparency_split_view_alerts | bool | true | no |
| COMMERCIAL_WITNESS_FEDERATION_ENABLED | commercial_witness_federation_enabled | bool | false | no |
| COMMERCIAL_WITNESS_MIN_SIGNATURES | commercial_witness_min_signatures | int | 1 | no |
| COMMERCIAL_WITNESS_MODE | commercial_witness_mode | str | dry_run | no |
| COMMERCIAL_WITNESS_REQUEST_TIMEOUT_SECONDS | commercial_witness_request_timeout_seconds | int | 10 | no |
| COMMERCIAL_WITNESS_REQUIRE_EXTERNAL | commercial_witness_require_external | bool | false | no |
| COMMERCIAL_WITNESS_SIGNATURE_ALGORITHM | commercial_witness_signature_algorithm | str | ed25519 | no |
| COMMERCIAL_WORKFLOW_CHECKPOINT_FREQUENCY | commercial_workflow_checkpoint_frequency | int | 1 | no |
| COMMERCIAL_WORKFLOW_DETERMINISM_ENABLED | commercial_workflow_determinism_enabled | bool | false | no |
| COMMERCIAL_WORKFLOW_DRIFT_THRESHOLD | commercial_workflow_drift_threshold | float | 0.01 | no |
| COMMERCIAL_WORKFLOW_ENFORCE_REPRODUCIBILITY | commercial_workflow_enforce_reproducibility | bool | true | no |

## `content`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CONTENT_MODERATION_ENABLED | content_moderation_enabled | bool | true | no |
| CONTENT_MODERATION_TOXICITY_THRESHOLD | content_moderation_toxicity_threshold | float | 0.7 | no |

## `control`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CONTROL_PLANE_HOST | control_plane_host | str | 0.0.0.0 | no |
| CONTROL_PLANE_PORT | control_plane_port | int | 8080 | no |

## `cors`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CORS_ALLOW_ORIGINS | cors_allow_origins | str | - | no |

## `create`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| CREATE_TABLES_ON_STARTUP | create_tables_on_startup | bool | false | no |

## `data`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DATA_PLANE_BASE_URL | data_plane_base_url | str | required | no |
| DATA_PLANE_TIMEOUT_SECONDS | data_plane_timeout_seconds | int | 120 | no |
| DATA_RESIDENCY_ENABLED | data_residency_enabled | bool | false | no |

## `database`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DATABASE_URL | database_url | str | required | no |

## `debug`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DEBUG | debug | bool | false | no |

## `deepseek`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DEEPSEEK_API_KEY | deepseek_api_key | str | <empty> | yes |
| DEEPSEEK_BASE_URL | deepseek_base_url | str | - | no |
| DEEPSEEK_CHAT_MODEL | deepseek_chat_model | str | - | no |
| DEEPSEEK_PROVIDER_ENABLED | deepseek_provider_enabled | bool | true | no |

## `default`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DEFAULT_EMBEDDING_MODEL | default_embedding_model | str | text-embedding-3-small | no |
| DEFAULT_MAX_TOKENS | default_max_tokens | int | <redacted> | yes |
| DEFAULT_TEMPERATURE | default_temperature | float | 0.7 | no |
| DEFAULT_TOP_P | default_top_p | float | 0.95 | no |

## `demo`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DEMO_CLIENT_NAME | demo_client_name | str | demo-client | no |
| DEMO_DAILY_TOKEN_QUOTA | demo_daily_token_quota | int | <redacted> | yes |
| DEMO_MODE | demo_mode | bool | false | no |
| DEMO_MONTHLY_TOKEN_QUOTA | demo_monthly_token_quota | int | <redacted> | yes |
| DEMO_RATE_LIMIT_PER_MINUTE | demo_rate_limit_per_minute | int | 5 | no |

## `deployment`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DEPLOYMENT_AUTOSCALE_ENABLED | deployment_autoscale_enabled | bool | true | no |
| DEPLOYMENT_AUTOSCALE_WINDOW_SEC | deployment_autoscale_window_sec | int | 60 | no |
| DEPLOYMENT_MODE | deployment_mode | str | appliance | no |

## `disaster`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DISASTER_RECOVERY_BACKUP_DIR | disaster_recovery_backup_dir | str | /tmp/agent-backups | no |
| DISASTER_RECOVERY_ENABLED | disaster_recovery_enabled | bool | false | no |
| DISASTER_RECOVERY_SCHEDULE_HOURS | disaster_recovery_schedule_hours | int | 24 | no |

## `distributed`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DISTRIBUTED_RUNTIME_ENABLED | distributed_runtime_enabled | bool | false | no |

## `docs`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DOCS_BASE_URL | docs_base_url | str | - | no |

## `document`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| DOCUMENT_VISION_ENABLED | document_vision_enabled | bool | false | no |

## `email`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| EMAIL_PROVIDER | email_provider | str | mock | no |

## `embedding`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| EMBEDDING_DIMENSIONS | embedding_dimensions | int | 384 | no |

## `embeddings`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| EMBEDDINGS_BACKEND | embeddings_backend | str | local | no |
| EMBEDDINGS_ENABLED | embeddings_enabled | bool | true | no |

## `enterprise`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ENTERPRISE_SSO_AZURE_CLIENT_ID | enterprise_sso_azure_client_id | str | - | no |
| ENTERPRISE_SSO_AZURE_CLIENT_SECRET | enterprise_sso_azure_client_secret | str | <empty> | yes |
| ENTERPRISE_SSO_ENABLED | enterprise_sso_enabled | bool | false | no |
| ENTERPRISE_SSO_OKTA_CLIENT_ID | enterprise_sso_okta_client_id | str | - | no |
| ENTERPRISE_SSO_OKTA_CLIENT_SECRET | enterprise_sso_okta_client_secret | str | <empty> | yes |
| ENTERPRISE_SSO_OKTA_DOMAIN | enterprise_sso_okta_domain | str | - | no |
| ENTERPRISE_SSO_SAML_CERTIFICATE | enterprise_sso_saml_certificate | str | - | no |
| ENTERPRISE_SSO_SAML_ENTITY_ID | enterprise_sso_saml_entity_id | str | - | no |
| ENTERPRISE_SSO_SAML_SSO_URL | enterprise_sso_saml_sso_url | str | - | no |
| ENTERPRISE_SSO_TENANT_ID | enterprise_sso_tenant_id | str | - | no |

## `experiment`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| EXPERIMENT_TRACKING_ENABLED | experiment_tracking_enabled | bool | false | no |

## `fcm`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| FCM_API_KEY | fcm_api_key | str | <empty> | yes |

## `fine`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| FINE_TUNING_ENABLED | fine_tuning_enabled | bool | false | no |
| FINE_TUNING_GPU_PROVIDER_ENABLED | fine_tuning_gpu_provider | bool | false | no |

## `fireworks`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| FIREWORKS_API_KEY | fireworks_api_key | str | <empty> | yes |
| FIREWORKS_PROVIDER_ENABLED | fireworks_provider_enabled | bool | true | no |

## `frontend`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| FRONTEND_URL | frontend_url | str | http://localhost:5173 | no |

## `gemini`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| GEMINI_API_KEY | gemini_api_key | str | <empty> | yes |
| GEMINI_BASE_URL | gemini_base_url | str | - | no |
| GEMINI_PROVIDER_ENABLED | gemini_provider_enabled | bool | true | no |

## `global`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| GLOBAL_CLOUD_KILL_SWITCH | global_cloud_kill_switch | bool | false | no |

## `gpu`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| GPU_AUTOSCALING_ENABLED | gpu_autoscaling_enabled | bool | false | no |

## `groq`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| GROQ_API_KEY | groq_api_key | str | <empty> | yes |
| GROQ_PROVIDER_ENABLED | groq_provider_enabled | bool | true | no |

## `hardware`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| HARDWARE_TRUST_ENABLED | hardware_trust_enabled | bool | false | no |
| HARDWARE_TRUST_PROVIDER | hardware_trust_provider | str | mock | no |

## `image`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| IMAGE_GENERATION_ENABLED | image_generation_enabled | bool | false | no |

## `inference`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| INFERENCE_MAX_COMPLETION_TOKENS | inference_max_completion_tokens | int | <redacted> | yes |
| INFERENCE_MAX_CONTEXT_TOKENS | inference_max_context_tokens | int | <redacted> | yes |
| INFERENCE_MAX_HISTORY_MESSAGES | inference_max_history_messages | int | 8 | no |
| INFERENCE_MAX_SYSTEM_CHARS | inference_max_system_chars | int | 2500 | no |

## `jaeger`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| JAEGER_EXPORT_ENABLED | jaeger_export_enabled | bool | false | no |

## `jwt`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| JWT_SECRET | jwt_secret | str | required | yes |

## `kb`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| KB_URL_INGESTION_ENABLED | kb_url_ingestion_enabled | bool | false | no |

## `kubernetes`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| KUBERNETES_MODE | kubernetes_mode | bool | false | no |

## `lmstudio`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| LMSTUDIO_API_KEY | lmstudio_api_key | str | <redacted> | yes |
| LMSTUDIO_BASE_URL | lmstudio_base_url | str | http://192.168.101.1:1234/v1 | no |
| LMSTUDIO_CHAT_MODEL | lmstudio_chat_model | str | nvidia/nemotron-3-nano-4b | no |
| LMSTUDIO_ENABLED | lmstudio_enabled | bool | false | no |
| LMSTUDIO_TIMEOUT | lmstudio_timeout | int | 60 | no |

## `local`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| LOCAL_APPLIANCE_MODE | local_appliance_mode | bool | false | no |
| LOCAL_BILLING_MODE | local_billing_mode | str | manual | no |

## `localhost`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| LOCALHOST_MODE | localhost_mode | bool | false | no |

## `log`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| LOG_LEVEL | log_level | str | INFO | no |

## `managed`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MANAGED_CONTROL_PLANE_ENABLED | managed_control_plane_enabled | bool | false | no |

## `margin`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MARGIN_WARNING_PERCENT | margin_warning_percent | float | 20.0 | no |

## `marketplace`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MARKETPLACE_GOVERNANCE_ENABLED | marketplace_governance_enabled | bool | true | no |
| MARKETPLACE_REQUIRE_APPROVAL | marketplace_require_approval | bool | true | no |
| MARKETPLACE_REQUIRE_SECURITY_SCAN | marketplace_require_security_scan | bool | true | no |

## `max`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL | max_client_provider_cost_per_day_brl | float | 0.0 | no |
| MAX_CONCURRENT_GENERATIONS | max_concurrent_generations | int | 1 | no |
| MAX_CONTEXT_TOKENS | max_context_tokens | int | <redacted> | yes |
| MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL | max_global_provider_cost_per_day_brl | float | 0.0 | no |
| MAX_INPUT_TOKENS | max_input_tokens | int | <redacted> | yes |
| MAX_PROVIDER_COST_PER_DAY_BRL | max_provider_cost_per_day_brl | float | 0.0 | no |
| MAX_QUEUE_SIZE | max_queue_size | int | 8 | no |
| MAX_REQUEST_BODY_SIZE_BYTES | max_request_body_size_bytes | int | 5242880 | no |
| MAX_TEMPERATURE | max_temperature | float | 1.5 | no |
| MAX_TOOL_ARGUMENTS_BYTES | max_tool_arguments_bytes | int | 16384 | no |
| MAX_TOOL_SCHEMA_BYTES | max_tool_schema_bytes | int | 24576 | no |
| MAX_TOOL_SCHEMA_DEPTH | max_tool_schema_depth | int | 16 | no |
| MAX_TOOL_SCHEMA_PROPERTIES | max_tool_schema_properties | int | 256 | no |
| MAX_TOOLS_PER_REQUEST | max_tools_per_request | int | 16 | no |
| MAX_TOP_P | max_top_p | float | 1.0 | no |

## `mercadopago`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MERCADOPAGO_ACCESS_TOKEN | mercadopago_access_token | str | <empty> | yes |

## `milvus`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MILVUS_ENABLED | milvus_enabled | bool | false | no |
| MILVUS_TOKEN | milvus_token | str \| None | <empty> | yes |
| MILVUS_URL | milvus_url | str | http://localhost:19530 | no |

## `mistral`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MISTRAL_API_KEY | mistral_api_key | str | <empty> | yes |
| MISTRAL_PROVIDER_ENABLED | mistral_provider_enabled | bool | true | no |

## `mlflow`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MLFLOW_INTEGRATION_ENABLED | mlflow_integration_enabled | bool | false | no |

## `mlops`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MLOPS_DATASET_STORAGE_PATH | mlops_dataset_storage_path | str | - | no |
| MLOPS_ENABLED | mlops_enabled | bool | false | no |

## `mobile`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MOBILE_FOUNDATION_ENABLED | mobile_foundation_enabled | bool | false | no |

## `mock`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MOCK_BACKEND_ENABLED | mock_backend_enabled | bool | false | no |

## `model`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MODEL_AB_TESTING_ENABLED | model_ab_testing_enabled | bool | false | no |
| MODEL_CANARY_ENABLED | model_canary_enabled | bool | false | no |
| MODEL_EXPERIMENTS_ENABLED | model_experiments_enabled | bool | false | no |
| MODEL_FILE | model_file | str | gemma-4-E4B-it-Q4_K_M.gguf | no |
| MODEL_HOT_SWAP_ENABLED | model_hot_swap_enabled | bool | false | no |
| MODEL_ID | model_id | str | unsloth/gemma-4-E4B-it-GGUF | no |
| MODEL_LOAD_TIMEOUT_SECONDS | model_load_timeout_seconds | int | 120 | no |
| MODEL_ROLLBACK_ON_FAILURE | model_rollback_on_failure | bool | true | no |
| MODEL_RUNTIME_MOCK_ENABLED | model_runtime_mock_enabled | bool | false | no |
| MODEL_RUNTIME_PORT_END | model_runtime_port_end | int | 18120 | no |
| MODEL_RUNTIME_PORT_START | model_runtime_port_start | int | 18081 | no |

## `models`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MODELS_DIR | models_dir | str | /models | no |

## `multi`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MULTI_CLUSTER_ENABLED | multi_cluster_enabled | bool | false | no |

## `multimodal`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| MULTIMODAL_ENABLED | multimodal_enabled | bool | false | no |

## `nats`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| NATS_TRIGGER_ENABLED | nats_trigger_enabled | bool | false | no |
| NATS_URL | nats_url | str | nats://localhost:4222 | no |

## `negative`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| NEGATIVE_MARGIN_BLOCK_MODE | negative_margin_block_mode | str | report_only | no |

## `node`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| NODE_ID | node_id | str | - | no |
| NODE_ROLE | node_role | str | api | no |

## `oauth`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| OAUTH_ENABLED | oauth_enabled | bool | false | no |
| OAUTH_GITHUB_CLIENT_ID | oauth_github_client_id | str | - | no |
| OAUTH_GITHUB_CLIENT_SECRET | oauth_github_client_secret | str | <empty> | yes |
| OAUTH_GOOGLE_CLIENT_ID | oauth_google_client_id | str | - | no |
| OAUTH_GOOGLE_CLIENT_SECRET | oauth_google_client_secret | str | <empty> | yes |

## `observability`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| OBSERVABILITY_ENABLED | observability_enabled | bool | true | no |

## `ollama`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| OLLAMA_BASE_URL | ollama_base_url | str | http://data-plane-ollama:11434 | no |

## `openai`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| OPENAI_API_KEY | openai_api_key | str | <empty> | yes |
| OPENAI_BASE_URL | openai_base_url | str | - | no |
| OPENAI_CHAT_MODEL | openai_chat_model | str | - | no |
| OPENAI_EMBEDDINGS_MODEL | openai_embeddings_model | str | - | no |
| OPENAI_PROVIDER_ENABLED | openai_provider_enabled | bool | true | no |

## `openrouter`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| OPENROUTER_API_KEY | openrouter_api_key | str | <empty> | yes |
| OPENROUTER_BASE_URL | openrouter_base_url | str | - | no |
| OPENROUTER_PROVIDER_ENABLED | openrouter_provider_enabled | bool | true | no |

## `opsgenie`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| OPSGENIE_API_KEY | opsgenie_api_key | str | <empty> | yes |
| OPSGENIE_API_URL | opsgenie_api_url | str | https://api.opsgenie.com/v2/alerts | no |

## `otlp`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| OTLP_EXPORT_ENABLED | otlp_export_enabled | bool | false | no |

## `pagerduty`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PAGERDUTY_ROUTING_KEY | pagerduty_routing_key | str | <empty> | yes |

## `payment`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PAYMENT_PROCESSING_ENABLED | payment_processing_enabled | bool | false | no |
| PAYMENT_PROVIDER | payment_provider | str | mock | no |
| PAYMENT_REAL_ENABLED | payment_real_enabled | bool | false | no |
| PAYMENT_WEBHOOK_SECRET | payment_webhook_secret | str | <empty> | yes |

## `perplexity`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PERPLEXITY_API_KEY | perplexity_api_key | str | <empty> | yes |
| PERPLEXITY_PROVIDER_ENABLED | perplexity_provider_enabled | bool | true | no |

## `pinecone`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PINECONE_API_KEY | pinecone_api_key | str | <empty> | yes |
| PINECONE_ENVIRONMENT | pinecone_environment | str | us-east-1-aws | no |
| PINECONE_INDEX_NAME | pinecone_index_name | str | agent-memory | no |

## `pix`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PIX_PAYMENT_ENABLED | pix_payment_enabled | bool | false | no |

## `pki`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PKI_CA_ROTATION_DAYS | pki_ca_rotation_days | int | 365 | no |
| PKI_CERT_ROTATION_DAYS | pki_cert_rotation_days | int | 90 | no |
| PKI_ENABLED | pki_enabled | bool | false | no |
| PKI_STORAGE_PATH | pki_storage_path | str | ./data/pki | no |

## `platform`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PLATFORM_PROFILE | platform_profile | str | appliance | no |

## `plugin`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PLUGIN_MARKETPLACE_ENABLED | plugin_marketplace_enabled | bool | false | no |
| PLUGIN_RUNTIME_ENABLED | plugin_runtime_enabled | bool | false | no |
| PLUGIN_SIGNATURE_REQUIRED | plugin_signature_required | bool | false | no |

## `project`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PROJECT_NAME | project_name | str | local-llm-inference-stack | no |
| PROJECT_VERSION | project_version | str | required | no |

## `prompt`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PROMPT_TEMPLATE_PLAYGROUND_ENABLED | prompt_template_playground_enabled | bool | false | no |
| PROMPT_TEMPLATES_ENABLED | prompt_templates_enabled | bool | false | no |

## `provider`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PROVIDER_FAIL_CLOSED | provider_fail_closed | bool | true | no |
| PROVIDER_MAX_RETRIES | provider_max_retries | int | 2 | no |

## `providers`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PROVIDERS_ENABLED | providers_enabled | str | local,lmstudio | no |

## `public`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PUBLIC_ANALYTICS_PROVIDER | public_analytics_provider | str | none | no |
| PUBLIC_API_ENABLED | public_api_enabled | bool | false | no |
| PUBLIC_BASE_URL | public_base_url | str | - | no |
| PUBLIC_BRAND_NAME | public_brand_name | str | LLM Inference Stack Cloud | no |
| PUBLIC_EXPOSURE | public_exposure | bool | false | no |
| PUBLIC_PLAUSIBLE_DOMAIN | public_plausible_domain | str | - | no |
| PUBLIC_PLAUSIBLE_SRC | public_plausible_src | str | https://plausible.io/js/script.js | no |
| PUBLIC_SIGNUP_ENABLED | public_signup_enabled | bool | true | no |
| PUBLIC_SUPPORT_EMAIL | public_support_email | str | sales@example.com | no |

## `pulsar`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PULSAR_TRIGGER_ENABLED | pulsar_trigger_enabled | bool | false | no |
| PULSAR_URL | pulsar_url | str | pulsar://localhost:6650 | no |

## `push`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| PUSH_NOTIFICATIONS_ENABLED | push_notifications_enabled | bool | false | no |
| PUSH_PROVIDER | push_provider | str | mock | no |

## `qdrant`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| QDRANT_API_KEY | qdrant_api_key | str \| None | <empty> | yes |
| QDRANT_ENABLED | qdrant_enabled | bool | false | no |
| QDRANT_URL | qdrant_url | str | http://localhost:6333 | no |

## `queue`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| QUEUE_ADMIN_MAX_ACTIVE | queue_admin_max_active | int | 10 | no |
| QUEUE_ADMIN_MAX_WAITING | queue_admin_max_waiting | int | 20 | no |
| QUEUE_ADMIN_TIMEOUT | queue_admin_timeout | int | 60 | no |
| QUEUE_BASIC_MAX_ACTIVE | queue_basic_max_active | int | 2 | no |
| QUEUE_BASIC_MAX_WAITING | queue_basic_max_waiting | int | 10 | no |
| QUEUE_BASIC_TIMEOUT | queue_basic_timeout | int | 20 | no |
| QUEUE_FREE_MAX_ACTIVE | queue_free_max_active | int | 1 | no |
| QUEUE_FREE_MAX_WAITING | queue_free_max_waiting | int | 5 | no |
| QUEUE_FREE_TIMEOUT | queue_free_timeout | int | 15 | no |
| QUEUE_PREMIUM_MAX_ACTIVE | queue_premium_max_active | int | 5 | no |
| QUEUE_PREMIUM_MAX_WAITING | queue_premium_max_waiting | int | 15 | no |
| QUEUE_PREMIUM_TIMEOUT | queue_premium_timeout | int | 30 | no |
| QUEUE_TIMEOUT_SECONDS | queue_timeout_seconds | int | 30 | no |

## `rag`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| RAG_CHUNK_OVERLAP | rag_chunk_overlap | int | 150 | no |
| RAG_CHUNK_SIZE | rag_chunk_size | int | 1000 | no |
| RAG_EMBEDDING_MODEL | rag_embedding_model | str | sentence-transformers/all-MiniLM-L6-v2 | no |
| RAG_EMBEDDING_PROVIDER | rag_embedding_provider | str | local | no |
| RAG_ENABLED | rag_enabled | bool | true | no |
| RAG_MAX_FILE_MB | rag_max_file_mb | int | 25 | no |
| RAG_STORAGE_DIR | rag_storage_dir | str | ./data/rag_uploads | no |
| RAG_TOP_K_DEFAULT | rag_top_k_default | int | 5 | no |

## `rate`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| RATE_LIMIT_GLOBAL_PER_MINUTE | rate_limit_global_per_minute | int | 1000 | no |
| RATE_LIMIT_TENANT_PER_MINUTE | rate_limit_tenant_per_minute | int | 500 | no |

## `rbac`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| RBAC_ADMIN_ENABLED | rbac_admin_enabled | bool | true | no |

## `real`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| REAL_PROVIDER_LOG_PROMPTS | real_provider_log_prompts | bool | false | no |
| REAL_PROVIDER_MAX_COST_BRL | real_provider_max_cost_brl | float | 2.0 | no |
| REAL_PROVIDER_STORE_RESPONSES | real_provider_store_responses | bool | false | no |
| REAL_PROVIDER_VALIDATION_ENABLED | real_provider_validation_enabled | bool | false | no |

## `realtime`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| REALTIME_AUDIO_ENABLED | realtime_audio_enabled | bool | false | no |
| REALTIME_VOICE_ENABLED | realtime_voice_enabled | bool | false | no |

## `redis`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| REDIS_URL | redis_url | str | required | no |

## `replicate`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| REPLICATE_API_KEY | replicate_api_key | str | <empty> | yes |
| REPLICATE_PROVIDER_ENABLED | replicate_provider_enabled | bool | true | no |

## `request`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| REQUEST_TIMEOUT_SECONDS | request_timeout_seconds | int | 120 | no |

## `response`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| RESPONSE_CACHE_ENABLED | response_cache_enabled | bool | true | no |
| RESPONSE_CACHE_TTL_SECONDS | response_cache_ttl_seconds | int | 3600 | no |

## `retry`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| RETRY_ATTEMPTS | retry_attempts | int | 2 | no |
| RETRY_BACKOFF_SECONDS | retry_backoff_seconds | float | 1.0 | no |

## `routing`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ROUTING_TEST_FORCE_LOCAL_FAILURE | routing_test_force_local_failure | bool | false | no |

## `secrets`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| SECRETS_MANAGER_PROVIDER | secrets_manager_provider | str | <redacted> | yes |

## `semantic`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| SEMANTIC_CACHE_ENABLED | semantic_cache_enabled | bool | false | no |

## `sendgrid`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| SENDGRID_API_KEY | sendgrid_api_key | str | <empty> | yes |

## `smtp`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| SMTP_HOST | smtp_host | str | localhost | no |
| SMTP_PASSWORD | smtp_password | str | <empty> | yes |
| SMTP_PORT | smtp_port | int | 1025 | no |
| SMTP_USERNAME | smtp_username | str | - | no |

## `speech`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| SPEECH_TO_TEXT_ENABLED | speech_to_text_enabled | bool | false | no |

## `start`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| START_TIME | start_time | float | required | no |

## `stripe`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| STRIPE_API_KEY | stripe_api_key | str | <empty> | yes |
| STRIPE_PAYMENT_ENABLED | stripe_payment_enabled | bool | false | no |
| STRIPE_SECRET_KEY | stripe_secret_key | str | <empty> | yes |
| STRIPE_WEBHOOK_SECRET | stripe_webhook_secret | str | <empty> | yes |

## `test`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| TEST_TOOLS_ENABLED | test_tools_enabled | bool | false | no |

## `together`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| TOGETHER_API_KEY | together_api_key | str | <empty> | yes |
| TOGETHER_PROVIDER_ENABLED | together_provider_enabled | bool | true | no |

## `token`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| TOKEN_COUNTING_FALLBACK_ALLOWED | token_counting_fallback_allowed | bool | <redacted> | yes |
| TOKEN_COUNTING_REAL_ENABLED | token_counting_real_enabled | bool | <redacted> | yes |

## `tokenizer`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| TOKENIZER_CACHE_ENABLED | tokenizer_cache_enabled | bool | <redacted> | yes |
| TOKENIZER_MODE | tokenizer_mode | str | <redacted> | yes |
| TOKENIZER_MODEL_PATH | tokenizer_model_path | str \| None | <empty> | yes |
| TOKENIZER_STRICT | tokenizer_strict | bool | false | yes |

## `tool`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| TOOL_ARGUMENT_PREVIEW_CHARS | tool_argument_preview_chars | int | 160 | no |

## `tts`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| TTS_ENABLED | tts_enabled | bool | true | no |

## `vault`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| VAULT_ADDR | vault_addr | str | http://localhost:8200 | no |
| VAULT_KV_MOUNT | vault_kv_mount | str | secret | no |
| VAULT_TOKEN | vault_token | str | <empty> | yes |

## `vector`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| VECTOR_DB_PROVIDER | vector_db_provider | str | pgvector | no |

## `vision`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| VISION_INPUT_ENABLED | vision_input_enabled | bool | false | no |

## `vllm`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| VLLM_API_KEY | vllm_api_key | str | <empty> | yes |
| VLLM_BACKEND_ENABLED | vllm_backend_enabled | bool | false | no |
| VLLM_BASE_URL | vllm_base_url | str | http://localhost:8000/v1 | no |
| VLLM_DEFAULT_MODEL | vllm_default_model | str | facebook/opt-125m | no |
| VLLM_MAX_CONCURRENT_REQUESTS | vllm_max_concurrent_requests | int | 16 | no |
| VLLM_OPENAI_COMPAT_ENABLED | vllm_openai_compat_enabled | bool | false | no |
| VLLM_TIMEOUT_SECONDS | vllm_timeout_seconds | int | 120 | no |

## `voice`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| VOICE_AGENT_ENABLED | voice_agent_enabled | bool | false | no |
| VOICE_STT_STREAMING_ENABLED | voice_stt_streaming_enabled | bool | false | no |
| VOICE_TTS_STREAMING_ENABLED | voice_tts_streaming_enabled | bool | false | no |

## `wandb`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| WANDB_INTEGRATION_ENABLED | wandb_integration_enabled | bool | false | no |

## `weaviate`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| WEAVIATE_API_KEY | weaviate_api_key | str \| None | <empty> | yes |
| WEAVIATE_ENABLED | weaviate_enabled | bool | false | no |
| WEAVIATE_URL | weaviate_url | str | http://localhost:8080 | no |

## `web`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| WEB_IDE_ENABLED | web_ide_enabled | bool | false | no |
| WEB_IDE_WORKSPACES_DIR | web_ide_workspaces_dir | str | ./data/ide_workspaces | no |

## `webrtc`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| WEBRTC_AUDIO_ENABLED | webrtc_audio_enabled | bool | false | no |
| WEBRTC_VOICE_ENABLED | webrtc_voice_enabled | bool | false | no |

## `xai`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| XAI_API_KEY | xai_api_key | str | <empty> | yes |
| XAI_PROVIDER_ENABLED | xai_provider_enabled | bool | true | no |

## `zipkin`

| Env | Field | Type | Default | Secret |
| --- | --- | --- | --- | --- |
| ZIPKIN_EXPORT_ENABLED | zipkin_export_enabled | bool | false | no |
