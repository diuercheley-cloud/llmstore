# Working Tree Audit

| path | status | classification | reason | recommended_action | risk |
|---|---|---|---|---|---|
| HANGELOG.md | M  | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| Makefile |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| config/feature-flags.yaml |  M | release_delta | Explicitly requested release file | should_commit | low |
| config/platform-freeze-rules.json |  M | release_delta | Explicitly requested release file | should_commit | low |
| control_plane/app/api/agent_execution_admin.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/api/agent_worker_admin.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/api/client.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/core/config.py |  M | release_delta | Explicitly requested release file | should_commit | low |
| control_plane/app/main.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/models/__init__.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/models/agents.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/agent_cancellation.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/agent_execution_plane.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/agent_llm_provider.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/agent_runtime.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/code_interpreter/providers/firecracker_sandbox.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/code_interpreter/sandbox_policy.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/audit.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/base.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/confluence_connector.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/github_connector.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/http_client.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/jira_connector.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/microsoft365_connector.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/salesforce_connector.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/connectors/slack_connector.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/agents/memory_indexing.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/inference_proxy.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/quota.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/services/tokenizer_service.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| docs/agents/code-interpreter-production.md |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| docs/cli/agentctl.md |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| operator/main.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| scripts/agentctl.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| tests/conftest.py |  M | valid_existing_change | Pre-existing work outside release delta | unknown_requires_user_review | low |
| control_plane/app/api/agent_a2a.py | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| control_plane/app/api/agents_ws.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/api/assistants_v1.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/api/batches_v1.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/api/billing_payments.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/models/assistants.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/models/batches.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/models/payments.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/agents/a2a/a2a_client.py | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| control_plane/app/services/agents/a2a/a2a_messages.py | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| control_plane/app/services/agents/a2a/a2a_registry.py | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| control_plane/app/services/agents/a2a/a2a_security.py | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| control_plane/app/services/agents/a2a/a2a_server.py | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| control_plane/app/services/agents/memory/chroma_memory_store.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/agents/memory/mock_memory_store.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/agents/memory/pgvector_memory_store.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/agents/memory/semantic_memory_retriever.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/agents/memory/vector_store.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/agents/streaming/run_event_stream.py | ?? | release_delta | Matches release keyword: streaming | should_commit | low |
| control_plane/app/services/agents/streaming/stream_auth.py | ?? | release_delta | Matches release keyword: streaming | should_commit | low |
| control_plane/app/services/agents/streaming/websocket_manager.py | ?? | release_delta | Matches release keyword: streaming | should_commit | low |
| control_plane/app/services/agents/tracing.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/assistants/assistant_registry.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/assistants/assistant_run_adapter.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/assistants/message_store.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/assistants/thread_store.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/batches/batch_registry.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/batches/batch_result_store.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/batches/batch_scheduler.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/batches/redis_queue.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/billing/payments/invoice_payment.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/billing/payments/mock_payment_provider.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/billing/payments/payment_provider.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/billing/payments/payment_webhooks.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/billing/payments/stripe_payment_provider.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/plugins/dev_kit.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/token_counting/__init__.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/token_counting/anthropic_token_counter.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/token_counting/fallback_token_counter.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/token_counting/llama_token_counter.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/token_counting/openai_token_counter.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| control_plane/app/services/token_counting/token_counter.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/agents/a2a-protocol.md | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| docs/agents/connectors-production.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/agents/semantic-memory-retrieval.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/api/agent-websocket-streaming.md | ?? | release_delta | Matches release keyword: streaming | should_commit | low |
| docs/api/assistants-compat.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/api/batch-api.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/billing/payment-processing.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/billing/token-counting.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/developers/portal.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/operations/agentic-scale.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/plugins/dev-kit.md | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| docs/releases/V2_X_AGENTIC_PLATFORM_GAP_CLOSURE.md | ?? | release_delta | Explicitly requested release file | should_commit | low |
| examples/agents/support-triage/agent.yaml | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| examples/plugins/safe-tool/plugin.json | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| frontend/admin/src/pages/developers/DeveloperPortal.tsx | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| scripts/load-test-agentic.sh | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/e2e/test_agent_a2a_protocol.py | ?? | release_delta | Matches release keyword: a2a | should_commit | low |
| tests/e2e/test_agent_executor_real_flow.py | ?? | release_delta | Matches release keyword: e2e/test_agent_executor | should_commit | low |
| tests/e2e/test_agent_websocket_streaming.py | ?? | release_delta | Matches release keyword: streaming | should_commit | low |
| tests/e2e/test_payment_processing.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/e2e/test_token_counting.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/load/test_agentic_scale.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/test_agent_cancellation.py | ?? | release_delta | Explicitly requested release file | should_commit | low |
| tests/test_assistants_v1.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/test_batches_v1.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/test_connector_mock_execution.py | ?? | release_delta | Explicitly requested release file | should_commit | low |
| tests/test_connectors_production.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/test_developer_experience.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/test_distributed_maturity.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/test_sandbox_final.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
| tests/test_semantic_memory_final.py | ?? | valid_existing_change | Pre-existing work outside release delta | should_keep_untracked_local | low |
