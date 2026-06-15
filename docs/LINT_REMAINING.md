# Remaining Lint Violations Report (LINT_REMAINING.md)

This document outlines the remaining lint violations in the codebase, categorized by category, priority, and rule. These violations require manual review and correction.

## Summary of Violations

| Rule Code | Category | Priority | Description | Count |
|---|---|---|---|---|
| `E722` | Safety / Security | **High** | do not use bare `except` | 9 |
| `B023` | Safety / Security | **High** | function closure uses loop variable | 2 |
| `B030` | Safety / Security | **High** | except handlers must catch BaseException-derived classes | 2 |
| `F821` | Safety / Security | **High** | undefined name | 1 |
| `F811` | Safety / Security | **High** | redefined-while-unused | 1 |
| `F841` | Maintainability | **Low** | local variable assigned but never used | 188 |
| `SIM105` | Maintainability | **Low** | use contextlib.suppress instead of try-except-pass | 79 |
| `B007` | Maintainability | **Low** | loop control variable not used within loop body | 74 |
| `B011` | Maintainability | **Low** | do not assert False | 59 |
| `ARG005` | Maintainability | **Low** | unused lambda argument | 40 |
| `E741` | Maintainability | **Low** | ambiguous variable name | 26 |
| `SIM115` | Maintainability | **Low** | use a context manager for opening files | 25 |
| `B905` | Maintainability | **Low** | `zip()` without an explicit `strict=` parameter | 21 |
| `SIM103` | Maintainability | **Low** | needless boolean control flow | 21 |
| `N806` | Maintainability | **Low** | variable name in function should be lowercase | 19 |
| `SIM108` | Maintainability | **Low** | use ternary operator instead of if-else | 17 |
| `ARG004` | Maintainability | **Low** | unused static method argument | 15 |
| `N818` | Maintainability | **Low** | exception name should end with Error | 15 |
| `W293` | Maintainability | **Low** | blank line contains whitespace | 13 |
| `SIM110` | Maintainability | **Low** | reimplemented builtin `any` or `all` | 12 |
| `N801` | Maintainability | **Low** | class name should use CapWords convention | 11 |
| `B017` | Maintainability | **Low** | asserting on too broad/blind exceptions | 9 |
| `ARG003` | Maintainability | **Low** | unused class method argument | 5 |
| `B006` | Maintainability | **Low** | do not use mutable data structures for argument defaults | 4 |
| `W291` | Maintainability | **Low** | trailing whitespace | 4 |
| `SIM118` | Maintainability | **Low** | use key in dict instead of key in dict.keys() | 4 |
| `SIM201` | Maintainability | **Low** | negate-equal-op | 3 |
| `SIM116` | Maintainability | **Low** | if-else block instead of dictionary lookup | 2 |
| `SIM212` | Maintainability | **Low** | if-expr-with-twisted-arms | 2 |
| `SIM211` | Maintainability | **Low** | if-expr-with-false-true | 2 |
| `E731` | Maintainability | **Low** | do not assign a lambda expression, use a def | 1 |
| `SIM210` | Maintainability | **Low** | if-expr-with-true-false | 1 |
| `SIM113` | Maintainability | **Low** | use enumerate in for loop | 1 |
| `SIM222` | Maintainability | **Low** | expression or True | 1 |
| `SIM109` | Maintainability | **Low** | compare with tuple | 1 |
| `invalid-syntax` | Other | **Low** | Unknown rule | 1 |
| `E402` | Imports | **Medium** | module level import not at top of file | 161 |
| `F401` | Imports | **Medium** | unused import | 66 |
| `F403` | Imports | **Medium** | star imports used | 9 |
| `UP035` | Imports | **Medium** | deprecated import | 2 |
| `E712` | Typing | **Medium** | comparison to True/False should be `cond` or `not cond` | 130 |
| `UP042` | Typing | **Medium** | replace-str-enum | 52 |
| `E711` | Typing | **Medium** | comparison to None should be `cond is None` | 12 |
| `UP045` | Typing | **Medium** | non-pep604-annotation-optional | 1 |

---

## Detailed Rules & Affected Files

### 1. High Priority (Safety & Security)

#### `E722`: do not use bare `except` (9 occurrences)

- [ ] `/home/kleber/llm-inference-stack/scripts/dev/benchmark_runner.py:50`
- [ ] `/home/kleber/llm-inference-stack/scripts/validators/audit-feature-flags.py:48`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_agent_deterministic_executor.py:41`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_agent_policy_enforcement.py:40`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_agent_promotion_gates.py:39`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_agent_runtime_determinism_phases.py:47`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_agent_tool_governance.py:33`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_agent_worker_operability.py:50`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_agentic_readiness_honest.py:43`

#### `B023`: function closure uses loop variable (2 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/tool_executor.py:253`
- [ ] `/home/kleber/llm-inference-stack/scripts/llm_harness/plugins/__init__.py:164`

#### `B030`: except handlers must catch BaseException-derived classes (2 occurrences)

- [ ] `/home/kleber/llm-inference-stack/scripts/llm_harness/utils/retry.py:24`
- [ ] `/home/kleber/llm-inference-stack/scripts/llm_harness/utils/retry.py:26`

#### `F821`: undefined name (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/scripts/dev/agentctl_pkg/main.py:97`

#### `F811`: redefined-while-unused (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_admin_billing_margins_api.py:59`

### 2. Medium Priority (Imports & Typing)

#### `E402`: module level import not at top of file (161 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_inference.py:54`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_metrics.py:108`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_compliance_admin.py:557`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_crypto_admin.py:19`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_global_routing_admin.py:110`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_global_routing_admin.py:111`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_global_routing_admin.py:113`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_global_routing_admin.py:114`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_global_routing_admin.py:115`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_global_routing_admin.py:116`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_qos_admin.py:226`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_qos_admin.py:227`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_qos_admin.py:228`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_qos_admin.py:229`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_qos_admin.py:230`
- ... and 146 more occurrences.

#### `F401`: unused import (66 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:2`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:10`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:11`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:14`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:15`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:16`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:17`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:2`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:3`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:4`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:5`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:8`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/governance/__init__.py:9`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/events/adapters/nats_adapter.py:13`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/events/adapters/rabbitmq_adapter.py:13`
- ... and 48 more occurrences.

#### `F403`: star imports used (9 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:1`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:10`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:3`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:4`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:5`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:6`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:7`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:8`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/__init__.py:9`

#### `UP035`: deprecated import (2 occurrences)

- [ ] `/home/kleber/llm-inference-stack/scripts/llm_harness/plugins/__init__.py:8`

#### `E712`: comparison to True/False should be `cond` or `not cond` (130 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_metrics.py:118`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_tests.py:278`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/agent_studio_admin.py:110`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/agent_studio_admin.py:126`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/agent_studio_admin.py:142`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/agent_studio_admin.py:177`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/agent_studio_admin.py:94`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/auth.py:100`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/auth.py:221`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/hybrid_admin.py:356`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/hybrid_admin.py:363`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/hybrid_admin.py:490`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/hybrid_admin.py:504`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/hybrid_admin.py:87`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/hybrid_admin.py:91`
- ... and 115 more occurrences.

#### `UP042`: replace-str-enum (52 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/contracts/agents/base.py:10`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/agents/advanced_memory.py:12`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/agents/advanced_memory.py:22`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/commercial/commercial_crypto_trust.py:12`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/commercial/commercial_crypto_trust.py:19`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/commercial/commercial_crypto_trust.py:26`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/models/core/federation_mesh.py:13`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/schemas/compliance_evidence.py:16`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/schemas/compliance_evidence.py:46`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/schemas/compliance_evidence.py:9`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/schemas/performance.py:7`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/schemas/routing.py:11`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/schemas/routing.py:19`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/schemas/routing.py:27`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/a2a/a2a_protocol.py:19`
- ... and 37 more occurrences.

#### `E711`: comparison to None should be `cond is None` (12 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_catalog.py:136`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/mcp/mcp_delegated_identity.py:29`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/mcp/mcp_token_exchange.py:84`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/tool_credentials.py:144`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/tool_credentials.py:147`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/inference/confidential_runtime.py:35`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/rag/rag_access_control.py:130`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/routing/commercial_capacity_forecasting.py:41`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/routing/commercial_capacity_monitor.py:155`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/routing/qos_chargeback.py:26`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/routing/qos_fairness.py:238`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/runtime/determinism_repair.py:65`

#### `UP045`: non-pep604-annotation-optional (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/performance_admin.py:88`

### 3. Low Priority (Style & Maintainability)

#### `F841`: local variable assigned but never used (188 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/a2a_router.py:40`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_backends.py:201`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_benchmarks.py:54`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_tests.py:592`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_tests.py:611`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/agent_canary_admin.py:38`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/agent_studio_ga_admin.py:154`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/collab_chat.py:208`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_execution_proofs_admin.py:207`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/commercial_revenue_forecasting_admin.py:37`
- ... and 178 more occurrences.

#### `SIM105`: use contextlib.suppress instead of try-except-pass (79 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_models.py:869`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/collab_chat.py:39`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/harness.py:201`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/harness.py:245`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/harness.py:322`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/harness.py:358`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/harness.py:499`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/harness.py:534`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/operations_admin.py:177`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/system.py:424`
- ... and 69 more occurrences.

#### `B007`: loop control variable not used within loop body (74 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/compat/crewai/adapters.py:65`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_graph/engine.py:395`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_llm_provider.py:422`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_worker.py:126`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/events/pubsub_triggers.py:49`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/knowledge_graph/providers/internal_sql_graph.py:422`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/multi_agent/hierarchical_runtime.py:91`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/reasoning/mcts/mcts_runtime.py:43`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/compliance_evidence_collector.py:92`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/enterprise_onboarding.py:59`
- ... and 58 more occurrences.

#### `B011`: do not assert False (59 occurrences)

- [ ] `/home/kleber/llm-inference-stack/tests/integration/llm_harness/test_property_hypothesis.py:65`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_capabilities_page.py:100`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_capabilities_page_security.py:37`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_clean_install_report.py:97`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_client_presentation_docs.py:194`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_client_ready_report_security.py:119`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_client_ready_report_security.py:34`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_client_ready_report_security.py:53`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_client_ready_report_security.py:68`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_commercial_demo_e2e_report.py:114`
- ... and 49 more occurrences.

#### `ARG005`: unused lambda argument (40 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_executor.py:127`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/mcp/mcp_server.py:15`
- [ ] `/home/kleber/llm-inference-stack/tests/api/test_harness_api.py:96`
- [ ] `/home/kleber/llm-inference-stack/tests/e2e/test_agent_executor_real_flow.py:246`
- [ ] `/home/kleber/llm-inference-stack/tests/e2e/test_agent_executor_real_flow.py:249`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/llm_harness/test_new_platform_features.py:209`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/llm_harness/test_new_platform_features.py:211`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/llm_harness/test_new_platform_features.py:212`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/llm_harness/test_stress_chaos.py:132`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/security/test_code_interpreter_hardening.py:71`
- ... and 18 more occurrences.

#### `E741`: ambiguous variable name (26 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/domains/audit/repositories.py:72`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/domains/audit/repositories.py:82`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_trace_correlation.py:61`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/inference/execution_proofs.py:292`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/operations/correlation/trust_graph.py:113`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/operations/correlation/trust_graph.py:127`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/runtime/hardware_detection.py:79`
- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:375`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_operational_trust_graph.py:42`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_operational_trust_graph.py:45`
- ... and 16 more occurrences.

#### `SIM115`: use a context manager for opening files (25 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/backup/restore_lock_service.py:71`
- [ ] `/home/kleber/llm-inference-stack/scripts/validators/platform-freeze-check.py:137`
- [ ] `/home/kleber/llm-inference-stack/scripts/validators/platform-freeze-check.py:169`
- [ ] `/home/kleber/llm-inference-stack/scripts/validators/platform-freeze-check.py:176`
- [ ] `/home/kleber/llm-inference-stack/scripts/validators/platform-freeze-check.py:214`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_attestation_dashboard.py:2`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_attestation_dashboard.py:3`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_attestation_framework_models.py:99`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_compatibility_dashboard.py:2`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_compatibility_dashboard.py:3`
- ... and 15 more occurrences.

#### `B905`: `zip()` without an explicit `strict=` parameter (21 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_backends.py:148`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_metrics.py:133`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/system.py:641`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/memory/mock_memory_store.py:72`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/memory/pgvector_memory_store.py:130`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/memory/redis_memory_store.py:76`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/memory_indexing.py:22`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/memory_retriever.py:124`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/workflows/workflow_dag.py:172`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/workflows/workflow_dag.py:193`
- ... and 11 more occurrences.

#### `SIM103`: needless boolean control flow (21 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/core/logging.py:31`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_evaluation_framework.py:534`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/multi_agent/governance_policy.py:67`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/planning/step_cache.py:136`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/rate_limits/redis_rate_limiter.py:115`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/rate_limits/redis_rate_limiter.py:189`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/tool_synthesis/sandbox_policy.py:10`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/backup/restore_lock_service.py:32`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/governance/data_residency.py:27`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/inference/agent_governance.py:123`
- ... and 11 more occurrences.

#### `N806`: variable name in function should be lowercase (19 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/system.py:713`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/human_approval.py:128`
- [ ] `/home/kleber/llm-inference-stack/examples/client_sdk_demo.py:14`
- [ ] `/home/kleber/llm-inference-stack/examples/client_sdk_demo.py:15`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_control_plane_mesh.py:12`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_mesh_consensus.py:13`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_mesh_failover.py:13`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_mesh_replication.py:13`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_health_ready_metrics.py:34`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_admin_lab.py:14`
- ... and 9 more occurrences.

#### `SIM108`: use ternary operator instead of if-else (17 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/sales.py:249`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/optimization/ab_testing.py:28`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/tools/web_search_tool.py:132`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/pricing_engine.py:216`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/rag/retrieval_proofs.py:49`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/routing/commercial_global_router.py:104`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/routing/commercial_global_router.py:120`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/tokenizer_service.py:248`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/tokenizer_service.py:277`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/tts_usage.py:15`
- ... and 7 more occurrences.

#### `ARG004`: unused static method argument (15 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/code_interpreter/sandbox_attestation.py:28`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/connectors/credentials.py:16`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/connectors/credentials.py:45`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/reasoning/structured_output.py:18`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/workspace/artifact_permissions.py:14`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/workspace/artifact_versioning.py:24`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/approval_service.py:232`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/payments/invoice_payment.py:75`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/payments/invoice_payment.py:76`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/payments/payment_reconciliation.py:12`
- ... and 2 more occurrences.

#### `N818`: exception name should end with Error (15 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/code_interpreter/sandbox_policy.py:64`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/tool_synthesis/generated_tool_validator.py:4`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/wallet_service.py:13`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/wallet_service.py:17`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/wallet_service.py:21`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/wallet_service.py:25`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/circuit_breaker.py:8`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/queue_manager.py:17`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/queue_manager.py:23`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/quota.py:9`
- ... and 5 more occurrences.

#### `W293`: blank line contains whitespace (13 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/developer_docs.py:155`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/developer_docs.py:158`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/developer_docs.py:160`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/developer_docs.py:166`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/developer_docs.py:174`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/platform/deployment_modes.py:277`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/rate_limit_service.py:32`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/rate_limit_service.py:35`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/rate_limit_service.py:37`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/rate_limit_service.py:40`
- ... and 3 more occurrences.

#### `SIM110`: reimplemented builtin `any` or `all` (12 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/contracts/queue.py:42`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_memory.py:82`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/memory_retriever.py:151`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/collab_chat/moderation_policy.py:15`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/mlops/evaluation_artifacts.py:20`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/notifications/notification_policy.py:32`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/security/attestation_challenges.py:159`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/security/offline_crl.py:225`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/utils/anti_loop.py:31`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_demo_visual_guide_security.py:32`
- ... and 2 more occurrences.

#### `N801`: class name should use CapWords convention (11 occurrences)

- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:117`
- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:210`
- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:302`
- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:344`
- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:386`
- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:59`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_phase_80_validation.py:28`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/operations/test_phase_81_validation.py:36`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/releases/test_profile_resolver.py:44`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_phase56_migration_postgres.py:30`
- ... and 1 more occurrences.

#### `B017`: asserting on too broad/blind exceptions (9 occurrences)

- [ ] `/home/kleber/llm-inference-stack/tests/backup_dr/test_dr_scenarios.py:149`
- [ ] `/home/kleber/llm-inference-stack/tests/chaos/test_chaos.py:69`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_prompt_template_engine.py:482`
- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_web_ide.py:87`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_agent_tools.py:164`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_enterprise_rag_chunking.py:155`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_enterprise_rag_security.py:108`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_queue_priority.py:82`
- [ ] `/home/kleber/llm-inference-stack/tests/unit/services/prompts/test_prompt_management.py:36`

#### `ARG003`: unused class method argument (5 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/payments/card_service.py:29`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/billing/payments/pix_service.py:29`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/notifications/notification_policy.py:48`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/notifications/push_provider.py:160`

#### `B006`: do not use mutable data structures for argument defaults (4 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/a2a_router.py:79`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/api/admin_tests.py:517`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/inference/agent_governance.py:23`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/inference/witness_federation.py:25`

#### `W291`: trailing whitespace (4 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/memory/pgvector_memory_store.py:79`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/vectorstores/pgvector_store.py:239`
- [ ] `/home/kleber/llm-inference-stack/scripts/dev/run_free_model.py:544`
- [ ] `/home/kleber/llm-inference-stack/scripts/dev/run_free_model.py:545`

#### `SIM118`: use key in dict instead of key in dict.keys() (4 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/runtime_profiles.py:77`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/utils/tool_calling.py:421`
- [ ] `/home/kleber/llm-inference-stack/scripts/llm_harness/mcp/client.py:213`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/llm_harness/test_provider_matrix.py:135`

#### `SIM201`: negate-equal-op (3 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/runtime_tuning.py:205`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_surface_consolidation.py:65`
- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_surface_consolidation.py:91`

#### `SIM116`: if-else block instead of dictionary lookup (2 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/meta_reviewer/reviewer_decision_engine.py:20`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/workflows/workflow_branching.py:54`

#### `SIM212`: if-expr-with-twisted-arms (2 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/inference/receipt_verification.py:133`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/runtime/real_execution_readiness.py:267`

#### `SIM211`: if-expr-with-false-true (2 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/sandbox/service.py:66`
- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/sandbox/service.py:67`

#### `E731`: do not assign a lambda expression, use a def (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/agents/agent_executor.py:127`

#### `SIM210`: if-expr-with-true-false (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/operations/plugin_supply_chain/sbom_service.py:326`

#### `SIM113`: use enumerate in for loop (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/control_plane/app/services/rag_enterprise/parsers.py:168`

#### `SIM222`: expression or True (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/tests/control_plane/test_plugin_marketplace.py:291`

#### `SIM109`: compare with tuple (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/tests/integration/test_v1_7_release_metadata.py:36`

#### `invalid-syntax`: Unknown rule (1 occurrences)

- [ ] `/home/kleber/llm-inference-stack/scripts/security_audit_v2.py:273`
