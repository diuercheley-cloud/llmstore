<!-- AUTO-GENERATED: do not edit manually -->


# Configuration Reference

This document lists all environment variables used to configure the platform.

## `a2a`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `A2A_API_KEY` | str | `-` | Yes |
| `A2A_BASE_URL` | str | `-` | No |
| `A2A_ENABLED` | bool | `false` | No |

## `abuse`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ABUSE_AUTO_SUSPEND_ENABLED` | bool | `false` | No |
| `ABUSE_DETECTION_ENABLED` | bool | `true` | No |
| `ABUSE_DRY_RUN` | bool | `true` | No |

## `admin`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ADMIN_BASE_URL` | str | `-` | No |
| `ADMIN_READ_TOKEN` | str | None | `-` | Yes |
| `ADMIN_SUPER_TOKEN` | str | None | `-` | Yes |
| `ADMIN_TESTS_RATE_LIMIT_ENABLED` | bool | `true` | No |
| `ADMIN_TOKEN` | str | <redacted> | Yes |
| `ADMIN_WRITE_TOKEN` | str | None | `-` | Yes |

## `agent`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `AGENT_A2A_ENABLED` | bool | `false` | No |
| `AGENT_A2A_EXTERNAL_ENABLED` | bool | `false` | No |
| `AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION` | bool | `false` | No |
| `AGENT_ANOMALY_DETECTION_ENABLED` | bool | `false` | No |
| `AGENT_APPROVAL_PORTAL_ENABLED` | bool | `false` | No |
| `AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK` | bool | `true` | No |
| `AGENT_APPROVAL_TIMEOUT_SECONDS` | int | `3600` | No |
| `AGENT_ASSISTANTS_API_ENABLED` | bool | `false` | No |
| `AGENT_ASYNC_EXECUTION_ENABLED` | bool | `false` | No |
| `AGENT_AUTO_APPLY_LEARNINGS` | bool | `true` | No |
| `AGENT_AUTO_OPTIMIZATION_ENABLED` | bool | `false` | No |
| `AGENT_AUTO_RETRY_ENABLED` | bool | `true` | No |
| `AGENT_BATCH_API_ENABLED` | bool | `false` | No |
| `AGENT_BREAKPOINTS_ENABLED` | bool | `false` | No |
| `AGENT_BROWSER_ALLOWLIST` | str | `example.com,wikipedia.org` | No |
| `AGENT_BROWSER_EXTERNAL_NETWORK_ENABLED` | bool | `false` | No |
| `AGENT_BROWSER_SCREENSHOT_ENABLED` | bool | `false` | No |
| `AGENT_BROWSER_TOOL_ENABLED` | bool | `false` | No |
| `AGENT_BUNDLE_INSTALL_ENABLED` | bool | `true` | No |
| `AGENT_BUNDLE_SIGNATURE_REQUIRED` | bool | `false` | No |
| `AGENT_CANARY_AGENTS_ENABLED` | bool | `true` | No |
| `AGENT_CANARY_AUTO_PROMOTE` | bool | `false` | No |
| `AGENT_CLUSTER_FEDERATION_ENABLED` | bool | `false` | No |
| `AGENT_CODE_INTERPRETER_ENABLED` | bool | `false` | No |
| `AGENT_CODE_SANDBOX_DOCKER_ENABLED` | bool | `false` | No |
| `AGENT_CODE_SANDBOX_FIRECRACKER_ENABLED` | bool | `false` | No |
| `AGENT_CODE_SANDBOX_GVISOR_ENABLED` | bool | `false` | No |
| `AGENT_CODE_SANDBOX_MICROVM_REQUIRED` | bool | `false` | No |
| `AGENT_CODE_SANDBOX_NETWORK_ENABLED` | bool | `false` | No |
| `AGENT_CODE_SANDBOX_PROVIDER` | str | `gvisor` | No |
| `AGENT_CODE_SANDBOX_WASM_ENABLED` | bool | `false` | No |
| `AGENT_CODE_SANDBOX_WRITE_ENABLED` | bool | `false` | No |
| `AGENT_COGNITIVE_LOOPBACK_ENABLED` | bool | `true` | No |
| `AGENT_COGNITIVE_MEMORY_ENABLED` | bool | `false` | No |
| `AGENT_CONNECTOR_CATALOG_ENABLED` | bool | `false` | No |
| `AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED` | bool | `false` | No |
| `AGENT_CONNECTOR_MODE` | str | `mock` | No |
| `AGENT_CONNECTOR_REAL_HTTP_ENABLED` | bool | `false` | No |
| `AGENT_CONNECTOR_WRITE_ENABLED` | bool | `false` | No |
| `AGENT_CONSTRAINT_REASONING_ENABLED` | bool | `false` | No |
| `AGENT_CONTEXT_COMPRESSION_ENABLED` | bool | `false` | No |
| `AGENT_CRON_TRIGGERS_ENABLED` | bool | `false` | No |
| `AGENT_DB_READ_TOOL_ENABLED` | bool | `false` | No |
| `AGENT_DEBUG_STATE_EDITING_ENABLED` | bool | `false` | No |
| `AGENT_DEBUGGER_ENABLED` | bool | `false` | No |
| `AGENT_DESTRUCTIVE_TOOLS_ENABLED` | bool | `false` | No |
| `AGENT_DIGITAL_TWINS_ENABLED` | bool | `false` | No |
| `AGENT_DISTRIBUTED_RATE_LIMITING_ENABLED` | bool | `false` | No |
| `AGENT_DISTRIBUTED_RUNTIME_ENABLED` | bool | `false` | No |
| `AGENT_DYNAMIC_TOOL_EXECUTION_ENABLED` | bool | `false` | No |
| `AGENT_EMAIL_NOTIFICATIONS_ENABLED` | bool | `false` | No |
| `AGENT_EMBEDDED_WORKER_ENABLED` | bool | `false` | No |
| `AGENT_ENTERPRISE_OBSERVABILITY_ENABLED` | bool | `false` | No |
| `AGENT_EVAL_ALLOW_MOCK_FOR_PROMOTION` | bool | `false` | No |
| `AGENT_EVAL_GATE_STRICT` | bool | `true` | No |
| `AGENT_EVAL_PROVIDER` | str | `mock` | No |
| `AGENT_EVAL_REAL_PROVIDER_ENABLED` | bool | `false` | No |
| `AGENT_EVAL_REGRESSION_GATE_ENABLED` | bool | `true` | No |
| `AGENT_EVALS_ENABLED` | bool | `false` | No |
| `AGENT_EVENT_DRIVEN_ENABLED` | bool | `false` | No |
| `AGENT_EXECUTION_ENABLED` | bool | `false` | No |
| `AGENT_EXECUTION_PLANE_ENABLED` | bool | `false` | No |
| `AGENT_EXECUTOR_ALLOW_SIMULATION` | bool | `false` | No |
| `AGENT_EXECUTOR_DRY_RUN_MODE` | bool | `false` | No |
| `AGENT_EXECUTOR_MOCK_MODE` | bool | `false` | No |
| `AGENT_FEDERATED_MEMORY_ENABLED` | bool | `false` | No |
| `AGENT_FEDERATED_MEMORY_RAW_DATA_SYNC` | bool | `false` | No |
| `AGENT_FEDERATED_MEMORY_SYNC_ENABLED` | bool | `false` | No |
| `AGENT_FEEDBACK_LEARNING_ENABLED` | bool | `false` | No |
| `AGENT_FEWSHOT_AUTO_CURATOR_ENABLED` | bool | `false` | No |
| `AGENT_FILE_DELETE_ENABLED` | bool | `false` | No |
| `AGENT_FILE_TOOLS_ENABLED` | bool | `false` | No |
| `AGENT_FILE_WRITE_ENABLED` | bool | `false` | No |
| `AGENT_FLOW_COMPILER_ENABLED` | bool | `false` | No |
| `AGENT_GITHUB_CONNECTOR_ENABLED` | bool | `false` | No |
| `AGENT_GLPK_SOLVER_ENABLED` | bool | `false` | No |
| `AGENT_GRAPH_EXTERNAL_DB_ENABLED` | bool | `false` | No |
| `AGENT_GRAPH_RAG_ENABLED` | bool | `false` | No |
| `AGENT_GRAPH_WRITE_ENABLED` | bool | `false` | No |
| `AGENT_HANDOFFS_ENABLED` | bool | `false` | No |
| `AGENT_HARD_COST_CAP_ENABLED` | bool | `true` | No |
| `AGENT_HTTP_TOOL_ENABLED` | bool | `false` | No |
| `AGENT_HUMAN_APPROVAL_ENABLED` | bool | `true` | No |
| `AGENT_IAM_ENABLED` | bool | `false` | No |
| `AGENT_INCIDENT_RESPONSE_ENABLED` | bool | `true` | No |
| `AGENT_INTERNAL_BUNDLE_SIGNATURE_REQUIRED_IN_PRODUCTION` | bool | `true` | No |
| `AGENT_IOT_CONNECTORS_ENABLED` | bool | `false` | No |
| `AGENT_KG_ADJACENCY_CACHE_ENABLED` | bool | `false` | No |
| `AGENT_KG_EXTERNAL_PROVIDER_ENABLED` | bool | `false` | No |
| `AGENT_KG_MOCK_MODE` | bool | `false` | No |
| `AGENT_KG_PATHFINDING_MAX_DEPTH` | int | `6` | No |
| `AGENT_KG_PATHFINDING_MAX_NODES` | int | `500` | No |
| `AGENT_KG_PATHFINDING_TIMEOUT_MS` | int | `5000` | No |
| `AGENT_KG_PGROUTING_ENABLED` | bool | `false` | No |
| `AGENT_KG_PGVECTOR_ENABLED` | bool | `false` | No |
| `AGENT_KG_POSTGRES_GRAPH_ENABLED` | bool | `true` | No |
| `AGENT_KG_PROVIDER` | str | `internal_sql` | No |
| `AGENT_KG_WRITE_ENABLED` | bool | `false` | No |
| `AGENT_KNOWLEDGE_GRAPH_ENABLED` | bool | `false` | No |
| `AGENT_LIVE_STEPPING_ENABLED` | bool | `false` | No |
| `AGENT_LLM_PROVIDER` | str | `mock` | No |
| `AGENT_LLM_STREAMING_ENABLED` | bool | `false` | No |
| `AGENT_LONG_TERM_MEMORY_ENABLED` | bool | `false` | No |
| `AGENT_MARKETPLACE_ENABLED` | bool | `true` | No |
| `AGENT_MCP_CALL_MAX_RETRIES` | int | `2` | No |
| `AGENT_MCP_CALL_TIMEOUT_MS` | int | `10000` | No |
| `AGENT_MCP_CATALOG_ENABLED` | bool | `false` | No |
| `AGENT_MCP_CLIENT_ENABLED` | bool | `false` | No |
| `AGENT_MCP_ENABLED` | bool | `false` | No |
| `AGENT_MCP_EXTERNAL_NETWORK_ENABLED` | bool | `false` | No |
| `AGENT_MCP_GLOBAL_CREDENTIALS_ALLOWED` | bool | `false` | No |
| `AGENT_MCP_MOCK_MODE` | bool | `false` | No |
| `AGENT_MCP_OAUTH_TOKEN_EXCHANGE_ENABLED` | bool | <redacted> | Yes |
| `AGENT_MCP_REAL_DISCOVERY_ENABLED` | bool | `false` | No |
| `AGENT_MCP_SAMPLING_ENABLED` | bool | `false` | No |
| `AGENT_MCP_SERVER_ENABLED` | bool | `false` | No |
| `AGENT_MCP_USER_DELEGATION_REQUIRED` | bool | `false` | No |
| `AGENT_MCTS_REASONING_ENABLED` | bool | `false` | No |
| `AGENT_MCTS_SANDBOX_SIMULATION_ENABLED` | bool | `false` | No |
| `AGENT_MEMORY_CONSENT_REQUIRED` | bool | `true` | No |
| `AGENT_MEMORY_CONTEXT_INJECTION_ENABLED` | bool | `false` | No |
| `AGENT_MEMORY_EMBEDDINGS_PROVIDER` | str | `mock` | No |
| `AGENT_MEMORY_ENABLED` | bool | `false` | No |
| `AGENT_MEMORY_ENCRYPTION_ENABLED` | bool | `false` | No |
| `AGENT_MEMORY_EXPORT_ENABLED` | bool | `false` | No |
| `AGENT_MEMORY_SEARCH_ENABLED` | bool | `false` | No |
| `AGENT_MEMORY_SEMANTIC_SEARCH_ENABLED` | bool | `false` | No |
| `AGENT_MEMORY_VECTOR_PROVIDER` | str | `mock` | No |
| `AGENT_MEMORY_WRITE_ENABLED` | bool | `false` | No |
| `AGENT_META_REVIEWER_BLOCKING_MODE` | bool | `false` | No |
| `AGENT_META_REVIEWER_ENABLED` | bool | `false` | No |
| `AGENT_META_REVIEWER_PARALLEL_ENABLED` | bool | `false` | No |
| `AGENT_MULTI_AGENT_ARBITRATION_ENABLED` | bool | `false` | No |
| `AGENT_MULTI_AGENT_CRITIC_REVIEW_ENABLED` | bool | `false` | No |
| `AGENT_MULTI_AGENT_ENABLED` | bool | `false` | No |
| `AGENT_MULTI_AGENT_MOCK_ARBITRATION` | bool | `false` | No |
| `AGENT_OBSERVABILITY_ENABLED` | bool | `true` | No |
| `AGENT_OPTIMIZATION_APPLY_ENABLED` | bool | `false` | No |
| `AGENT_OPTIMIZER_APPLY_WINNER_ENABLED` | bool | `false` | No |
| `AGENT_OPTIMIZER_ENABLED` | bool | `false` | No |
| `AGENT_OPTIMIZER_PARALLEL_EVALS_ENABLED` | bool | `false` | No |
| `AGENT_OPTIMIZER_TOURNAMENTS_ENABLED` | bool | `false` | No |
| `AGENT_OTEL_TRACING_ENABLED` | bool | `true` | No |
| `AGENT_PHYSICAL_ACTUATION_ENABLED` | bool | `false` | No |
| `AGENT_PLAN_AND_SOLVE_ENABLED` | bool | `false` | No |
| `AGENT_PLAN_EXECUTION_ENABLED` | bool | `false` | No |
| `AGENT_PLANNER_REAL_EXECUTION_ENABLED` | bool | `false` | No |
| `AGENT_PLANNING_ENABLED` | bool | `false` | No |
| `AGENT_PLUGIN_SUPPLY_CHAIN_ENABLED` | bool | `false` | No |
| `AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE` | bool | `true` | No |
| `AGENT_PROMOTION_REQUIRES_EVALS` | bool | `false` | No |
| `AGENT_PUBSUB_TRIGGERS_ENABLED` | bool | `false` | No |
| `AGENT_PUSH_NOTIFICATIONS_ENABLED` | bool | `false` | No |
| `AGENT_QUEUE_BACKPRESSURE_ENABLED` | bool | `false` | No |
| `AGENT_REACT_LOOP_ENABLED` | bool | `false` | No |
| `AGENT_REAL_LLM_ENABLED` | bool | `false` | No |
| `AGENT_REAL_PROVIDER_VALIDATION_ENABLED` | bool | `false` | No |
| `AGENT_REASONING_LOOP_ENABLED` | bool | `false` | No |
| `AGENT_REMOTE_MARKETPLACE_ENABLED` | bool | `false` | No |
| `AGENT_REPLAY_ENABLED` | bool | `false` | No |
| `AGENT_REPLAY_FROM_STEP_ENABLED` | bool | `false` | No |
| `AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION` | bool | `true` | No |
| `AGENT_RUNTIME_ENABLED` | bool | `false` | No |
| `AGENT_SAAS_CONNECTORS_ENABLED` | bool | `false` | No |
| `AGENT_SAB_ENABLED` | bool | `true` | No |
| `AGENT_SAB_EXPORT_ENABLED` | bool | `false` | No |
| `AGENT_SAB_IMPORT_ENABLED` | bool | `false` | No |
| `AGENT_SANDBOX_ALLOW_SIMULATED_PROVIDER` | bool | `false` | No |
| `AGENT_SANDBOX_PRODUCTION_REQUIRES_ATTESTATION` | bool | `false` | No |
| `AGENT_SEMANTIC_MEMORY_ENABLED` | bool | `false` | No |
| `AGENT_SHADOW_MODE_ENABLED` | bool | `false` | No |
| `AGENT_SHELL_TOOL_ENABLED` | bool | `false` | No |
| `AGENT_SLO_ENFORCEMENT_ENABLED` | bool | `false` | No |
| `AGENT_STATEFUL_WORKFLOWS_ENABLED` | bool | `false` | No |
| `AGENT_STRICT_BUDGETS` | bool | `false` | No |
| `AGENT_STUDIO_ENABLED` | bool | `true` | No |
| `AGENT_STUDIO_GA_ENABLED` | bool | `true` | No |
| `AGENT_TASK_DRY_RUN_MODE` | bool | `false` | No |
| `AGENT_TASK_MOCK_MODE` | bool | `false` | No |
| `AGENT_TASK_SIMULATION_MODE` | bool | `false` | No |
| `AGENT_TELEMETRY_BACKPRESSURE_ENABLED` | bool | `true` | No |
| `AGENT_TELEMETRY_DROP_DEBUG_SPANS_ENABLED` | bool | `true` | No |
| `AGENT_TELEMETRY_STRICT_EXPORT` | bool | `false` | No |
| `AGENT_TIME_TRAVEL_DEBUGGER_ENABLED` | bool | `false` | No |
| `AGENT_TOOL_ADAPTERS_ENABLED` | bool | `false` | No |
| `AGENT_TOOL_CREDENTIAL_DELEGATION_ENABLED` | bool | `false` | No |
| `AGENT_TOOL_EXECUTION_ENABLED` | bool | `false` | No |
| `AGENT_TOOL_REGISTRY_ENABLED` | bool | `false` | No |
| `AGENT_TOOL_ROLLBACK_ENABLED` | bool | `true` | No |
| `AGENT_TOOL_SANDBOX_ENABLED` | bool | `true` | No |
| `AGENT_TRACE_EXPORT_ENABLED` | bool | `false` | No |
| `AGENT_UNCERTAINTY_AUTO_RESEARCH_ENABLED` | bool | `false` | No |
| `AGENT_UNCERTAINTY_DETECTION_ENABLED` | bool | `true` | No |
| `AGENT_UNCERTAINTY_HITL_ENABLED` | bool | `true` | No |
| `AGENT_VISUAL_FLOW_EDITOR_ENABLED` | bool | `false` | No |
| `AGENT_WALLET_EXTERNAL_SPEND_ENABLED` | bool | `false` | No |
| `AGENT_WALLET_STRIPE_ENABLED` | bool | `false` | No |
| `AGENT_WALLET_WEB3_ENABLED` | bool | `false` | No |
| `AGENT_WALLETS_ENABLED` | bool | `true` | No |
| `AGENT_WEB_SEARCH_ALLOWLIST_ENABLED` | bool | `true` | No |
| `AGENT_WEB_SEARCH_ENABLED` | bool | `false` | No |
| `AGENT_WEB_SEARCH_EXTERNAL_NETWORK_ENABLED` | bool | `false` | No |
| `AGENT_WEBSOCKET_STREAMING_ENABLED` | bool | `false` | No |
| `AGENT_WORKER_AUTOSCALING_ENABLED` | bool | `false` | No |
| `AGENT_WORKER_ENABLED` | bool | `false` | No |
| `AGENT_Z3_SOLVER_ENABLED` | bool | `false` | No |

## `agentic`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `AGENTIC_ROUTER_V2_ENABLED` | bool | `false` | No |

## `ai21`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `AI21_API_KEY` | str | `-` | Yes |
| `AI21_PROVIDER_ENABLED` | bool | `true` | No |

## `allow`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ALLOW_UNSIGNED_INTERNAL_BUNDLES` | bool | `false` | No |

## `anthropic`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | str | `-` | Yes |
| `ANTHROPIC_BASE_URL` | str | `-` | No |
| `ANTHROPIC_MODEL` | str | `-` | No |

## `api`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `API_BASE_URL` | str | `-` | No |

## `apns`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `APNS_KEY_ID` | str | `-` | Yes |

## `app`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `APP_ENV` | str | `local` | No |
| `APP_PUBLIC_URL` | str | `http://localhost:18080` | No |

## `asaas`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ASAAS_API_KEY` | str | `-` | Yes |

## `async`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ASYNC_JOB_QUEUE_NAME` | str | `generation_jobs:queue` | No |
| `ASYNC_WORKER_BLOCK_SECONDS` | int | `5` | No |

## `attestation`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ATTESTATION_MODE` | str | `advisory` | No |

## `aws`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `AWS_ACCESS_KEY_ID` | str | `-` | Yes |
| `AWS_REGION` | str | `us-east-1` | No |
| `AWS_SECRET_ACCESS_KEY` | str | `-` | Yes |

## `azure`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `AZURE_OPENAI_API_KEY` | str | `-` | Yes |
| `AZURE_OPENAI_API_VERSION` | str | `2024-10-21` | No |
| `AZURE_OPENAI_DEPLOYMENT` | str | `-` | No |
| `AZURE_OPENAI_ENDPOINT` | str | `-` | No |
| `AZURE_OPENAI_PROVIDER_ENABLED` | bool | `true` | No |

## `backup`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `BACKUP_RESTORE_ENABLED` | bool | `false` | No |

## `bedrock`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `BEDROCK_PROVIDER_ENABLED` | bool | `true` | No |

## `billing`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `BILLING_DUE_DAYS` | int | `7` | No |
| `BILLING_INVOICE_DAY` | int | `1` | No |
| `BILLING_SUSPEND_AFTER_DAYS` | int | `15` | No |

## `card`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CARD_PAYMENT_ENABLED` | bool | `false` | No |

## `circuit`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | int | `3` | No |
| `CIRCUIT_BREAKER_RECOVERY_SECONDS` | int | `20` | No |

## `client`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CLIENT_PORTAL_BASE_URL` | str | `-` | No |

## `cloud`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CLOUD_PROVIDERS_ENABLED` | bool | `false` | No |

## `cluster`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CLUSTER_ID` | str | `local` | No |
| `CLUSTER_REGION` | str | `default` | No |

## `cohere`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `COHERE_API_KEY` | str | `-` | Yes |
| `COHERE_PROVIDER_ENABLED` | bool | `true` | No |

## `collab`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `COLLAB_CHAT_ENABLED` | bool | `false` | No |
| `COLLAB_CHAT_WEBSOCKET_ENABLED` | bool | `false` | No |

## `commercial`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `COMMERCIAL_AGENT_DEFAULT_DELEGATION_LIMIT` | int | `3` | No |
| `COMMERCIAL_AGENT_GOVERNANCE_ENABLED` | bool | `false` | No |
| `COMMERCIAL_AGENT_GOVERNANCE_MODE` | str | `audit_only` | No |
| `COMMERCIAL_AGENT_MEMORY_ISOLATION_LEVEL` | str | `strict` | No |
| `COMMERCIAL_AGENT_TOOL_APPROVAL_REQUIRED` | bool | `true` | No |
| `COMMERCIAL_AIRGAP_REQUIRE_ENCRYPTION` | bool | `true` | No |
| `COMMERCIAL_AIRGAP_REQUIRE_SIGNATURE` | bool | `true` | No |
| `COMMERCIAL_AIRGAP_SYNC_ENABLED` | bool | `true` | No |
| `COMMERCIAL_AIRGAP_SYNC_MODE` | str | `dry_run` | No |
| `COMMERCIAL_ANALYTICS_AGGREGATION_BUCKET_MINUTES` | int | `5` | No |
| `COMMERCIAL_ANALYTICS_DEDUPE_ENABLED` | bool | `true` | No |
| `COMMERCIAL_ANALYTICS_RETENTION_DAYS` | int | `90` | No |
| `COMMERCIAL_ANOMALY_LOOKBACK_HOURS` | int | `24` | No |
| `COMMERCIAL_APPLIANCE_DEPLOYMENT_TIER` | str | `regulated` | No |
| `COMMERCIAL_APPLIANCE_ID` | str | `appliance-000` | No |
| `COMMERCIAL_APPLIANCE_MODE_ENABLED` | bool | `false` | No |
| `COMMERCIAL_APPLIANCE_REQUIRE_REMOVABLE_MEDIA` | bool | `false` | No |
| `COMMERCIAL_AUTOSCALING_MODE` | str | `dry_run` | No |
| `COMMERCIAL_CALIBRATION_AUTO_APPLY` | bool | `false` | No |
| `COMMERCIAL_CALIBRATION_AUTO_APPLY_MAX_CHANGE_PERCENT` | float | `10.0` | No |
| `COMMERCIAL_CALIBRATION_AUTO_APPLY_MIN_CONFIDENCE` | str | `high` | No |
| `COMMERCIAL_CALIBRATION_AUTO_APPLY_MIN_RECENT_SAMPLES` | int | `20` | No |
| `COMMERCIAL_CALIBRATION_AUTO_APPLY_MODE` | str | `dry_run` | No |
| `COMMERCIAL_CALIBRATION_AUTO_APPLY_RATE_LIMIT_MINUTES` | int | `60` | No |
| `COMMERCIAL_CALIBRATION_AUTO_APPLY_REQUIRE_24H_DATA` | bool | `true` | No |
| `COMMERCIAL_CALIBRATION_CANARY_DEFAULT_PERCENT` | int | `5` | No |
| `COMMERCIAL_CALIBRATION_CANARY_MAX_PERCENT` | int | `25` | No |
| `COMMERCIAL_CALIBRATION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_CALIBRATION_LOOKBACK_DAYS` | int | `7` | No |
| `COMMERCIAL_CALIBRATION_MAX_MULTIPLIER` | float | `3.0` | No |
| `COMMERCIAL_CALIBRATION_MAX_RECOMMENDED_CHANGE_PERCENT` | float | `25.0` | No |
| `COMMERCIAL_CALIBRATION_MIN_MULTIPLIER` | float | `0.5` | No |
| `COMMERCIAL_CALIBRATION_MIN_SAMPLES` | int | `20` | No |
| `COMMERCIAL_CALIBRATION_MODE` | str | `recommend_only` | No |
| `COMMERCIAL_CALIBRATION_OUTLIER_TRIM_PERCENT` | float | `5.0` | No |
| `COMMERCIAL_CALIBRATION_USE_TRIMMED_MEAN` | bool | `true` | No |
| `COMMERCIAL_CANARY_AUTO_PROMOTION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_CANARY_AUTO_PROMOTION_MODE` | str | `dry_run` | No |
| `COMMERCIAL_CANARY_AUTO_ROLLBACK_ENABLED` | bool | `true` | No |
| `COMMERCIAL_CANARY_MAX_ERROR_RATE_PERCENT` | float | `2.0` | No |
| `COMMERCIAL_CANARY_MAX_ESTIMATION_ERROR_PERCENT` | float | `15.0` | No |
| `COMMERCIAL_CANARY_MAX_LATENCY_REGRESSION_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_CANARY_MIN_MARGIN_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_CANARY_MIN_OBSERVATION_MINUTES` | int | `60` | No |
| `COMMERCIAL_CANARY_MIN_REQUESTS_PER_STEP` | int | `100` | No |
| `COMMERCIAL_CANARY_PROMOTION_STEPS` | str | `5,10,25,50,100` | No |
| `COMMERCIAL_CAPACITY_FORECAST_WINDOW_MINUTES` | int | `60` | No |
| `COMMERCIAL_CAPACITY_PLANNING_ENABLED` | bool | `true` | No |
| `COMMERCIAL_CAPACITY_RETENTION_DAYS` | int | `30` | No |
| `COMMERCIAL_CAPACITY_SNAPSHOT_INTERVAL_SECONDS` | int | `30` | No |
| `COMMERCIAL_CLUSTER_ENVIRONMENT` | str | `local` | No |
| `COMMERCIAL_CLUSTER_ID` | str | `local` | No |
| `COMMERCIAL_CLUSTER_REGION` | str | `local` | No |
| `COMMERCIAL_COMPLIANCE_CONTROLS_ENABLED` | bool | `true` | No |
| `COMMERCIAL_COMPLIANCE_DEFAULT_APPROVER_COUNT` | int | `1` | No |
| `COMMERCIAL_COMPLIANCE_MODE` | str | `report_only` | No |
| `COMMERCIAL_COMPLIANCE_REQUIRE_EVIDENCE` | bool | `true` | No |
| `COMMERCIAL_COMPLIANCE_SEGREGATION_REQUIRED` | bool | `true` | No |
| `COMMERCIAL_CONFIDENTIAL_DEFAULT_RETENTION_SECONDS` | int | `0` | No |
| `COMMERCIAL_CONFIDENTIAL_PROHIBIT_PLAINTEXT_LOGGING` | bool | `true` | No |
| `COMMERCIAL_CONFIDENTIAL_REQUIRE_MODEL_TRUST` | bool | `true` | No |
| `COMMERCIAL_CONFIDENTIAL_RUNTIME_ENABLED` | bool | `false` | No |
| `COMMERCIAL_CONFIDENTIAL_RUNTIME_MODE` | str | `report_only` | No |
| `COMMERCIAL_COST_DRIFT_ALERT_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_ENABLED` | bool | `true` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | int | `5` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_RESET_SECONDS` | int | `60` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_ENABLED` | bool | `false` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_MAX_RETRIES` | int | `1` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_MAX_SHIFTED_PERCENT` | int | `10` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_MODE` | str | `disabled` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_REQUIRE_JWT` | bool | `true` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_REQUIRE_MTLS` | bool | `false` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_STREAM_TIMEOUT_SECONDS` | int | `30` | No |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_TIMEOUT_SECONDS` | int | `2` | No |
| `COMMERCIAL_DISTRIBUTED_ANALYTICS_ENABLED` | bool | `false` | No |
| `COMMERCIAL_ENTERPRISE_AUDIT_EXPORT_PDF_ENABLED` | bool | `false` | No |
| `COMMERCIAL_ENTERPRISE_AUDIT_LOG_RETENTION_DAYS` | int | `365` | No |
| `COMMERCIAL_ENTERPRISE_AUDIT_PORTAL_ENABLED` | bool | `true` | No |
| `COMMERCIAL_ENTERPRISE_AUDIT_REQUIRE_RBAC` | bool | `true` | No |
| `COMMERCIAL_EXECUTION_PROOFS_ENABLED` | bool | `true` | No |
| `COMMERCIAL_EXECUTION_PROOFS_EXPORT_ENABLED` | bool | `true` | No |
| `COMMERCIAL_EXECUTIVE_DASHBOARD_ENABLED` | bool | `true` | No |
| `COMMERCIAL_FEDERATION_ALLOW_PUSH` | bool | `false` | No |
| `COMMERCIAL_FEDERATION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_FEDERATION_MODE` | str | `disabled` | No |
| `COMMERCIAL_FEDERATION_REQUIRE_TOKEN` | bool | <redacted> | Yes |
| `COMMERCIAL_FEDERATION_RETENTION_DAYS` | int | `180` | No |
| `COMMERCIAL_FEDERATION_SHARED_TOKEN` | str | `-` | Yes |
| `COMMERCIAL_FEDERATION_SYNC_INTERVAL_SECONDS` | int | `300` | No |
| `COMMERCIAL_FINANCIAL_ANOMALY_DETECTION_ENABLED` | bool | `true` | No |
| `COMMERCIAL_FINANCIAL_ANOMALY_MIN_SAMPLES` | int | `7` | No |
| `COMMERCIAL_FINANCIAL_ANOMALY_PERCENT_THRESHOLD` | float | `30.0` | No |
| `COMMERCIAL_FINANCIAL_ANOMALY_ZSCORE_THRESHOLD` | float | `3.0` | No |
| `COMMERCIAL_FINANCIAL_AUDIT_CHAIN_ENABLED` | bool | `true` | No |
| `COMMERCIAL_FINANCIAL_DISPUTE_ENABLED` | bool | `true` | No |
| `COMMERCIAL_FINANCIAL_MANUAL_CREDIT_ENABLED` | bool | `false` | No |
| `COMMERCIAL_FINANCIAL_RECONCILIATION_ENABLED` | bool | `true` | No |
| `COMMERCIAL_FINANCIAL_RECONCILIATION_THRESHOLD_PERCENT` | float | `2.0` | No |
| `COMMERCIAL_GEO_ROUTING_ALLOW_CROSS_OCEAN` | bool | `false` | No |
| `COMMERCIAL_GEO_ROUTING_ENABLED` | bool | `false` | No |
| `COMMERCIAL_GEO_ROUTING_HEALTH_WEIGHT` | float | `0.15` | No |
| `COMMERCIAL_GEO_ROUTING_LATENCY_PENALTY_WEIGHT` | float | `0.35` | No |
| `COMMERCIAL_GEO_ROUTING_MARGIN_WEIGHT` | float | `0.35` | No |
| `COMMERCIAL_GEO_ROUTING_MAX_REGION_DISTANCE_KM` | int | `5000` | No |
| `COMMERCIAL_GEO_ROUTING_MODE` | str | `dry_run` | No |
| `COMMERCIAL_GEO_ROUTING_REGION_WEIGHT` | float | `0.15` | No |
| `COMMERCIAL_GLOBAL_ROUTING_ALLOW_CROSS_REGION` | bool | `false` | No |
| `COMMERCIAL_GLOBAL_ROUTING_ENABLED` | bool | `false` | No |
| `COMMERCIAL_GLOBAL_ROUTING_HEALTH_WEIGHT` | float | `0.15` | No |
| `COMMERCIAL_GLOBAL_ROUTING_LATENCY_WEIGHT` | float | `0.25` | No |
| `COMMERCIAL_GLOBAL_ROUTING_MARGIN_WEIGHT` | float | `0.4` | No |
| `COMMERCIAL_GLOBAL_ROUTING_MAX_LATENCY_MS` | int | `5000` | No |
| `COMMERCIAL_GLOBAL_ROUTING_MODE` | str | `disabled` | No |
| `COMMERCIAL_GLOBAL_ROUTING_PRIORITY_WEIGHT` | float | `0.1` | No |
| `COMMERCIAL_GLOBAL_ROUTING_REGION_WEIGHT` | float | `0.1` | No |
| `COMMERCIAL_GLOBAL_ROUTING_REQUIRE_HEALTHY_CLUSTER` | bool | `true` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_AUTO_ROLLBACK` | bool | `true` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_DEFAULT_CANARY_PERCENT` | int | `1` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_ENABLED` | bool | `false` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_CANARY_PERCENT` | int | `10` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_ERROR_RATE_PERCENT` | float | `2.0` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MAX_LATENCY_REGRESSION_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MIN_MARGIN_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_MODE` | str | `dry_run` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_REQUIRE_ADMIN_APPROVAL` | bool | `true` | No |
| `COMMERCIAL_GLOBAL_TRAFFIC_SHIFTING_REQUIRE_HEALTHY_TARGET` | bool | `true` | No |
| `COMMERCIAL_GOVERNANCE_FEDERATION_CLUSTER_ID` | str | `local` | No |
| `COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_GOVERNANCE_FEDERATION_MODE` | str | `disabled` | No |
| `COMMERCIAL_GOVERNANCE_FEDERATION_REGION` | str | `local` | No |
| `COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_SIGNATURE` | bool | `true` | No |
| `COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_TOKEN` | bool | <redacted> | Yes |
| `COMMERCIAL_GOVERNANCE_FEDERATION_SHARED_TOKEN` | str | `-` | Yes |
| `COMMERCIAL_GOVERNANCE_FEDERATION_SYNC_INTERVAL_SECONDS` | int | `300` | No |
| `COMMERCIAL_GPU_UTILIZATION_ALERT_PERCENT` | float | `90.0` | No |
| `COMMERCIAL_GUARDRAILS_ENABLED` | bool | `false` | No |
| `COMMERCIAL_HARDWARE_ATTESTATION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_HARDWARE_ATTESTATION_MODE` | str | `report_only` | No |
| `COMMERCIAL_INFRA_ADAPTERS_ENABLED` | str | `mock` | No |
| `COMMERCIAL_INFRA_EXECUTION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_INFRA_EXECUTION_MODE` | str | `simulation_only` | No |
| `COMMERCIAL_INFRA_REQUIRE_APPROVAL` | bool | `true` | No |
| `COMMERCIAL_INFRA_REQUIRE_FENCING` | bool | `true` | No |
| `COMMERCIAL_INFRA_REQUIRE_LEADER` | bool | `true` | No |
| `COMMERCIAL_INFRA_SIMULATION_ENABLED` | bool | `true` | No |
| `COMMERCIAL_K8S_CONTEXT` | str | `-` | No |
| `COMMERCIAL_K8S_DRY_RUN` | bool | `true` | No |
| `COMMERCIAL_K8S_EXECUTION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_K8S_NAMESPACE` | str | `default` | No |
| `COMMERCIAL_LATENCY_DRIFT_ALERT_PERCENT` | float | `25.0` | No |
| `COMMERCIAL_LATENCY_WEIGHT` | float | `0.15` | No |
| `COMMERCIAL_LEADER_ELECTION_ENABLED` | bool | `true` | No |
| `COMMERCIAL_LEADER_FENCING_ENABLED` | bool | `true` | No |
| `COMMERCIAL_LEASE_DURATION_SECONDS` | int | `60` | No |
| `COMMERCIAL_LEASE_HEARTBEAT_SECONDS` | int | `15` | No |
| `COMMERCIAL_LEASE_MAX_CLOCK_SKEW_SECONDS` | int | `5` | No |
| `COMMERCIAL_LEASE_RENEW_BEFORE_SECONDS` | int | `20` | No |
| `COMMERCIAL_LIVE_BALANCING_ENABLED` | bool | `false` | No |
| `COMMERCIAL_LIVE_BALANCING_HYSTERESIS_PERCENT` | float | `10.0` | No |
| `COMMERCIAL_LIVE_BALANCING_MAX_LATENCY_MS` | int | `5000` | No |
| `COMMERCIAL_LIVE_BALANCING_MAX_TRAFFIC_CHANGE_PERCENT` | int | `5` | No |
| `COMMERCIAL_LIVE_BALANCING_MIN_MARGIN_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_LIVE_BALANCING_MIN_STABLE_MINUTES` | int | `30` | No |
| `COMMERCIAL_LIVE_BALANCING_MODE` | str | `dry_run` | No |
| `COMMERCIAL_LIVE_BALANCING_REBALANCE_INTERVAL_SECONDS` | int | `300` | No |
| `COMMERCIAL_LOCAL_GPU_ALLOW_POWER_LIMIT` | bool | `false` | No |
| `COMMERCIAL_LOCAL_GPU_ALLOW_PROCESS_KILL` | bool | `false` | No |
| `COMMERCIAL_LOCAL_GPU_ALLOW_SERVICE_RESTART` | bool | `false` | No |
| `COMMERCIAL_LOCAL_GPU_ALLOWED_ACTIONS` | str | `inspect,metrics` | No |
| `COMMERCIAL_LOCAL_GPU_DRY_RUN` | bool | `true` | No |
| `COMMERCIAL_LOCAL_GPU_EXECUTION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_LOCAL_ROUTE_BONUS` | float | `10.0` | No |
| `COMMERCIAL_MARGIN_DRIFT_ALERT_PERCENT` | float | `15.0` | No |
| `COMMERCIAL_MARGIN_WEIGHT` | float | `0.6` | No |
| `COMMERCIAL_MAX_AUTOSCALING_COST_INCREASE_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_MAX_AUTOSCALING_MARGIN_DROP_PERCENT` | float | `10.0` | No |
| `COMMERCIAL_MAX_AUTOSCALING_SLA_RISK_PERCENT` | float | `5.0` | No |
| `COMMERCIAL_MAX_BLAST_RADIUS` | str | `medium` | No |
| `COMMERCIAL_MERKLE_TIMELINE_AUTO_SEAL` | bool | `false` | No |
| `COMMERCIAL_MERKLE_TIMELINE_WINDOW_MINUTES` | int | `60` | No |
| `COMMERCIAL_MERKLE_TIMELINES_ENABLED` | bool | `true` | No |
| `COMMERCIAL_MIN_MARGIN_PERCENT` | float | `20.0` | No |
| `COMMERCIAL_MODEL_INTEGRITY_AUTO_QUARANTINE` | bool | `false` | No |
| `COMMERCIAL_MODEL_INTEGRITY_BOOT_SCAN_ENABLED` | bool | `true` | No |
| `COMMERCIAL_MODEL_INTEGRITY_MONITOR_ENABLED` | bool | `true` | No |
| `COMMERCIAL_MODEL_INTEGRITY_SCAN_INTERVAL_SECONDS` | int | `3600` | No |
| `COMMERCIAL_MODEL_LIFECYCLE_AUTO_QUARANTINE` | bool | `false` | No |
| `COMMERCIAL_MODEL_LIFECYCLE_ENABLED` | bool | `true` | No |
| `COMMERCIAL_MODEL_LIFECYCLE_MODE` | str | `report_only` | No |
| `COMMERCIAL_MODEL_LIFECYCLE_OFFLINE_VERIFICATION_STRICT` | bool | `true` | No |
| `COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_APPROVAL` | bool | `true` | No |
| `COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_CHECKSUM` | bool | `true` | No |
| `COMMERCIAL_MODEL_LIFECYCLE_REQUIRE_LINEAGE` | bool | `true` | No |
| `COMMERCIAL_MODEL_QUARANTINE_ON_CHECKSUM_MISMATCH` | bool | `true` | No |
| `COMMERCIAL_MODEL_REQUIRE_CHECKSUM_FOR_LOCAL` | bool | `true` | No |
| `COMMERCIAL_MODEL_REQUIRE_TRUSTED_FOR_ROUTING` | bool | `false` | No |
| `COMMERCIAL_MODEL_SUPPLY_CHAIN_ENABLED` | bool | `true` | No |
| `COMMERCIAL_MODEL_TRUST_ENFORCEMENT_MODE` | str | `report_only` | No |
| `COMMERCIAL_NEGATIVE_MARGIN_ALERT` | bool | `true` | No |
| `COMMERCIAL_NODE_HEARTBEAT_INTERVAL_SECONDS` | int | `30` | No |
| `COMMERCIAL_NODE_OFFLINE_AFTER_SECONDS` | int | `120` | No |
| `COMMERCIAL_NOMAD_ADDR` | str | `-` | No |
| `COMMERCIAL_NOMAD_DRY_RUN` | bool | `true` | No |
| `COMMERCIAL_NOMAD_EXECUTION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_NOMAD_TOKEN` | str | `-` | Yes |
| `COMMERCIAL_OFFLINE_CRL_ENABLED` | bool | `true` | No |
| `COMMERCIAL_OPERATIONAL_CONTROL_DEFAULT_EVIDENCE_SLA_DAYS` | int | `90` | No |
| `COMMERCIAL_OPERATIONAL_CONTROL_OVERDUE_ESCALATIONS_ENABLED` | bool | `true` | No |
| `COMMERCIAL_OPERATIONAL_CONTROLS_ENABLED` | bool | `true` | No |
| `COMMERCIAL_OPERATIONAL_CONTROLS_MODE` | str | `report_only` | No |
| `COMMERCIAL_P95_LATENCY_ALERT_MS` | int | `5000` | No |
| `COMMERCIAL_PROXMOX_ALLOWED_CT_IDS` | str | `-` | No |
| `COMMERCIAL_PROXMOX_ALLOWED_VM_IDS` | str | `-` | No |
| `COMMERCIAL_PROXMOX_API_URL` | str | `-` | No |
| `COMMERCIAL_PROXMOX_DRY_RUN` | bool | `true` | No |
| `COMMERCIAL_PROXMOX_EXECUTION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_PROXMOX_NODE` | str | `-` | No |
| `COMMERCIAL_PROXMOX_TOKEN_ID` | str | `-` | Yes |
| `COMMERCIAL_PROXMOX_TOKEN_SECRET` | str | `-` | Yes |
| `COMMERCIAL_PROXMOX_VERIFY_TLS` | bool | `true` | No |
| `COMMERCIAL_PUBLIC_ATTESTATION_ALLOW_ANONYMOUS` | bool | `false` | No |
| `COMMERCIAL_PUBLIC_ATTESTATION_GATEWAY_ENABLED` | bool | `false` | No |
| `COMMERCIAL_PUBLIC_ATTESTATION_MAX_PAYLOAD_KB` | int | `512` | No |
| `COMMERCIAL_PUBLIC_ATTESTATION_MODE` | str | `local_only` | No |
| `COMMERCIAL_PUBLIC_ATTESTATION_RATE_LIMIT_RPM` | int | `60` | No |
| `COMMERCIAL_QOS_BASIC_RPM` | int | `60` | No |
| `COMMERCIAL_QOS_BILLING_DEBIT_WALLET` | bool | `false` | No |
| `COMMERCIAL_QOS_BILLING_ENABLED` | bool | `false` | No |
| `COMMERCIAL_QOS_BILLING_INCLUDE_OPPORTUNITY_COST` | bool | `false` | No |
| `COMMERCIAL_QOS_BILLING_INVOICE_LINE_ITEM` | bool | `true` | No |
| `COMMERCIAL_QOS_BILLING_MAX_DAILY_DEBIT_BRL_PER_CLIENT` | float | `100.0` | No |
| `COMMERCIAL_QOS_BILLING_MIN_AMOUNT_BRL` | float | `0.01` | No |
| `COMMERCIAL_QOS_BILLING_MODE` | str | `report_only` | No |
| `COMMERCIAL_QOS_CHARGEBACK_ENABLED` | bool | `true` | No |
| `COMMERCIAL_QOS_CHARGEBACK_MODE` | str | `report_only` | No |
| `COMMERCIAL_QOS_ENTERPRISE_RPM` | int | `5000` | No |
| `COMMERCIAL_QOS_FAIRNESS_COLLECTION_INTERVAL_SECONDS` | int | `60` | No |
| `COMMERCIAL_QOS_FAIRNESS_ENABLED` | bool | `true` | No |
| `COMMERCIAL_QOS_FREE_RPM` | int | `10` | No |
| `COMMERCIAL_QOS_MAX_STARVATION_SECONDS` | int | `1800` | No |
| `COMMERCIAL_QOS_PREMIUM_RPM` | int | `1000` | No |
| `COMMERCIAL_QOS_PRIORITY_INVERSION_ALERT` | bool | `true` | No |
| `COMMERCIAL_QOS_PRIORITY_QUEUE_ENABLED` | bool | `false` | No |
| `COMMERCIAL_QOS_PRIORITY_QUEUE_MODE` | str | `shadow` | No |
| `COMMERCIAL_QOS_PRIORITY_SLOT_COST_BRL_PER_SECOND` | float | `0.001` | No |
| `COMMERCIAL_QOS_PRO_RPM` | int | `300` | No |
| `COMMERCIAL_QOS_QUEUE_AGING_SECONDS` | int | `300` | No |
| `COMMERCIAL_QOS_RATE_LIMIT_MODE` | str | `report_only` | No |
| `COMMERCIAL_QOS_RATE_LIMITING_ENABLED` | bool | `true` | No |
| `COMMERCIAL_QOS_STARVATION_THRESHOLD_SECONDS` | int | `1800` | No |
| `COMMERCIAL_QUALITY_WEIGHT` | float | `0.25` | No |
| `COMMERCIAL_QUEUE_DEPTH_ALERT` | int | `100` | No |
| `COMMERCIAL_RAG_VAULT_ENABLE_IMMUTABLE_AUDIT` | bool | `true` | No |
| `COMMERCIAL_RAG_VAULT_ENABLE_POISON_DETECTION` | bool | `true` | No |
| `COMMERCIAL_RAG_VAULT_ENABLED` | bool | `false` | No |
| `COMMERCIAL_RAG_VAULT_MAX_CONTEXT_CHUNKS` | int | `20` | No |
| `COMMERCIAL_RAG_VAULT_POLICY_MODE` | str | `report_only` | No |
| `COMMERCIAL_RAG_VAULT_REQUIRE_CONFIDENTIAL_RUNTIME` | bool | `false` | No |
| `COMMERCIAL_RAG_VAULT_REQUIRE_SIGNED_DOCUMENTS` | bool | `false` | No |
| `COMMERCIAL_RECEIPT_SIGNATURE_ALGORITHM` | str | `ed25519` | No |
| `COMMERCIAL_RECEIPTS_CHAINING_ENABLED` | bool | `true` | No |
| `COMMERCIAL_RECEIPTS_ENABLED` | bool | `true` | No |
| `COMMERCIAL_RECEIPTS_EXPORT_ENABLED` | bool | `true` | No |
| `COMMERCIAL_RECEIPTS_SIGNATURE_REQUIRED` | bool | `false` | No |
| `COMMERCIAL_RECEIPTS_TIMESTAMP_MODE` | str | `local` | No |
| `COMMERCIAL_REPLAY_ALLOW_CROSS_BACKEND` | bool | `false` | No |
| `COMMERCIAL_REPLAY_CAPTURE_PROMPT_HASH_ONLY` | bool | `true` | No |
| `COMMERCIAL_REPLAY_DEFAULT_MODE` | str | `best_effort` | No |
| `COMMERCIAL_REPLAY_MAX_AGE_DAYS` | int | `30` | No |
| `COMMERCIAL_REPORT_DEFAULT_RECIPIENTS` | str | `-` | No |
| `COMMERCIAL_REPORT_EMAIL_ALLOWLIST` | str | `-` | No |
| `COMMERCIAL_REPORT_EMAIL_ENABLED` | bool | `false` | No |
| `COMMERCIAL_REPORT_EMAIL_MAX_RECIPIENTS` | int | `10` | No |
| `COMMERCIAL_REPORT_EMAIL_MODE` | str | `disabled` | No |
| `COMMERCIAL_REPORT_EMAIL_PROVIDER` | str | `disabled` | No |
| `COMMERCIAL_REPORT_EMAIL_RETRY_BACKOFF_SECONDS` | int | `10` | No |
| `COMMERCIAL_REPORT_EMAIL_RETRY_COUNT` | int | `3` | No |
| `COMMERCIAL_REPORT_SEND_REAL_EMAIL` | bool | `false` | No |
| `COMMERCIAL_REPORT_SMTP_FROM` | str | `-` | No |
| `COMMERCIAL_REPORT_SMTP_HOST` | str | `-` | No |
| `COMMERCIAL_REPORT_SMTP_PASSWORD` | str | `-` | Yes |
| `COMMERCIAL_REPORT_SMTP_PORT` | int | `587` | No |
| `COMMERCIAL_REPORT_SMTP_TIMEOUT_SECONDS` | int | `15` | No |
| `COMMERCIAL_REPORT_SMTP_USE_STARTTLS` | bool | `true` | No |
| `COMMERCIAL_REPORT_SMTP_USE_TLS` | bool | `true` | No |
| `COMMERCIAL_REPORT_SMTP_USERNAME` | str | `-` | No |
| `COMMERCIAL_REPRODUCIBILITY_ENABLED` | bool | `true` | No |
| `COMMERCIAL_REQUIRE_APPROVAL_FOR_CRITICAL` | bool | `true` | No |
| `COMMERCIAL_REVENUE_EMAIL_ESCALATION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_REVENUE_EMAIL_ESCALATION_RECIPIENTS` | str | `-` | No |
| `COMMERCIAL_REVENUE_ESCALATION_COOLDOWN_MINUTES` | int | `30` | No |
| `COMMERCIAL_REVENUE_ESCALATION_MAX_RETRIES` | int | `3` | No |
| `COMMERCIAL_REVENUE_ESCALATIONS_ENABLED` | bool | `true` | No |
| `COMMERCIAL_REVENUE_ESCALATIONS_MODE` | str | `dry_run` | No |
| `COMMERCIAL_REVENUE_FORECAST_METHOD` | str | `ewma` | No |
| `COMMERCIAL_REVENUE_FORECAST_MIN_SAMPLES` | int | `7` | No |
| `COMMERCIAL_REVENUE_FORECAST_WINDOW_DAYS` | int | `30` | No |
| `COMMERCIAL_REVENUE_FORECASTING_ENABLED` | bool | `true` | No |
| `COMMERCIAL_REVENUE_PAGERDUTY_ENABLED` | bool | `false` | No |
| `COMMERCIAL_REVENUE_PAGERDUTY_ROUTING_KEY` | str | `-` | Yes |
| `COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE` | bool | `false` | No |
| `COMMERCIAL_REVENUE_PROTECTION_COOLDOWN_MINUTES` | int | `60` | No |
| `COMMERCIAL_REVENUE_PROTECTION_ENABLED` | bool | `true` | No |
| `COMMERCIAL_REVENUE_PROTECTION_MODE` | str | `report_only` | No |
| `COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_ENABLED` | bool | `false` | No |
| `COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_URL` | str | `-` | No |
| `COMMERCIAL_REVENUE_SLACK_ENABLED` | bool | `false` | No |
| `COMMERCIAL_REVENUE_SLACK_WEBHOOK_URL` | str | `-` | No |
| `COMMERCIAL_REVENUE_WEBHOOK_ENABLED` | bool | `false` | No |
| `COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET` | str | `-` | Yes |
| `COMMERCIAL_REVENUE_WEBHOOK_URL` | str | `-` | No |
| `COMMERCIAL_ROUTING_DEFAULT_POLICY` | str | `disabled` | No |
| `COMMERCIAL_ROUTING_ENABLED` | bool | `false` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_BLOCK_UNTRUSTED` | bool | `false` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_CHALLENGE_TTL_SECONDS` | int | `60` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_ENCLAVE_TYPE` | str | `software_attested` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_ENFORCE_ON_STARTUP` | bool | `false` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_EVIDENCE_TTL_SECONDS` | int | `3600` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_MAX_DRIFT_THRESHOLD` | float | `0.1` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_MIN_TRUST_SCORE` | float | `0.0` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_MODE` | str | `report_only` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_PLATFORM_TYPE` | str | `linux_x86_64` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SENSITIVE_TENANTS` | bool | `false` | No |
| `COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SOVEREIGN` | bool | `false` | No |
| `COMMERCIAL_SAFETY_GATES_ENABLED` | bool | `true` | No |
| `COMMERCIAL_SLA_RISK_ALERT_PERCENT` | float | `5.0` | No |
| `COMMERCIAL_SOVEREIGN_GOVERNANCE_ENABLED` | bool | `true` | No |
| `COMMERCIAL_SOVEREIGN_LIFECYCLE_BLOCK_UNAPPROVED` | bool | `false` | No |
| `COMMERCIAL_SOVEREIGN_LIFECYCLE_ENFORCE` | bool | `false` | No |
| `COMMERCIAL_TENANT_ENCRYPTION_AUTO_ROTATION_DAYS` | int | `90` | No |
| `COMMERCIAL_TENANT_ENCRYPTION_BLOCK_RESTRICTED_EXPORTS` | bool | `true` | No |
| `COMMERCIAL_TENANT_ENCRYPTION_ENABLED` | bool | `true` | No |
| `COMMERCIAL_TENANT_ENCRYPTION_MASTER_KEY` | str | <redacted> | Yes |
| `COMMERCIAL_TENANT_ENCRYPTION_MODE` | str | `report_only` | No |
| `COMMERCIAL_TENANT_ENCRYPTION_REQUIRE_ENCRYPTED_EXPORTS` | bool | `false` | No |
| `COMMERCIAL_TRANSPARENCY_CHECKPOINT_INTERVAL_MINUTES` | int | `60` | No |
| `COMMERCIAL_TRANSPARENCY_GOSSIP_ENABLED` | bool | `false` | No |
| `COMMERCIAL_TRANSPARENCY_GOSSIP_MODE` | str | `dry_run` | No |
| `COMMERCIAL_TRANSPARENCY_REQUIRE_WITNESS_QUORUM` | bool | `false` | No |
| `COMMERCIAL_TRANSPARENCY_SPLIT_VIEW_ALERTS` | bool | `true` | No |
| `COMMERCIAL_WITNESS_FEDERATION_ENABLED` | bool | `false` | No |
| `COMMERCIAL_WITNESS_MIN_SIGNATURES` | int | `1` | No |
| `COMMERCIAL_WITNESS_MODE` | str | `dry_run` | No |
| `COMMERCIAL_WITNESS_REQUEST_TIMEOUT_SECONDS` | int | `10` | No |
| `COMMERCIAL_WITNESS_REQUIRE_EXTERNAL` | bool | `false` | No |
| `COMMERCIAL_WITNESS_SIGNATURE_ALGORITHM` | str | `ed25519` | No |
| `COMMERCIAL_WORKFLOW_CHECKPOINT_FREQUENCY` | int | `1` | No |
| `COMMERCIAL_WORKFLOW_DETERMINISM_ENABLED` | bool | `false` | No |
| `COMMERCIAL_WORKFLOW_DRIFT_THRESHOLD` | float | `0.01` | No |
| `COMMERCIAL_WORKFLOW_ENFORCE_REPRODUCIBILITY` | bool | `true` | No |

## `content`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CONTENT_MODERATION_ENABLED` | bool | `true` | No |
| `CONTENT_MODERATION_TOXICITY_THRESHOLD` | float | `0.7` | No |

## `control`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CONTROL_PLANE_HOST` | str | `0.0.0.0` | No |
| `CONTROL_PLANE_PORT` | int | `8080` | No |

## `cors`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CORS_ALLOW_ORIGINS` | str | `-` | No |

## `create`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `CREATE_TABLES_ON_STARTUP` | bool | `false` | No |

## `data`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DATA_PLANE_BASE_URL` | str | `PydanticUndefined` | No |
| `DATA_PLANE_TIMEOUT_SECONDS` | int | `120` | No |
| `DATA_RESIDENCY_ENABLED` | bool | `false` | No |

## `database`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DATABASE_URL` | str | `PydanticUndefined` | No |

## `debug`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DEBUG` | bool | `false` | No |

## `deepseek`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DEEPSEEK_API_KEY` | str | `-` | Yes |
| `DEEPSEEK_BASE_URL` | str | `-` | No |
| `DEEPSEEK_CHAT_MODEL` | str | `-` | No |

## `default`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DEFAULT_EMBEDDING_MODEL` | str | `text-embedding-3-small` | No |
| `DEFAULT_MAX_TOKENS` | int | <redacted> | Yes |
| `DEFAULT_TEMPERATURE` | float | `0.7` | No |
| `DEFAULT_TOP_P` | float | `0.95` | No |

## `demo`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DEMO_CLIENT_NAME` | str | `demo-client` | No |
| `DEMO_DAILY_TOKEN_QUOTA` | int | <redacted> | Yes |
| `DEMO_MODE` | bool | `false` | No |
| `DEMO_MONTHLY_TOKEN_QUOTA` | int | <redacted> | Yes |
| `DEMO_RATE_LIMIT_PER_MINUTE` | int | `5` | No |

## `deployment`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DEPLOYMENT_AUTOSCALE_ENABLED` | bool | `true` | No |
| `DEPLOYMENT_AUTOSCALE_WINDOW_SEC` | int | `60` | No |
| `DEPLOYMENT_MODE` | str | `appliance` | No |

## `disaster`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DISASTER_RECOVERY_BACKUP_DIR` | str | `/tmp/agent-backups` | No |
| `DISASTER_RECOVERY_ENABLED` | bool | `false` | No |
| `DISASTER_RECOVERY_SCHEDULE_HOURS` | int | `24` | No |

## `distributed`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DISTRIBUTED_RUNTIME_ENABLED` | bool | `false` | No |

## `docs`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DOCS_BASE_URL` | str | `-` | No |

## `document`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `DOCUMENT_VISION_ENABLED` | bool | `false` | No |

## `email`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `EMAIL_PROVIDER` | str | `mock` | No |

## `embedding`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `EMBEDDING_DIMENSIONS` | int | `384` | No |

## `embeddings`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `EMBEDDINGS_BACKEND` | str | `local` | No |
| `EMBEDDINGS_ENABLED` | bool | `true` | No |

## `enterprise`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ENTERPRISE_SSO_AZURE_CLIENT_ID` | str | `-` | No |
| `ENTERPRISE_SSO_AZURE_CLIENT_SECRET` | str | `-` | Yes |
| `ENTERPRISE_SSO_ENABLED` | bool | `false` | No |
| `ENTERPRISE_SSO_OKTA_CLIENT_ID` | str | `-` | No |
| `ENTERPRISE_SSO_OKTA_CLIENT_SECRET` | str | `-` | Yes |
| `ENTERPRISE_SSO_OKTA_DOMAIN` | str | `-` | No |
| `ENTERPRISE_SSO_SAML_CERTIFICATE` | str | `-` | No |
| `ENTERPRISE_SSO_SAML_ENTITY_ID` | str | `-` | No |
| `ENTERPRISE_SSO_SAML_SSO_URL` | str | `-` | No |
| `ENTERPRISE_SSO_TENANT_ID` | str | `-` | No |

## `experiment`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `EXPERIMENT_TRACKING_ENABLED` | bool | `false` | No |

## `fcm`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `FCM_API_KEY` | str | `-` | Yes |

## `fine`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `FINE_TUNING_ENABLED` | bool | `false` | No |
| `FINE_TUNING_GPU_PROVIDER` | bool | `false` | No |

## `fireworks`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `FIREWORKS_API_KEY` | str | `-` | Yes |
| `FIREWORKS_PROVIDER_ENABLED` | bool | `true` | No |

## `frontend`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `FRONTEND_URL` | str | `http://localhost:5173` | No |

## `gemini`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | str | `-` | Yes |
| `GEMINI_BASE_URL` | str | `-` | No |
| `GEMINI_PROVIDER_ENABLED` | bool | `true` | No |

## `global`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `GLOBAL_CLOUD_KILL_SWITCH` | bool | `false` | No |

## `gpu`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `GPU_AUTOSCALING_ENABLED` | bool | `false` | No |

## `groq`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | str | `-` | Yes |
| `GROQ_PROVIDER_ENABLED` | bool | `true` | No |

## `hardware`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `HARDWARE_TRUST_ENABLED` | bool | `false` | No |
| `HARDWARE_TRUST_PROVIDER` | str | `mock` | No |

## `image`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `IMAGE_GENERATION_ENABLED` | bool | `false` | No |

## `inference`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `INFERENCE_MAX_COMPLETION_TOKENS` | int | <redacted> | Yes |
| `INFERENCE_MAX_CONTEXT_TOKENS` | int | <redacted> | Yes |
| `INFERENCE_MAX_HISTORY_MESSAGES` | int | `8` | No |
| `INFERENCE_MAX_SYSTEM_CHARS` | int | `2500` | No |

## `jaeger`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `JAEGER_EXPORT_ENABLED` | bool | `false` | No |

## `jwt`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `JWT_SECRET` | str | <redacted> | Yes |

## `kb`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `KB_URL_INGESTION_ENABLED` | bool | `false` | No |

## `kubernetes`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `KUBERNETES_MODE` | bool | `false` | No |

## `lmstudio`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `LMSTUDIO_API_KEY` | str | <redacted> | Yes |
| `LMSTUDIO_BASE_URL` | str | `http://192.168.101.1:1234/v1` | No |
| `LMSTUDIO_CHAT_MODEL` | str | `nvidia/nemotron-3-nano-4b` | No |
| `LMSTUDIO_ENABLED` | bool | `false` | No |
| `LMSTUDIO_TIMEOUT` | int | `60` | No |

## `local`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `LOCAL_APPLIANCE_MODE` | bool | `false` | No |
| `LOCAL_BILLING_MODE` | str | `manual` | No |

## `localhost`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `LOCALHOST_MODE` | bool | `false` | No |

## `log`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `LOG_LEVEL` | str | `INFO` | No |

## `managed`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MANAGED_CONTROL_PLANE_ENABLED` | bool | `false` | No |

## `margin`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MARGIN_WARNING_PERCENT` | float | `20.0` | No |

## `marketplace`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MARKETPLACE_GOVERNANCE_ENABLED` | bool | `true` | No |
| `MARKETPLACE_REQUIRE_APPROVAL` | bool | `true` | No |
| `MARKETPLACE_REQUIRE_SECURITY_SCAN` | bool | `true` | No |

## `max`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL` | float | `0.0` | No |
| `MAX_CONCURRENT_GENERATIONS` | int | `1` | No |
| `MAX_CONTEXT_TOKENS` | int | <redacted> | Yes |
| `MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL` | float | `0.0` | No |
| `MAX_INPUT_TOKENS` | int | <redacted> | Yes |
| `MAX_PROVIDER_COST_PER_DAY_BRL` | float | `0.0` | No |
| `MAX_QUEUE_SIZE` | int | `8` | No |
| `MAX_REQUEST_BODY_SIZE_BYTES` | int | `5242880` | No |
| `MAX_TEMPERATURE` | float | `1.5` | No |
| `MAX_TOOL_ARGUMENTS_BYTES` | int | `16384` | No |
| `MAX_TOOL_SCHEMA_BYTES` | int | `24576` | No |
| `MAX_TOOL_SCHEMA_DEPTH` | int | `16` | No |
| `MAX_TOOL_SCHEMA_PROPERTIES` | int | `256` | No |
| `MAX_TOOLS_PER_REQUEST` | int | `16` | No |
| `MAX_TOP_P` | float | `1.0` | No |

## `mercadopago`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MERCADOPAGO_ACCESS_TOKEN` | str | `-` | Yes |

## `milvus`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MILVUS_ENABLED` | bool | `false` | No |
| `MILVUS_TOKEN` | str | None | `-` | Yes |
| `MILVUS_URL` | str | `http://localhost:19530` | No |

## `mistral`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MISTRAL_API_KEY` | str | `-` | Yes |
| `MISTRAL_PROVIDER_ENABLED` | bool | `true` | No |

## `mlflow`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MLFLOW_INTEGRATION_ENABLED` | bool | `false` | No |

## `mlops`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MLOPS_DATASET_STORAGE_PATH` | str | `-` | No |
| `MLOPS_ENABLED` | bool | `false` | No |

## `mobile`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MOBILE_FOUNDATION_ENABLED` | bool | `false` | No |

## `mock`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MOCK_BACKEND_ENABLED` | bool | `false` | No |

## `model`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MODEL_AB_TESTING_ENABLED` | bool | `false` | No |
| `MODEL_CANARY_ENABLED` | bool | `false` | No |
| `MODEL_EXPERIMENTS_ENABLED` | bool | `false` | No |
| `MODEL_FILE` | str | `gemma-4-E4B-it-Q4_K_M.gguf` | No |
| `MODEL_HOT_SWAP_ENABLED` | bool | `false` | No |
| `MODEL_ID` | str | `unsloth/gemma-4-E4B-it-GGUF` | No |
| `MODEL_LOAD_TIMEOUT_SECONDS` | int | `120` | No |
| `MODEL_ROLLBACK_ON_FAILURE` | bool | `true` | No |
| `MODEL_RUNTIME_MOCK_ENABLED` | bool | `false` | No |
| `MODEL_RUNTIME_PORT_END` | int | `18120` | No |
| `MODEL_RUNTIME_PORT_START` | int | `18081` | No |

## `models`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MODELS_DIR` | str | `/models` | No |

## `multi`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MULTI_CLUSTER_ENABLED` | bool | `false` | No |

## `multimodal`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `MULTIMODAL_ENABLED` | bool | `false` | No |

## `nats`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `NATS_TRIGGER_ENABLED` | bool | `false` | No |
| `NATS_URL` | str | `nats://localhost:4222` | No |

## `negative`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `NEGATIVE_MARGIN_BLOCK_MODE` | str | `report_only` | No |

## `node`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `NODE_ID` | str | `-` | No |
| `NODE_ROLE` | str | `api` | No |

## `oauth`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OAUTH_ENABLED` | bool | `false` | No |
| `OAUTH_GITHUB_CLIENT_ID` | str | `-` | No |
| `OAUTH_GITHUB_CLIENT_SECRET` | str | `-` | Yes |
| `OAUTH_GOOGLE_CLIENT_ID` | str | `-` | No |
| `OAUTH_GOOGLE_CLIENT_SECRET` | str | `-` | Yes |

## `observability`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OBSERVABILITY_ENABLED` | bool | `true` | No |

## `ollama`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OLLAMA_BASE_URL` | str | `http://data-plane-ollama:11434` | No |

## `openai`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | str | `-` | Yes |
| `OPENAI_BASE_URL` | str | `-` | No |
| `OPENAI_CHAT_MODEL` | str | `-` | No |
| `OPENAI_EMBEDDINGS_MODEL` | str | `-` | No |

## `openrouter`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | str | `-` | Yes |
| `OPENROUTER_BASE_URL` | str | `-` | No |

## `operational`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OPERATIONAL_PROFILE` | str | `lite` | No |

## `opsgenie`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OPSGENIE_API_KEY` | str | `-` | Yes |
| `OPSGENIE_API_URL` | str | `https://api.opsgenie.com/v2/alerts` | No |

## `otlp`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `OTLP_EXPORT_ENABLED` | bool | `false` | No |

## `pagerduty`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PAGERDUTY_ROUTING_KEY` | str | `-` | Yes |

## `payment`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PAYMENT_PROCESSING_ENABLED` | bool | `false` | No |
| `PAYMENT_PROVIDER` | str | `mock` | No |
| `PAYMENT_REAL_ENABLED` | bool | `false` | No |
| `PAYMENT_WEBHOOK_SECRET` | str | `-` | Yes |

## `perplexity`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PERPLEXITY_API_KEY` | str | `-` | Yes |
| `PERPLEXITY_PROVIDER_ENABLED` | bool | `true` | No |

## `pinecone`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PINECONE_API_KEY` | str | `-` | Yes |
| `PINECONE_ENVIRONMENT` | str | `us-east-1-aws` | No |
| `PINECONE_INDEX_NAME` | str | `agent-memory` | No |

## `pix`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PIX_PAYMENT_ENABLED` | bool | `false` | No |

## `pki`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PKI_CA_ROTATION_DAYS` | int | `365` | No |
| `PKI_CERT_ROTATION_DAYS` | int | `90` | No |
| `PKI_ENABLED` | bool | `false` | No |
| `PKI_STORAGE_PATH` | str | `./data/pki` | No |

## `platform`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PLATFORM_PROFILE` | str | `appliance` | No |

## `plugin`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PLUGIN_MARKETPLACE_ENABLED` | bool | `false` | No |
| `PLUGIN_RUNTIME_ENABLED` | bool | `false` | No |
| `PLUGIN_SIGNATURE_REQUIRED` | bool | `false` | No |

## `project`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PROJECT_NAME` | str | `local-llm-inference-stack` | No |
| `PROJECT_VERSION` | str | `PydanticUndefined` | No |

## `prompt`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PROMPT_TEMPLATE_PLAYGROUND_ENABLED` | bool | `false` | No |
| `PROMPT_TEMPLATES_ENABLED` | bool | `false` | No |

## `provider`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PROVIDER_FAIL_CLOSED` | bool | `true` | No |
| `PROVIDER_MAX_RETRIES` | int | `2` | No |

## `providers`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PROVIDERS_ENABLED` | str | `local,lmstudio` | No |

## `public`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PUBLIC_ANALYTICS_PROVIDER` | str | `none` | No |
| `PUBLIC_API_ENABLED` | bool | `false` | No |
| `PUBLIC_BASE_URL` | str | `-` | No |
| `PUBLIC_BRAND_NAME` | str | `LLM Inference Stack Cloud` | No |
| `PUBLIC_EXPOSURE` | bool | `false` | No |
| `PUBLIC_PLAUSIBLE_DOMAIN` | str | `-` | No |
| `PUBLIC_PLAUSIBLE_SRC` | str | `https://plausible.io/js/script.js` | No |
| `PUBLIC_SIGNUP_ENABLED` | bool | `true` | No |
| `PUBLIC_SUPPORT_EMAIL` | str | `sales@example.com` | No |

## `pulsar`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PULSAR_TRIGGER_ENABLED` | bool | `false` | No |
| `PULSAR_URL` | str | `pulsar://localhost:6650` | No |

## `push`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `PUSH_NOTIFICATIONS_ENABLED` | bool | `false` | No |
| `PUSH_PROVIDER` | str | `mock` | No |

## `qdrant`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `QDRANT_API_KEY` | str | None | `-` | Yes |
| `QDRANT_ENABLED` | bool | `false` | No |
| `QDRANT_URL` | str | `http://localhost:6333` | No |

## `queue`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `QUEUE_ADMIN_MAX_ACTIVE` | int | `10` | No |
| `QUEUE_ADMIN_MAX_WAITING` | int | `20` | No |
| `QUEUE_ADMIN_TIMEOUT` | int | `60` | No |
| `QUEUE_BASIC_MAX_ACTIVE` | int | `2` | No |
| `QUEUE_BASIC_MAX_WAITING` | int | `10` | No |
| `QUEUE_BASIC_TIMEOUT` | int | `20` | No |
| `QUEUE_FREE_MAX_ACTIVE` | int | `1` | No |
| `QUEUE_FREE_MAX_WAITING` | int | `5` | No |
| `QUEUE_FREE_TIMEOUT` | int | `15` | No |
| `QUEUE_PREMIUM_MAX_ACTIVE` | int | `5` | No |
| `QUEUE_PREMIUM_MAX_WAITING` | int | `15` | No |
| `QUEUE_PREMIUM_TIMEOUT` | int | `30` | No |
| `QUEUE_TIMEOUT_SECONDS` | int | `30` | No |

## `rag`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `RAG_CHUNK_OVERLAP` | int | `150` | No |
| `RAG_CHUNK_SIZE` | int | `1000` | No |
| `RAG_EMBEDDING_MODEL` | str | `sentence-transformers/all-MiniLM-L6-v2` | No |
| `RAG_EMBEDDING_PROVIDER` | str | `local` | No |
| `RAG_ENABLED` | bool | `true` | No |
| `RAG_MAX_FILE_MB` | int | `25` | No |
| `RAG_STORAGE_DIR` | str | `./data/rag_uploads` | No |
| `RAG_TOP_K_DEFAULT` | int | `5` | No |

## `rate`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `RATE_LIMIT_GLOBAL_PER_MINUTE` | int | `1000` | No |
| `RATE_LIMIT_TENANT_PER_MINUTE` | int | `500` | No |

## `rbac`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `RBAC_ADMIN_ENABLED` | bool | `true` | No |

## `real`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `REAL_PROVIDER_LOG_PROMPTS` | bool | `false` | No |
| `REAL_PROVIDER_MAX_COST_BRL` | float | `2.0` | No |
| `REAL_PROVIDER_STORE_RESPONSES` | bool | `false` | No |
| `REAL_PROVIDER_VALIDATION_ENABLED` | bool | `false` | No |

## `realtime`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `REALTIME_AUDIO_ENABLED` | bool | `false` | No |
| `REALTIME_VOICE_ENABLED` | bool | `false` | No |

## `redis`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `REDIS_URL` | str | `PydanticUndefined` | No |

## `replicate`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `REPLICATE_API_KEY` | str | `-` | Yes |
| `REPLICATE_PROVIDER_ENABLED` | bool | `true` | No |

## `request`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `REQUEST_TIMEOUT_SECONDS` | int | `120` | No |

## `response`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `RESPONSE_CACHE_ENABLED` | bool | `true` | No |
| `RESPONSE_CACHE_TTL_SECONDS` | int | `3600` | No |

## `retry`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `RETRY_ATTEMPTS` | int | `2` | No |
| `RETRY_BACKOFF_SECONDS` | float | `1.0` | No |

## `routing`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ROUTING_TEST_FORCE_LOCAL_FAILURE` | bool | `false` | No |

## `secrets`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `SECRETS_MANAGER_PROVIDER` | str | <redacted> | Yes |

## `semantic`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `SEMANTIC_CACHE_ENABLED` | bool | `false` | No |

## `sendgrid`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `SENDGRID_API_KEY` | str | `-` | Yes |

## `smtp`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `SMTP_HOST` | str | `localhost` | No |
| `SMTP_PASSWORD` | str | `-` | Yes |
| `SMTP_PORT` | int | `1025` | No |
| `SMTP_USERNAME` | str | `-` | No |

## `speech`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `SPEECH_TO_TEXT_ENABLED` | bool | `false` | No |

## `start`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `START_TIME` | float | `PydanticUndefined` | No |

## `stripe`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `STRIPE_API_KEY` | str | `-` | Yes |
| `STRIPE_PAYMENT_ENABLED` | bool | `false` | No |
| `STRIPE_SECRET_KEY` | str | `-` | Yes |
| `STRIPE_WEBHOOK_SECRET` | str | `-` | Yes |

## `tempo`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `TEMPO_ENDPOINT` | str | `http://localhost:4317` | No |

## `test`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `TEST_TOOLS_ENABLED` | bool | `false` | No |

## `together`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `TOGETHER_API_KEY` | str | `-` | Yes |
| `TOGETHER_PROVIDER_ENABLED` | bool | `true` | No |

## `token`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `TOKEN_COUNTING_FALLBACK_ALLOWED` | bool | <redacted> | Yes |
| `TOKEN_COUNTING_REAL_ENABLED` | bool | <redacted> | Yes |

## `tokenizer`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `TOKENIZER_CACHE_ENABLED` | bool | <redacted> | Yes |
| `TOKENIZER_MODE` | str | <redacted> | Yes |
| `TOKENIZER_MODEL_PATH` | str | None | `-` | Yes |
| `TOKENIZER_STRICT` | bool | <redacted> | Yes |

## `tool`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `TOOL_ARGUMENT_PREVIEW_CHARS` | int | `160` | No |

## `tts`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `TTS_ENABLED` | bool | `true` | No |

## `vault`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `VAULT_ADDR` | str | `http://localhost:8200` | No |
| `VAULT_KV_MOUNT` | str | `secret` | No |
| `VAULT_TOKEN` | str | `-` | Yes |

## `vector`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `VECTOR_DB_PROVIDER` | str | `pgvector` | No |

## `vision`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `VISION_INPUT_ENABLED` | bool | `false` | No |

## `vllm`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `VLLM_API_KEY` | str | `-` | Yes |
| `VLLM_BACKEND_ENABLED` | bool | `false` | No |
| `VLLM_BASE_URL` | str | `http://localhost:8000/v1` | No |
| `VLLM_DEFAULT_MODEL` | str | `facebook/opt-125m` | No |
| `VLLM_MAX_CONCURRENT_REQUESTS` | int | `16` | No |
| `VLLM_OPENAI_COMPAT_ENABLED` | bool | `false` | No |
| `VLLM_TIMEOUT_SECONDS` | int | `120` | No |

## `voice`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `VOICE_AGENT_ENABLED` | bool | `false` | No |
| `VOICE_STT_STREAMING_ENABLED` | bool | `false` | No |
| `VOICE_TTS_STREAMING_ENABLED` | bool | `false` | No |

## `wandb`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `WANDB_INTEGRATION_ENABLED` | bool | `false` | No |

## `weaviate`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `WEAVIATE_API_KEY` | str | None | `-` | Yes |
| `WEAVIATE_ENABLED` | bool | `false` | No |
| `WEAVIATE_URL` | str | `http://localhost:8080` | No |

## `web`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `WEB_IDE_ENABLED` | bool | `false` | No |
| `WEB_IDE_WORKSPACES_DIR` | str | `./data/ide_workspaces` | No |

## `webrtc`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `WEBRTC_AUDIO_ENABLED` | bool | `false` | No |
| `WEBRTC_VOICE_ENABLED` | bool | `false` | No |

## `xai`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `XAI_API_KEY` | str | `-` | Yes |
| `XAI_PROVIDER_ENABLED` | bool | `true` | No |

## `zipkin`

| Env Var | Type | Default | Secret |
| --- | --- | --- | --- |
| `ZIPKIN_EXPORT_ENABLED` | bool | `false` | No |
