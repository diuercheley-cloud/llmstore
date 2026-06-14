<!-- synced_from: docs/PRODUCT_SURFACE.md -->

> Source of truth: `docs/PRODUCT_SURFACE.md`

---
owner: platform-ops
status: reference-generated
generated_from:
  - config/supported-surface.yaml
generated_by: scripts/docs/generate_reference_docs.py
---

# Product Surface

This document is generated from `config/supported-surface.yaml`. It is the documentation source of truth for capability status claims.

## Lifecycle Tiers

| Tier | Definition |
| --- | --- |
| production_core | No mock in critical path. Enabled by default or production-gated. Readiness required. |
| production_optional | Production-quality but opt-in. Mock-safe defaults. Gated behind feature flags. |
| beta | Feature-complete but evolving API/behavior. Not recommended for production without evaluation. |
| experimental | Early stage. Heavy mock usage. Limited testing. May change without notice. |
| internal | Internal tools only. Not customer-facing. |
| deprecated | No longer maintained. Will be removed in future releases. |
| advisory | Implemented as advisory-only posture; not a production claim. |
| non-production | Available for development or transition use only; not a supported production posture. |

## Status Summary

| Status | Capabilities |
| --- | --- |
| beta | 47 |
| experimental | 6 |
| deprecated | 1 |
| advisory | 1 |
| internal | 2 |
| non-production | 2 |
| production_core | 18 |
| production_optional | 13 |

## Capability Matrix

| Capability | ID | Status | Support | Owner | Surface | Docs | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Advanced cognitive memory | cognitive-memory | beta | pilot | agent-platform | `AGENT_COGNITIVE_MEMORY_ENABLED` | `agents/cognitive-memory.md` | No mock in service path. Memory summarization is advisory by default. Limited dedicated test coverage. |
| Agent admin UI | agent-admin-ui | beta | pilot | agent-platform | - | `agents/admin-ui.md` | Operator-facing UI. Must not be used to imply unrestricted agent autonomy. |
| Agent auto-optimization | agent-auto-optimization | beta | pilot | agent-platform | `/admin/agents/optimization` / `agent_auto_optimization_enabled` | `agents/auto-optimization.md` | Candidate generation and evaluation supported under governance. Automatic apply disabled by default. |
| Agent auto-optimization (advisory) | agent-optimizer | beta | pilot | agent-platform | `/admin/agents` / `AGENT_OPTIMIZER_ENABLED` | `agents/optimizer-tournaments.md` | Optimization is advisory by default. Tournaments support parallel evaluation but winner application stays disabled until explicitly enabled. |
| Agent code interpreter | agent-code-interpreter | beta | pilot | agent-platform | `/admin/agents/sandbox` / `agent_code_interpreter_enabled` | `agents/code-interpreter.md` | MockSandboxProvider is the default. Real providers (Docker, Firecracker, gVisor, Wasm) are opt-in. Network and filesystem writes disabled by default. |
| Agent connector OAuth | agent-connector-oauth | beta | pilot | agent-platform | `/admin/agents/connectors` / `agent_connector_oauth_enabled` | `agents/connector-oauth.md` | OAuth bootstrap and token persistence disabled by default. Gated behind flag. |
| Agent context compression | agent-context-compression | beta | pilot | agent-platform | `agent_context_compression_enabled` | `agents/context-compression.md` | Compression has inline mock summary for development. Disabled by default. |
| Agent debugger | agent-debugger | beta | pilot | agent-platform | `/admin/agents/studio/debug` | `agents/agent-studio.md` | Interactive debugging disabled by default. Gated behind flag. |
| Agent enterprise observability | agent-enterprise-observability | beta | pilot | agent-platform | `agent_enterprise_observability_enabled` | `platform/deployment-modes.md` | Enhanced enterprise observability is only part of enterprise managed mode. |
| Agent evals | agent-evals | beta | pilot | agent-platform | `/admin/agent-evals` / `agent_evals_enabled` | `agents/eval-gates.md` | Heavy mock usage — MockEvalProvider is the default. Real provider is opt-in. Mock cannot count as production evidence for promotion. |
| Agent execution plane | agent-execution-plane | beta | pilot | agent-platform | `AGENT_EXECUTION_PLANE_ENABLED` | `runtime/agentic-durable-queue.md` | Durable queue, lease recovery, scheduler safety supported. Production posture requires readiness gate approval. |
| Agent knowledge graph | agent-knowledge-graph | beta | pilot | graph-team | `/admin/agents/knowledge-graph` / `agent_knowledge_graph_enabled` | `agents/knowledge-graph.md` | Explicit mock mode flag (agent_kg_mock_mode) is test-only. Real pathfinding is implemented through internal SQL today; external providers and Postgres acceleration remain opt-in and beta. |
| Agent multi-agent topologies | agent-multi-agent-topologies | beta | pilot | agent-platform | `/admin/agents/teams` / `agent_multi_agent_enabled` | `agents/multi-agent-ga-readiness.md` | Hierarchical and debate topologies are now beta with formal governance. Arbitration produces receipts. Loop detection is active. |
| Agent ReAct loop | agent-react-loop | beta | pilot | agent-platform | `agent_react_loop_enabled` | `agents/reasoning-loop.md` | Iterative reasoning/acting disabled by default. Gated behind flag. |
| Agent real connectors | agent-real-connectors | beta | pilot | agent-platform | `AGENT_CONNECTOR_MODE` | `agents/connectors-real-mode.md` | Real SaaS side effects require per-connector enablement. No fallback from failed real calls to mock payloads. |
| Agent semantic fallback | agent-semantic-fallback | beta | pilot | agent-platform | `agent_semantic_model_fallback_enabled` | `agents/model-fallback.md` | Fallback disabled until explicitly allowed. Gated behind flag. |
| Agent Shadow & Canary Deployment | agent-shadow-canary | beta | pilot | agent-platform | `AGENT_CANARY_AGENTS_ENABLED` | `agents/shadow-mode.md` | Shadow runs block destructive tools. Canary traffic splitting is random-sampled. |
| Agent shared artifacts | agent-shared-artifacts | beta | pilot | agent-platform | `/admin/agents/workspaces` / `agent_shared_workspace_enabled` | `agents/shared-artifacts.md` | Shared collaboration disabled by default. Artifacts are tenant-scoped. Concurrency uses version checks plus explicit locks. |
| Agent SLO enforcement | agent-slo-enforcement | beta | pilot | agent-platform | `agent_slo_enforcement_enabled` | `platform/deployment-modes.md` | SLO enforcement is operator control. Only meaningful after runtime activation. |
| Agent structured output repair | agent-structured-output-repair | beta | pilot | agent-platform | `agent_structured_output_retry_enabled` | `agents/reasoning-loop.md` | Repair uses MagicMock in test imports. Disabled by default. |
| Agent Studio and approval portal | agent-studio-approvals | beta | pilot | agent-platform | `AGENT_STUDIO_ENABLED` | `agents/agent-studio.md` | Visual DAG builder runs client-side. Execution bound to control plane validation rules. |
| Agent Studio GA Flow Lifecycle | agent-studio-ga | beta | pilot | agent-platform | `/admin/agents/studio` / `AGENT_STUDIO_GA_ENABLED` | `agents/agent-studio-ga.md` | Authoring, validation, compilation, and dry-run are operator-only and disabled by default. |
| Agent Time-Travel Debugger | agent-time-travel-debugger | beta | pilot | agent-platform | `AGENT_TIME_TRAVEL_DEBUGGER_ENABLED` | `agents/time-travel-debugger.md` | Snapshots capture state at step level. CoT is masked. Original runs remain immutable. |
| Agent tool synthesis | agent-tool-synthesis | beta | pilot | agent-platform | `/admin/agents/tool-synthesis` / `agent_tool_synthesis_enabled` | `agents/tool-synthesis.md` | Generated tools disabled by default. Approval required before public execution. Dynamic execution stays blocked unless explicitly enabled. |
| Agent visual builder | agent-visual-builder | beta | pilot | agent-platform | `/admin/agents/studio` / `agent_visual_builder_enabled` | `agents/agent-studio.md` | Graph authoring disabled by default. Gated behind flag. |
| Agent Wallets & Autonomous Budgets | agent-wallets | beta | pilot | agent-platform | `AGENT_WALLETS_ENABLED` | `agents/agent-wallets.md` | Internal ledger by default. External spend requires explicit opt-in. |
| Agent worker autoscaling | agent-worker-autoscaling | beta | pilot | agent-platform | `agent_worker_autoscaling_enabled` | `platform/deployment-modes.md` | Autoscaling is posture-dependent. Only supported in production and enterprise managed modes. |
| Agent workflow polling | agent-workflow-polling | beta | pilot | agent-platform | `/admin/agents/workflows` / `agent_workflow_polling_enabled` | `agents/workflow-polling.md` | Polling wake-up disabled until explicitly allowed. Inline mock responses exist in development path. |
| Agent workflow webhooks | agent-workflow-webhooks | beta | pilot | agent-platform | `/admin/agents/workflows` / `agent_workflow_webhooks_enabled` | `agents/workflow-webhooks.md` | Webhook wake-up disabled until operators explicitly enable inbound workflow callbacks. |
| Agentic RBAC | agent-rbac | beta | pilot | agent-platform | - | `agents/agentic-rbac.md` | Granular roles enforced at service level. Feature-complete but not yet production-validated across all deployment modes. |
| Cognitive Loopback | agent-cognitive-loopback | beta | pilot | agent-platform | `/admin/agents` / `AGENT_COGNITIVE_LOOPBACK_ENABLED` | `agents/cognitive-loopback.md` | Learning candidates remain draft-first. Auto-apply stays disabled by default and requires explicit human approval. |
| Compliance readiness | compliance-readiness | beta | pilot | compliance-team | - | `compliance/readiness-framework.md` | Self-attested advisory framework. Not a formal certification. |
| Deployment modes | deployment-modes | beta | pilot | platform-ops | - | `platform/deployment-modes.md` | Modes govern posture defaults. Readiness catches incoherent overrides. |
| Digital Twin Connectors & IoT | agent-digital-twins | beta | pilot | agent-platform | `AGENT_DIGITAL_TWINS_ENABLED` | `agents/digital-twins.md` | Read-only state by default. Actuation requires explicit opt-in and HITL. Safety interlocks active. |
| Distributed runtime | distributed-runtime | beta | pilot | platform-ops | `/admin/distributed-runtime` / `DISTRIBUTED_RUNTIME_ENABLED` | `runtime/distributed-agent-runtime.md` | Real node registration, heartbeat, placement, lease, and failover primitives exist. Production claims require environment validation and non-mock E2E evidence. |
| Epistemic Uncertainty Detection | agent-uncertainty-detection | beta | pilot | agent-platform | `/admin/agents` / `AGENT_UNCERTAINTY_DETECTION_ENABLED` | `agents/uncertainty-detection.md` | Confidence thresholds require calibration. Auto-research stays disabled by default. |
| Feature flag audit | feature-flag-audit | beta | pilot | platform-ops | - | `platform/feature-flag-governance.md` | Validates registry hygiene. Does not remove flags automatically unless cleanup mode is invoked. |
| Federated Memory & Sovereign Sync | agent-federated-memory | beta | pilot | agent-platform | `AGENT_FEDERATED_MEMORY_ENABLED` | `agents/federated-memory.md` | Sanitized summaries only by default. Raw sync requires sovereign trust. Data residency policies enforced. |
| Managed control-plane | managed-control-plane | beta | pilot | platform-ops | `MANAGED_CONTROL_PLANE_ENABLED` | `managed/managed-control-plane.md` | Supported only for metadata-safe synchronization and enterprise-managed posture. Prompt and document payload classes are out of scope. |
| MCP client/server | mcp-interoperability | beta | pilot | agent-platform | `/admin/agents/mcp` / `agent_mcp_enabled` | `agents/mcp-ga-readiness.md` | Requires explicit tool approval. Mock mode blocked in production. Tenant isolation enforced. |
| Meta-Reviewer | agent-meta-reviewer | beta | pilot | agent-platform | `AGENT_META_REVIEWER_ENABLED` | `agents/meta-reviewer.md` | Advisory-first by default. Blocking mode requires explicit operator enablement and policy tuning. |
| Multi-cluster | multi-cluster | beta | pilot | platform-ops | `MULTI_CLUSTER_ENABLED` | `multicluster` | Cluster inventory and status flows exist, but distributed production posture remains opt-in and release-gated. |
| Platform GA readiness | ga-readiness | beta | pilot | platform-ops | `/admin/platform` | `platform/ga-readiness.md` | Evidence-driven. Only as current as latest generated artifacts. |
| Provider validation | provider-validation | beta | pilot | agent-platform | `agent_real_provider_validation_enabled` | `evals/real-provider-validation.md` | Opt-in. Designed to run with synthetic data and constrained budgets. |
| Standardized Agent Bundle (SAB) | agent-sab-portability | beta | pilot | agent-platform | `AGENT_SAB_ENABLED` | `agents/standardized-agent-bundle.md` | Import creates draft definitions. Mandatory signature verification in production. |
| Surface audit | surface-audit | beta | pilot | platform-ops | - | `support/supported-surface-area.md` | Governance report, not runtime enforcement. |
| Tenant agentic readiness | tenant-agentic-readiness | beta | pilot | agent-platform | `/admin/tenants` / `agent_runtime_enabled` | `agents/tenant-readiness.md` | Operator-facing reports. Does not override global safe defaults or tenant isolation policy. |
| Agent debate teams | agent-debate-teams | experimental | development | agent-platform | `/admin/agents/teams` | `agents/debate-agents.md` | Debate topology disabled by default. Mock arbitration path. Limited testing. |
| Agent hierarchical teams | agent-hierarchical-teams | experimental | development | agent-platform | `/admin/agents/teams` | `agents/hierarchical-agents.md` | Hierarchical delegation disabled by default. Limited testing. |
| Agent multi-agent governance | agent-multi-agent-governance | experimental | development | agent-platform | `agent_multi_agent_enabled` | `agents/multi-agent-runtime.md` | Delegation and shared-memory governance are implemented, but runtime remains experimental. Real arbitration requires critic review; mock arbitration is test-only and disabled by default. |
| Chaos engineering | chaos-engineering | experimental | development | qa-team | - | `chaos` | Runs synthetic load drops and provider delays for testing. Experimental tooling. |
| Constraint-Based Reasoning | agent-constraint-reasoning | experimental | development | agent-platform | `AGENT_CONSTRAINT_REASONING_ENABLED` | `agents/constraint-reasoning.md` | Requires formal solvers for proofing. Fallback to rule-based validation if solvers are disabled. |
| MCTS Reasoning Runtime | agent-mcts-reasoning | experimental | development | agent-platform | `AGENT_MCTS_REASONING_ENABLED` | `agents/mcts-reasoning.md` | Computationally expensive. Requires simulation sandbox for high-fidelity. |
| Marketplace (legacy) | marketplace | deprecated | none | product-team | `PLUGIN_MARKETPLACE_ENABLED` | `plugins` | No real plugins marketplace active. Replaced by agent-marketplace (beta). Will be removed. |
| Hardware trust | hardware-trust | advisory | advisory | security-team | `hardware_trust_enabled` | `CRYPTOGRAPHIC_TRUST_INFRASTRUCTURE.md` | Advisory local validation only. Not hardware root of trust. |
| CI/CD | ci-cd | internal | production | infra-team | - | `ci` | Internal pipeline orchestrations. |
| Support bundle | support-bundle | internal | production | platform-ops | `/admin/support` | `support/support-bundle.md` | Operator-only diagnostic surface; bundles must stay sanitized. |
| GPU orchestration | gpu-orchestration | non-production | non-production | cloud-team | `GPU_AUTOSCALING_ENABLED` | `HARDWARE_ATTESTATION_RUNTIME.md` | Advisory-first recommendation only. Will be removed. |
| Kubernetes | kubernetes | non-production | non-production | cloud-team | `KUBERNETES_MODE` | `kubernetes` | Minimal operator reconciliation for Deployments, Services, provider secret references, and status conditions. Advanced fleet orchestration out of scope. |
| Admin RBAC | admin-rbac | production_core | production | security-team | `rbac_admin_enabled` | `admin-tests.md` | Role assignments are static and config-defined. |
| Agent human approval | agent-hitl | production_core | production | agent-platform | `/admin/agent-approvals` / `agent_human_approval_enabled` | `agents/human-in-the-loop.md` | Enabled by default. Raw prompts are not shown to reviewers. Approval portal UI is opt-in. |
| Agent marketplace | agent-marketplace | production_core | production | agent-platform | `/admin/agent-marketplace` / `agent_marketplace_enabled` | `security/capability-signing-policy.md` | Mandatory cryptographic signing for all external packages. Internal packages require signing in production. |
| Agent memory | agent-memory | production_core | production | platform-ops | `/admin/agent-memory` / `agent_memory_enabled` | `compliance/right-to-be-forgotten.md` | Full support for Right to be Forgotten (RTBF) via explicit erasure and tombstones. |
| Agent observability | agent-observability | production_core | production | platform-ops | `/admin/agents/observability` / `agent_observability_enabled` | `agents/agentic-observability.md` | Enabled by default. Metrics and traces are sanitized; external export is opt-in. |
| Agent readiness | agent-readiness | production_core | production | agent-platform | `/admin/readiness` / `agent_runtime_enabled` | `agents/agentic-readiness.md` | Readiness is advisory while runtime is disabled, blocking once runtime is enabled. No mock in check path. |
| Agent tool governance | agent-tool-governance | production_core | production | platform-ops | `/admin/agent-tools` / `agent_tool_registry_enabled` | `agents/tool-governance.md` | Tool registry gated behind flag. Adapters default to mock discovery. Destructive tools blocked without approval. No mock in governance or sandbox enforcement path. |
| Agent worker operations | agent-worker-operations | production_core | production | agent-platform | `/admin/agents/worker` / `agent_worker_enabled` | `agents/worker-operations.md` | Worker operations, DLQ inspection, retry tooling. No mock in service path. Gated behind feature flag. |
| Agentic runtime | agentic-runtime | production_core | production | runtime-ops | `/v1/agents` / `agent_runtime_enabled` | `agents/runtime-canonical-api.md` | Operational runtime gated behind opt-in flags. LLM provider defaults to mock in non-production configs. /v1/agents is canonical tenant API. Background execution requires explicit worker enablement. Test mocks exist but are not in production code path. |
| Attestation | attestation | production_core | production | security-team | `attestation_mode` | `HARDWARE_ATTESTATION_RUNTIME.md` | Advisory-first signature validation only. Not hardware root of trust. |
| Billing | billing | production_core | production | billing-team | - | `BILLING_BRL.md` | Manual billing and cycle enforcement only; webhook auto-chargeback is advisory. |
| Capability catalog | capability-catalog | production_core | production | platform-ops | `/admin/agents/capability-catalog` / `AGENT_CONNECTOR_CATALOG_ENABLED` | `agents/capability-catalog.md` | Operator-only catalog with draft/approval workflow. Installation and approval exist, but production support still depends on signature, sandbox, and test evidence. |
| Hot swap GGUF | hot-swap-gguf | production_core | production | model-team | - | `MODEL_BENCHMARK_LOCAL.md` | Requires local disk path and llama.cpp restart. |
| Multi-provider routing | multi-provider-routing | production_core | production | core-team | - | `PROVIDERS.md` | Supports local, LMStudio, OpenAI, Anthropic, DeepSeek, OpenRouter. |
| OpenAI-compatible API | openai-api | production_core | production | core-team | `/v1` | `OPENAI_COMPATIBILITY.md` | Supports chat completions, embeddings, tools/function calling, and models list; no fine-tuning or assistants endpoint. |
| PKI | pki | production_core | production | security-team | `pki_enabled` | `CRYPTOGRAPHIC_TRUST_INFRASTRUCTURE.md` | Local self-signed keys and verification only. Not a production CA. |
| RAG | rag | production_core | production | rag-team | - | `RAG.md` | Supports standard pdf, txt, md processing. Large context routing is experimental. |
| TTS | tts | production_core | production | audio-team | - | `CUSTOMER_QUICKSTART.md` | Single-speaker offline synthesis. |
| Agent A2A & Streaming | agent-a2a | production_optional | production | agent-team | `/agents` | `api/agent-websocket-streaming.md` | - |
| Agent code sandbox | agent-code-sandbox | production_optional | production | agent-platform | `AGENT_CODE_INTERPRETER_ENABLED` | `security/sandbox-ga-hardening.md` | Mock success is strictly blocked in production. Real gVisor/runsc or Firecracker required for GA hardening. |
| Agent event-driven runtime | agent-event-driven | production_optional | production | agent-platform | `/admin/agents/event-triggers` / `agent_event_driven_enabled` | `agents/event-driven-agents.md` | No mock in event path. Real event bus, cron, pubsub, webhook triggers. All gated behind flags. Rate limit, budget, dedup controls required for production operation. |
| Agent IAM | agent-iam | production_optional | production | platform-ops | `/admin/agents/iam` / `agent_iam_enabled` | `agents/service-principals.md` | Service principals and IAM audit are production-quality. Delegated tokens use mock issuance for development. Secrets never re-emitted after creation. Gated behind flag. |
| Agent OpenTelemetry tracing | agent-otel-tracing | production_optional | production | agent-platform | `AGENT_OTEL_TRACING_ENABLED` | `observability/agent-telemetry-backpressure.md` | No mock in tracing path. Real OTel semantic conventions, leaky-bucket backpressure, LangSmith and Phoenix exporters. Export is opt-in. Backpressure is enabled by default. |
| Agent planning | agent-planning | production_optional | production | agent-platform | `/admin/agent-tasks` / `agent_planning_enabled` | `agents/task-engine.md` | No mock in planning path. Task engine is production-quality. Task mock mode and dry-run mode exist for safe testing. Gated behind flag. |
| Agent reasoning loop | agent-reasoning-loop | production_optional | production | agent-platform | `agent_reasoning_loop_enabled` | `agents/reasoning-loop.md` | Context compressor has inline mock for development. Output repair uses MagicMock in tests. ReAct and plan-and-solve loops are real. Gated behind flags. |
| Agent Router V2 | agent-router-v2 | production_optional | production | agent-platform | `/admin/agents/routing` / `agentic_router_v2_enabled` | `agents/agentic-router-v2.md` | No mock in routing path. Per-step routing is opt-in. Cost optimization is optional. Gated behind flag. |
| Agent SaaS connectors | agent-saas-connectors | production_optional | production | platform-ops | `/admin/agents/connectors` / `agent_saas_connectors_enabled` | `agents/saas-connectors.md` | Every connector has full mock execution mode (default). Real mode requires per-connector enablement. Governance and audit are production-quality. Mock-friendly by design. |
| Agent stateful workflows | agent-stateful-workflows | production_optional | production | platform-ops | `/admin/agents/workflows` / `agent_stateful_workflows_enabled` | `agents/stateful-workflows.md` | State machine, signals, timers, webhooks, locks are production-quality. Polling has minor mock responses. Entire execution plane is opt-in. |
| Agent Studio | agent-studio | production_optional | production | agent-platform | `/admin/agents/studio` / `agent_studio_enabled` | `agents/agent-studio.md` | No mock in studio path. Visual builder and debugger are operator-facing. Gated behind flags. |
| Platform profiles | platform-profiles | production_optional | production | platform-ops | `PLATFORM_PROFILE` | `platform/platform-profiles.md` | Profiles are the supported operator contract. Per-flag overrides remain available but are not the preferred production posture. |
| Plugin runtime | plugin-runtime | production_optional | production | platform-ops | - | `plugins` | Plugin execution is local and sandboxed. Not a distributed plugin ecosystem. |
