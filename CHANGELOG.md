# Changelog

## [v2.x-agentic-production-trust-hardening] - 2026-05-29

### Added
- Real plugin runtime sandbox execution and signature verification.
- Cryptographic receipts verification API and public key export.
- Real visual observability timeline and error budget.
- Robust profile resolver with schema validation and conflict detection.
- Real production agentic E2E tests covering worker, memory, fake MCP, and rollback.
- Audit production placeholders script and clean-up of stubs.

## [v2.x-agentic-platform-complete-hardening] - 2026-05-29

### Added
- **Profile-driven platform posture**: platform profiles for `appliance`, `agentic-pilot`, `agentic-production`, and `enterprise-distributed` are now part of the release contract and governance surface.
- **Enterprise agentic control surfaces**: distributed fabric, capability catalog, plugin signature records, and managed control-plane metadata models/routes are now represented in release governance.
- **Release evidence pack**: `artifacts/releases/v2.x-agentic-platform-complete-hardening/` captures summary, validation, distributed runtime, sandbox, capability catalog, profile posture, E2E posture, and supported surface evidence.

### Changed
- **Supported surface is stricter and smaller**: distributed runtime, multi-cluster, managed control plane, production sandbox, and capability catalog are no longer treated as placeholders, but they remain opt-in and do not count as production core without passing non-mock gates.
- **Security posture is profile-first**: production guidance now points operators to `PLATFORM_PROFILE` instead of combinatorial flag assembly.
- **Production-claim policy is explicit**: code presence, mock-backed E2E, or initialization-only tests are not sufficient evidence for production marketing claims.

### Security
- **Metadata-safe control plane boundary**: managed control-plane posture is documented as metadata-only and rejects prompt/document payload classes.
- **Sandbox hardening remains fail-closed**: simulated providers are explicitly blocked when production sandbox controls require attestation or MicroVM isolation.

## [v2.x-agentic-production-maturity] - 2026-05-28

### Added
- **Production-on evidence path**: `make agentic-production-on-readiness` now delegates to the maintained Python validator, seeds the required eval tenant policies, and verifies runtime, worker, memory, KG, eval, receipts, and finalization without relying on dead admin endpoints.
- **Fail-closed multi-agent arbitration tests**: real arbitration now has explicit regression coverage for critic-review requirement, reviewer-provider failure, conflict handling, and consensus semantics.
- **Release evidence pack**: production maturity artifacts under `artifacts/releases/v2.x-agentic-production-maturity/` capture validation, supported surface, MCP, graph reasoning, eval provider modes, working-tree posture, and arbitration posture.

### Changed
- **Multi-agent arbitration is now fail-closed in real mode**: heuristic-only or silent fallback review paths are blocked unless mock arbitration is explicitly enabled for test posture.
- **Feature-flag governance is current**: eval, KG mock mode, MCP discovery, and multi-agent arbitration flags are now registered and classified against the supported surface.
- **Supported surface is more honest**: MCP and knowledge-graph capabilities now reference the real runtime flag names and document experimental/opt-in posture accurately.
- **Working-tree certification is stricter**: the release certification script now checks full `git status --porcelain`, emits a tag-scoped report, and no longer allows staged drift to pass as clean.
- **Supported-surface audit is non-mutating**: governance validation now fails on missing rollback metadata instead of rewriting the inventory during the check.

### Fixed
- **Agentic production-on shell wrapper**: no longer aborts on missing `KLEBER_API_KEY` due to `set -u` and no longer increments counters unsafely under `set -e`.
- **Production-on eval validation**: the validator now uses the actual eval service contract, checks pass/fail counts, and queries receipts by the correct `run_id` field.
- **Consensus detection**: identical multi-agent answers are no longer mislabeled as conflicts just because more than one candidate responded.

## [v2.x-agentic-consolidation-hardening] - 2026-05-28

### Added
- **Deterministic agentic-production validation**: the production profile validator now verifies the profile contract, dependency expectations, readiness topology, and live endpoints when available without claiming simulated success.
- **Continuous promotion hardening**: canary routing, rollback control, specialist routing, arbitration, and environment preflight services are now covered by release-scope tests and surface classification.
- **Release compatibility shims**: minimal governance and TTS readiness modules were restored to keep release validation green while the deprecated operational surface remains consolidated.

### Changed
- **Freeze and coverage gates now follow the release delta**: platform-freeze and service-coverage checks validate changed core services instead of failing on historical backlog outside the scope of this hardening line.
- **Real execution readiness is fail-closed but non-production aware**: worker-heartbeat store outages now degrade cleanly in appliance mode instead of crashing the gate.
- **Documentation consistency and release notes now recognize the `v2.x` release naming line.**

### Removed
- **Critical placeholder behavior**: simulated success paths in the production profile validator were removed in favor of deterministic offline or live checks.

## [v2.1.1-agentic-scale-hardening] - 2026-05-28

### Added
- **MicroVM sandbox providers**: Firecracker and gVisor providers, MicroVM policy enforcement, and sandbox attestation/readiness controls are now available as opt-in hardening paths for agent code execution.
- **MCP delegated identity**: OAuth client registry, delegated grant storage, token exchange, and MCP identity resolution now support tenant and user delegation flows with audit evidence.
- **Production GraphRAG acceleration**: Graph adjacency cache and PostgreSQL-backed graph retrieval with pgvector and pgRouting support are available behind explicit feature flags.
- **Optimizer tournaments**: Parallel tournament evaluation, pairwise scoring, winner approval, and rollback capture are now part of the governed optimization workflow.
- **Telemetry backpressure**: Leaky-bucket admission control and priority-based span shedding protect exporter paths during agent execution bursts.
- **Release evidence line**: `docs/releases/V2_1_1_AGENTIC_SCALE_HARDENING.md` and release artifacts formalize the scale-hardening criteria and validation flow.

### Changed
- **Safe defaults preserved for scale features**: Firecracker, gVisor, MCP OAuth token exchange, delegated user enforcement, external KG providers, PostgreSQL graph acceleration, optimizer winner application, and parallel evals remain opt-in.
- **Surface governance expanded**: `.env.example`, feature flags, supported surface, API surface, and script manifest now cover the scale-hardening controls exposed by the codebase.
- **Telemetry posture tightened**: backpressure remains enabled by default while strict export remains optional, preserving runtime liveness under load.

### Security
- **No privileged sandbox by default**: code interpreter continues to start on `mock` and cannot silently escalate into MicroVM providers.
- **No delegated identity without explicit enablement**: MCP token exchange is disabled until operators turn it on and provision grants.
- **No production GraphRAG provider by default**: PostgreSQL/pgvector/pgRouting remain disabled until operators explicitly provision the stack.

## [v2.1.0-agentic-platform-expansion] - 2026-05-28

### Added
- **Enterprise Code Sandbox (Code Interpreter)**: Secure Python code interpreter sandbox supporting Docker, mock, and WASM providers with resource limits (CPU/Memory/Time), syscall validation, and sanitization policies.
- **Knowledge Graph & GraphRAG**: Fully functional SQLite-backed internal graph store fallback (and Neo4j support), relation provenance, strict tenant boundaries, and GraphRAG vector/sub-graph retrieval.
- **Model Context Protocol (MCP)**: Client and server support for MCP. The client converts external MCP tools into local adapters, enforcing policy allowlists and attestation. The server exposes internal RAG/KG queries securely.
- **Advanced Cognitive Memory**: Working memory sessions, episodic memories, and semantic preferences/concepts with context-aware summarization and consent controls.
- **Agent Studio & Approval Portal**: React flows, visual nodes for memory/tools/policies, visual debugger panel, and multi-tenant approval gateway with risk sorting.
- **Internal Agent Marketplace**: Catalog of reusable, semver-tracked templates with installation reviews and automated trust reports.
- **Observability**: Sanitized GenAI-compatible OpenTelemetry spans mapping agent reasoning loops, step states, sandbox actions, and tool invocations.
- **Auto-Optimization**: Advisory eval-driven auto-optimization candidates (prompts, tool selection, policies) with rollback safety.
- **Comprehensive E2E Testing**: Validates jailbreaks, sandbox escapes, 10k entities graph performance, and multi-agent workflows.

## [v2.0.3-agentic-real-execution-hardening] - 2026-05-28

### Added
- **Real execution readiness gate**: `RealExecutionReadinessService` now checks durable queue posture, explicit executor modes, connector mode validity, operator mode, sandbox posture, worker heartbeats, and code-integrity blockers.
- **Release evidence line**: `docs/releases/V2_0_3_AGENTIC_REAL_EXECUTION_HARDENING.md` documents the hardening criteria, validation flow, and operator expectations for production-like autonomy.
- **Operator mode model**: Kubernetes reconciliation now recognizes `real`, `mock`, and `dry_run` modes explicitly.

### Changed
- **TaskEngine success path fixed**: task output validation now uses the contract layer instead of failing operationally after a successful side effect.
- **Tool execution is fail-closed**: real tool execution no longer emits implicit simulated output when no implementation is registered.
- **Sandbox fallback is explicit**: `execute_in_sandbox` only emits simulated output for explicit `mock` or `dry_run` mode; `real` requires a concrete callable.
- **Connector real mode is complete**: GitHub, Jira, Confluence, Microsoft 365, Salesforce, and Slack real paths no longer end in `NotImplementedError`, and Slack no longer downgrades failed real reads into mock payloads.
- **Connector responses are mode-tagged**: mock responses carry explicit mock metadata, while real responses remain clearly marked as real mode without synthetic downgrade flags.

### Security
- **No silent simulation in production-like paths**: executor, connector, sandbox, and operator flows now reject implicit mock behavior.
- **No placeholder real path in connectors**: unsupported real actions are reported explicitly as unsupported, not surfaced as unimplemented internals.
- **Queue-backed execution remains mandatory**: production-like readiness blocks when the durable execution plane is disabled.

## [v2.1.0-agentic-autonomy] - 2026-05-27

### Added
- **Governed code generation and execution**: Agent Tool Synthesis, generated-tool validation/approval, sandbox session inspection, and Code Interpreter execution are now part of the supported release line.
- **Graph-native RAG 2.0**: Knowledge Graph extraction/query APIs and Graph RAG controls are formalized for tenant-isolated retrieval augmentation.
- **Proactive agent runtime**: Event sources, triggers, subscriptions, webhook entrypoints, and delivery logs are added for governed event-driven execution.
- **Agent IAM**: Service principals, delegated token grants, token exchange, and IAM audit endpoints are documented as supported autonomy controls.
- **Agentic optimization workflow**: Optimization experiments, candidate evaluation, approval, and apply flows are now part of the platform surface.
- **Router 2.0 evidence**: Per-step capability catalog, routing policies, simulation, and auditable routing decision history are included in the release line.
- **Shared artifact collaboration**: Collaborative workspaces, artifact versioning, diffs, lock management, reviews, and event timelines are promoted into the supported surface.
- **Release evidence line**: `docs/releases/V2_1_0_AGENTIC_AUTONOMY.md` and release artifacts formalize the Enterprise Agentic Autonomy criteria.

### Changed
- **Safe defaults extended to autonomy features**: tool synthesis, code interpreter, dynamic generated-tool execution, graph writes, event-driven hooks, IAM, optimization apply, Router V2, and shared workspace/artifacts all remain opt-in.
- **Sandbox posture clarified**: code interpreter network and write access are disabled by default, preserving a governed local execution baseline.
- **Surface governance expanded**: supported surface, API surface, feature flags, and script manifest now explicitly cover the autonomy features required by the release.

### Security
- **No autonomous side effects by default**: connector network/write access and dynamic generated-tool execution remain blocked until explicitly enabled.
- **No silent optimization apply**: auto-promotion and candidate apply remain disabled unless separately turned on.
- **Tenant isolation preserved for graph and artifact features**: knowledge graph and shared artifact collaboration are documented as tenant-scoped and auditable.

## [v2.0.2-agentic-ga-readiness] - 2026-05-23

### Added
- **GA readiness release gate**: `scripts/ga-readiness.sh` and `make ga-readiness` now generate platform and release artifacts and fail unless all 12 GA criteria pass.
- **Surface-area audit target**: `make surface-area-audit` now produces release-governed surface artifacts from declarative inventories.
- **Release evidence line**: `docs/releases/V2_0_2_AGENTIC_GA_READINESS.md` documents the GA criteria, artifacts, and final blocking conditions.

### Changed
- **Surface governance is inventory-driven**: supported surface, API surface, and script manifest metadata now drive GA evidence instead of broad heuristic orphan detection.
- **Provider validation evidence is stricter**: GA only accepts recent non-mock validation when a real/gateway `basic_model_call` passed.
- **Task execution is fail-closed**: unsupported simulation mode no longer falls through implicit execution paths, and completed task/tool outputs require explicit `execution_mode`.
- **Legacy provider-validation alias deprecated**: `REAL_PROVIDER_VALIDATION_ENABLED` now points operators to `AGENT_REAL_PROVIDER_VALIDATION_ENABLED`.

### Security
- **No silent production mock posture for GA**: production overrides for mock LLM remain outside the GA-ready posture.
- **No silent task completion**: task and tool execution paths now tag `execution_mode` explicitly or fail.

## [v2.0.1-agentic-operational-maturity] - 2026-05-23

### Added
- **Controlled deployment modes**: `DEPLOYMENT_MODE` now governs supported postures for `appliance`, `pilot`, `production`, and `enterprise_managed`.
- **GA readiness framework**: Objective maturity scoring, admin reporting endpoints, and release artifacts now measure pilot, production, and GA posture.
- **Runtime activation playbooks**: Official pilot, production, and rollback playbooks now update real platform flags instead of placeholder rollout markers.
- **Feature flag audit artifacts**: Governance audit, orphan detection, and release evidence are promoted into the operational maturity workflow.
- **Surface reduction reporting**: Supported surface and deprecation evidence are consolidated into release-ready markdown artifacts.
- **Security warning governance**: Allowlist metadata, expiration checks, and tracked-file blocking formalize warning cleanup.
- **Real provider validation workflow**: Provider validation remains opt-in but now sits inside the release readiness evidence chain.

### Changed
- **Release narrative shifted from architectural to operational**: the release line now emphasizes activation safety, supportability, and objective readiness over feature expansion.
- **Managed control-plane mode naming aligned**: runtime gating now consistently uses `enterprise_managed`.
- **Playbook activation is environment-realistic**: pilot/production/rollback scripts now write canonical platform flags such as `AGENT_RUNTIME_ENABLED`, `AGENT_EVALS_ENABLED`, and `AGENT_WORKER_AUTOSCALING_ENABLED`.
- **README and security posture updated**: documentation now points operators to operational modes, GA readiness, rollout playbooks, and cleanup governance.

### Security
- **No critical orphaned flags accepted for release**: feature-flag cleanup is now part of the operational maturity gate.
- **Allowlists are restricted to non-versioned synthetic artifacts**: tracked code and versioned files cannot bypass security warning review.
- **Rollback posture restored to appliance-safe defaults**: operational rollback explicitly disables runtime execution and connector writes.

## [v2.0.0-agentic-ai-platform] - 2026-05-22

### Added
- **Gateway LLM Provider**: `AgentExecutor` can use the internal inference gateway when `AGENT_REAL_LLM_ENABLED=true` and `AGENT_LLM_PROVIDER=gateway`.
- **Versioned Tool Adapters**: Built-in adapters are registered, seeded into the tool registry, and executed through the governed tool pipeline.
- **Governed SaaS Connectors**: GitHub, Slack, Jira, Confluence, Salesforce, and Microsoft 365 connectors can operate through governed mock/dry-run and explicit execution paths.
- **Resilient Stateful Workflows**: Workflow runs can persist, sleep, wake on signals/webhooks/polling, and recover without tying up a worker for the entire wait.
- **Reasoning/Acting Repair Loop**: Structured-output repair, malformed JSON correction, context compression, and fallback controls are available for robust iterative execution.
- **Advanced Multi-Agent Topologies**: Team orchestration now includes hierarchical and debate runtimes behind explicit governance flags.
- **Agent Studio and Debugger**: Visual flow definition, validation, compilation, and debug session surfaces are added for operator-facing authoring.
- **Planner Runtime Loop**: Planner-created tasks can execute real tool/model/memory work through `TaskEngine` when explicitly enabled.
- **Semantic Memory Reinjection**: Long-term memory retrieval can be injected back into model context behind dedicated flags.
- **Opt-in Worker Deployment**: Docker Compose `agentic` profile and Helm `agentWorker.enabled=true` now expose the official worker deployment path.
- **Canonical Agent API**: `/v1/agents` is the unified runtime surface and `/agents` is now explicitly deprecated.
- **Promotion Gate Artifacts**: Eval promotion reports are written under `artifacts/agent-evals/latest/`.
- **Versioned Agent Contracts**: Runtime, planner, tool-call, and memory-injection contracts are formalized and validated in test coverage.
- **Agentic SLO and Playbooks**: Operational SLO classes, dashboards, readiness checks, and playbooks are part of the release line.

### Changed
- **Safe defaults expanded**: real LLM, tool adapters, planner real execution, semantic search, context injection, worker, async execution, evals, and real eval provider all stay disabled by default.
- **Five critical layers made explicit**: connectors, workflows, reasoning/acting, multi-agent, and Studio all ship as opt-in, auditable, safe-by-default release surfaces.
- **Promotion posture hardened**: `AGENT_PROMOTION_REQUIRES_EVALS=true` remains the default and blocks promotion without passing eval evidence.
- **Runtime classification updated**: the platform is operational when enabled, but still opt-in and governance-gated by default.
- **Release criteria formalized**: release readiness is now tracked against the eight required criteria for planning/execution, auditability, policy/approval, worker/queue, eval promotion gates, SLOs, versioned contracts, and safe defaults.

### Security
- **No implicit provider reach-out**: agent LLM execution stays on `mock` until the operator intentionally selects the gateway path.
- **Connector side effects stay blocked**: external network access and write capabilities for SaaS connectors remain disabled until explicitly enabled.
- **Legacy surface deprecation**: `/agents` now advertises deprecation and points operators toward `/v1/agents`.
- **Release artifact hygiene**: eval markdown output is redirected to the artifacts tree to support clean release commits.
- **Approval-first posture preserved**: `AGENT_HUMAN_APPROVAL_ENABLED=true` remains the default and continues to gate high-risk or destructive actions.

## [1.10.0-agentic-runtime] - 2026-05-15

### Added
- Agent Registry, Agent Runtime, Tool Governance, Memory, Planning, Human-in-the-Loop approvals, Observability, Evals, and Admin UI surfaces for the Agentic AI Platform.
- Safe-by-default agentic feature gates in `Settings`, `.env.example`, supported-surface governance, and API surface metadata.
- Release artifacts and release notes for `v1.10.0-agentic-runtime`.

### Changed
- Agentic capabilities are now classified as `beta` or `experimental` until the platform matures.
- The default platform posture still prevents real agent execution, real tool execution, memory persistence, planning execution, handoffs, multi-agent orchestration, and marketplace installs.
- Human approval remains enabled by default for high-risk agent actions, and observability remains sanitized by default.

### Security
- Raw prompts are not displayed by default in approval, replay, observability, or memory flows.
- Cross-tenant memory remains disallowed, destructive tools remain blocked by default, and unrestricted autonomy claims are explicitly out of scope.

## [v1.9.8-platform-consolidation] - 2026-05-20

### Added
- **Supportability Pack**: Sanitized diagnostic bundles (`support-bundle-*.tar.gz`) and operator tooling for platform troubleshooting inside the existing admin/operations surface.
- **Support API**: `POST /admin/support/bundle` and `GET /admin/support/bundle/latest` for operator-gated diagnostics.
- **Performance Baseline**: `scripts/performance-baseline.sh` for measuring startup, imports, and latency during freeze validation.
- **Release Artifacts**: Platform freeze, complexity, supported-surface, and validation reporting promoted into the release checklist.

### Changed
- **No new major domain**: `v1.9.8` consolidates existing administrative and operational areas rather than introducing a new bounded context.
- **Lazy Loading**: Router imports in `app.main` are deferred to reduce startup overhead and keep optional surfaces gated.
- **Latency Optimization**: Core endpoint latency was reduced through consolidation and import cleanup.
- **Consolidated Setup**: `app.main`, supportability scripts, supported-surface metadata, and runtime-profile tooling were aligned for lower operational complexity.

### Security
- **Hardened Redaction**: Support-bundle redaction is intended to exclude prompts, documents, keys, and tokens from exported diagnostics.
- **Zero-Secret Release Policy**: Release validation continues to block real `.env` files, committed secrets, and unsupported security marketing claims.

## [1.9.4-enterprise-runtime] - 2026-05-19

### Added
- Explicit enterprise runtime feature gates for Kubernetes/operator mode, distributed runtime, GPU autoscaling, plugin marketplace, and managed control-plane.
- Managed control-plane heartbeat schema guardrails that reject prompt/document-style payload fields and accept operational metadata only.
- Targeted regression coverage for safe enterprise defaults and optional router exposure.
- Release notes draft in `docs/releases/V1_9_4_ENTERPRISE_RUNTIME.md`.

### Changed
- `DEPLOYMENT_MODE` remains `appliance` by default, with all new enterprise capabilities opt-in.
- Optional routers are mounted only when their corresponding feature flags are enabled.
- Distributed runtime resolution no longer interferes with local GGUF hot-swap routing when the feature is disabled.
- Marketplace and GPU orchestration models now keep SQLite-compatible JSON columns for the local/offline test path while preserving PostgreSQL JSONB on PostgreSQL.

### Security
- Managed control-plane payload boundaries are now enforced in code, not only documented.
- Secret scanning and offline marketplace behavior were revalidated for the release candidate.

## [1.9.3-stabilization-hardening] - 2026-05-19

### Added
- Standardized SLO and operational metrics layer with Prometheus integration (`llm_*` metrics).
- New administrative endpoints: `/admin/observability/slo` and `/admin/observability/platform-health`.
- `PlatformSLOService` for real-time reliability and platform health assessment.
- Operational Readiness Pack (`make operational-readiness`) for automated deployment validation.
- Architecture Duplication Audit Report and automated cleanup roadmap.
- `deprecation_middleware` with `X-Deprecated-Endpoint` header for legacy route identification.
- Resilience test suite: Smoke tests and Chaos tests (`make test-smoke-resilience`, `make test-chaos-resilience`).
- Instrumented RBAC, Hot Swap, and Attestation services with operational health metrics.

### Changed
- Improved `core/metrics.py` with standardized naming conventions and legacy compatibility aliases.
- Enhanced `system/operational-readiness` endpoint with database and redis connectivity checks.
- Refactored smoke tests to use robust asynchronous dependency overrides for deterministic results.
- Updated documentation suite with metrics catalog, SLO definitions, and simplification plan.

### Added
- Fase formal de estabilização com novos mecanismos de controle e auditoria.
- Target `make stabilization-check` para validação rigorosa pré-release.
- Target `make release-risk-report` para análise de impacto e riscos.
- Configuração centralizada em `config/stabilization-rules.json`.
- Documentação formal em `docs/releases/STABILIZATION_PHASE.md`.
- Real PKI implementation with local CA, certificate inventory, and CRL management.
- Verifiable Node Attestation service based on binary hash, config hash, and hardware trust.
- Secure Plugin Loader with manifest validation, checksum verification, and signature enforcement.
- Pluggable Hardware Trust Provider interface with Mock and File-based implementations.
- Enforcing mode for Attestation and Plugin security.
- New admin endpoints for PKI initialization and Attestation report/verify.
- Database models for Certificate Inventory, Attestation Reports, and Plugin Registry.
- GGUF Model Hot Swap support: load, unload, and switch models without restarting the data plane.
- Local supervisor for managing multiple `llama-server` processes.
- Admin endpoints and CLI scripts for model runtime management.
- Dynamic routing to active model runtime instances.
- Zero-downtime model switching and rollback support.

### Changed
- Integration hardening for administrative RBAC, tokenization, PKI/attestation, plugin trust, and GGUF hot swap.
- `make test` now exercises the feature-focused regression suite instead of succeeding as a no-op.
- Default-safe behavior is preserved when `RBAC_ADMIN_ENABLED=false`, `PKI_ENABLED=false`, `HARDWARE_TRUST_ENABLED=false`, `MODEL_HOT_SWAP_ENABLED=false`, and `TOKENIZER_MODE=auto`.

## [v1.9.7-compliance-readiness] - 2026-05-20
### Added
- **Compliance Readiness Framework**: Estrutura para preparação de auditorias SOC 2 e ISO 27001.
- **Automated Evidence Collector**: Coleta e sanitização de evidências técnicas para auditoria.
- **ISMS-Lite Governance**: Sistema de gestão de segurança com políticas, riscos e SoA.
- **SOC 2 Control Operations**: Rotinas de revisão de acesso, mudanças e incidentes.
- **Compliance Dashboard**: Interface visual premium para acompanhamento de prontidão e gaps.
- **Continuous Compliance CI/CD**: Gates automáticos para validação de governança e políticas.

## [v1.9.6-ci-chaos] - 2026-05-20
### Added
- **GitHub Actions & GitLab CI**: Pipelines modulares com paridade total para testes, segurança e release.
- **Chaos Engineering Framework**: Injeção controlada de falhas com Admin UI, relatórios de resiliência e auto-rollback.
- **Supply Chain Security**: Geração automática de SBOM e suporte a assinatura digital de artefatos.
- **Release Gates**: Gating rigoroso baseado em prontidão operacional, segurança e documentação.
- **Controlled Deployment**: Pipelines manuais protegidas por ambiente para Appliance, K8s e Pilots.

## [1.9.5-operational-experience] - 2026-05-19

### Added
- **UX Operacional Avançada**: Nova camada administrativa com Dashboards de Performance, Onboarding Enterprise e Gestão Multi-Cluster.
- **Automação de Deployment**: Scripts robustos para preflight, appliance setup, K8s (Helm) e fluxos de upgrade/rollback.
- **Runtime Tuning**: Engine de recomendações baseada em benchmarks sintéticos (Advisory por default).
- **Enterprise Onboarding**: Gestão de pilotos, checklists e geração de Handover Packs.
- **Observabilidade Visual**: Dashboards Grafana provisionados e rastreamento de Error Budget (SLO).
- **Operações Multi-Cluster**: Suporte a clusters remotos, drenagem de tráfego e sincronização segura de configurações.

### Fixed
- Melhoria na segurança de sincronização cross-cluster (proibição de payload sensível).
- Validação de preflight mais rigorosa para variáveis de banco e GPU.

## [1.8.3] - 2026-05-15

### Added
- Real tokenization support via `TokenizerService`.
- Support for `tiktoken` (OpenAI models) and local HuggingFace tokenizers.
- New environment variables: `TOKENIZER_MODE`, `TOKENIZER_MODEL_PATH`, `TOKENIZER_STRICT`, `TOKENIZER_CACHE_ENABLED`.

## [1.9.0] - 2026-05-18

### Added
- Real tokenization support via `TokenizerService`.
- Support for `tiktoken` (OpenAI models) and local HuggingFace tokenizers.
- New environment variables: `TOKENIZER_MODE`, `TOKENIZER_MODEL_PATH`, `TOKENIZER_STRICT`, `TOKENIZER_CACHE_ENABLED`.
- Tracking of tokenization method and estimation status in `usage_record` and `request_financial`.

### Changed
- Centralized token counting in `chat_completions`, `completions`, and `embeddings`.
- Updated billing and quota systems to use real token counts when available.

### Added
- Full administrative RBAC foundation with `admin_users`, `admin_roles`, `admin_permissions`, `admin_user_roles`, `admin_role_permissions` and `admin_audit_events`.
- Idempotent RBAC seed for the initial permission and role catalog plus legacy bootstrap admin user support.
- Administrative RBAC management API under `/admin/rbac/*`.
- Documentation for the admin RBAC rollout in `docs/security/admin-rbac.md`.

### Changed
- `X-Admin-Token` remains supported in legacy mode and becomes the RBAC credential header when `RBAC_ADMIN_ENABLED=true`.
- Existing admin endpoints now enforce domain permissions when RBAC is enabled, while preserving legacy behavior when disabled.
- `.env.example` now documents `RBAC_ADMIN_ENABLED`.

## [v1.9.0-release-engineering-baseline] - 2026-05-16

### Added
- Macrofases 69–82 implementation baseline.
- Plugin runtime foundation for modular platform extensions.
- Reproducible build metadata support.
- Platform sustainability governance models.
- Platform release baseline and validation snapshot infrastructure.

### Changed
- Technical freeze for Phases 69–82 established.
- Enhanced smoke/full validation split for operational stability.

### Governance
- Foundation for release engineering governance.
- Integration of version governance in platform core.
- Release receipt issuance and verification logic.

### Validation
- Operational stability baseline established.
- Deterministic validation snapshot tooling.
- Offline-first release verification suite.

### Documentation
- Release engineering documentation suite (process, governance, versioning).
- Operational runbooks for internal platform releases.
- Release baseline examples and manifest templates.


## [v1.8.1-real-provider-validation] - 2026-05-13

### Added
- Validação real opt-in para OpenAI, DeepSeek e Anthropic via `.env.local`, com dry-run e execução real separadas.
- Fallback real `local -> cloud` com política de `SKIP` controlado quando provider real não está configurado.
- Medição de custo real por provider e validação de billing/margem em BRL com requests reais opcionais.
- Scanner de artefatos/logs para impedir vazamento de API keys, prompts e respostas reais.
- E2E opcional de real providers com relatório consolidado, política de `SKIP/PASS/FAIL` e sanitização obrigatória.
- Documentação operacional da release em `docs/V1_8_1_RELEASE_NOTES.md` e `docs/REAL_PROVIDER_VALIDATION.md`.

### Changed
- VERSION atualizada de `v1.8.0-hybrid-ai-platform` para `v1.8.1-real-provider-validation`.
- `.env.example` expandido com gates `REAL_PROVIDER_VALIDATION_ENABLED`, limites de custo/timeout e blocos dedicados para OpenAI, DeepSeek e Anthropic.
- Scripts locais e `Makefile` passaram a expor comandos de validação real em modo dry-run e modo real opt-in.
- README e documentação de providers/routing/billing foram alinhados com a política de cloud opt-in e sem versionamento de chaves.

### Notes
- Providers reais continuam opcionais; ausência de `.env.local` ou de chaves reais deve resultar em `SKIP`, não em falha da release.
- `Security Report` deve permanecer `PASS` e `Production Readiness` deve permanecer `READY`.
- Cloud real continua opt-in.
- PIX real e PSP real continuam fora do escopo.
- `.env.local`, API keys, logs reais, prompts/respostas reais, `artifacts/real-provider-validation/` e bundles `.tar.gz` continuam proibidos no versionamento.

## [v1.8.0-hybrid-ai-platform] - 2026-05-13

### Added
- Suporte híbrido multi-provider para inferência local/cloud com registry centralizado, adapters configuráveis e health sanitizado.
- Smart routing com políticas `local_first`, `premium_quality`, `lowest_cost`, `coding` e fallback controlado.
- Billing em BRL com custo, preço e margem por requisição, regras por cliente e visibilidade administrativa separada do portal.
- Wallet pré-paga em BRL com crédito manual, débito por uso, idempotência transacional e bloqueio por saldo insuficiente.
- Cache inteligente com modos exato e semântico, integração com billing e isolamento multi-tenant.
- RAG empresarial com ingestão, chunking, retrieval, políticas e segurança por tenant.
- Admin híbrido com sumário consolidado de providers, routing, billing, wallet, cache, RAG e abuse detection.
- Abuse detection com dry-run seguro por padrão, sinais múltiplos e APIs administrativas sanitizadas.
- Validação E2E híbrida com script, relatório consolidado e checagens de segurança da plataforma.

### Changed
- VERSION atualizada de `v1.7.1-post-release-polish` para `v1.8.0-hybrid-ai-platform`.
- Release notes expandidas em `docs/V1_8_RELEASE_NOTES.md` com resumo executivo, limitações e upgrade path da plataforma híbrida.
- Cloud providers permanecem desabilitados por padrão para preservar o modo local-first e evitar chamadas acidentais em ambientes locais.

### Notes
- PIX real permanece fora do escopo desta release.
- PSP real permanece fora do escopo desta release.
- Testes e validações locais não devem disparar chamadas cloud reais.
- Bundles `.tar.gz`, secrets, `.env`/`.local`, chaves de providers, modelos `.gguf`, uploads RAG e artefatos brutos continuam proibidos no versionamento.

## [v1.7.1-post-release-polish] - 2026-05-13

### Added
- Diagnóstico e limpeza de warnings não bloqueantes pós-v1.7.0, com classificação e aceitação formal.
- Guia visual de demonstração com storyboard, screenshots e plano de captura (`docs/demo-visual-guide/`).
- Script `customer-demo-local.sh` para preparação e validação de demonstração para cliente (modos `--quick` e `--full`).
- Validação de fresh machine / WSL limpo com checklist e script dedicados (`FRESH_MACHINE_VALIDATION.md`, `fresh-machine-readiness-check.sh`).
- README.md reorganizado como porta de entrada profissional/comercial (seções: O que é, Para quem serve, Quick start, Customer demo, Limitações, etc.).
- README_CLIENT.md atualizado com exemplos de embeddings, responses API e referência ao SDK Python `scripts/llm_stack_client.py`.
- Script de validação `validate-readme-product-local.sh` com 24 checagens (título, comandos, limitações, links, secrets, scripts).
- Três suítes de teste: `test_readme_product_positioning.py`, `test_readme_links.py`, `test_readme_no_secrets.py`.
- Scripts de validação: `validate-demo-visual-guide.sh`, `validate-customer-demo-local.sh`, `validate-fresh-machine-docs.sh`, `validate-v1.7-warning-cleanup.sh`.
- Script de preparação de screenshots: `prepare-demo-screenshots-local.sh`.
- Documento de warning cleanup: `docs/V1_7_1_WARNING_CLEANUP.md`.

### Changed
- VERSION atualizada de v1.7.0-local-ai-appliance para v1.7.1-post-release-polish.
- README.md: estrutura reorganizada e limitações explicitadas (PSP/PIX real, cloud gerenciada, hardware-dependente).
- README_CLIENT.md: seção Client SDK adicionada com LLMStackClient.
- .gitignore: cobertura para artefatos de screenshot e demonstração.
- Makefile: targets customer-demo, fresh-machine-check, demo-screenshot-plan e validadores associados.

### Notes
- PSP/PIX real permanecem fora do escopo (documentado como limitação).
- Cloud gerenciada permanece fora do escopo (appliance on-premise).
- Screenshots gerados em `artifacts/` não são versionados.
- Nenhum .tar.gz versionado no git (apenas manifests e checksums).

## [v1.7.0-local-ai-appliance] - 2026-05-12

### Added
- Consolidação da linha v1.6.x (v1.6.0 a v1.6.7).
- Transformação em um produto empacotado para implantação on-premise/air-gapped.
- RAG multi-tenant, TTS local, embeddings e responses locais.
- Admin Dashboard e Client Portal.
- Fluxos comerciais completos (CRM, propostas, contratos, faturamento manual).
- White-label básico.
- Processos completos de backup, restore e rollback.
- Release bundle seguro com manifests e checksums versionados (sem .tar.gz).
- Checklist formal v1.7.0 com 13 categorias e 49 blockers.
- Go/No-Go Summary versionável (`docs/V1_7_GO_NO_GO_SUMMARY.md`).
- Validação final consolidada (`scripts/validate-v1.7-final-local.sh`).
- Script de preparação de release bundle (`scripts/prepare-v1.7-release-bundle.sh`).

### Changed
- VERSION atualizada de v1.6.7-final-qa para v1.7.0-local-ai-appliance.
- README.md atualizado com referências ao Go/No-Go Summary e release bundle.
- CLIENT_READY_FINAL_REPORT.md atualizado para v1.7.0-local-ai-appliance.
- V1_7_RELEASE_NOTES.md expandido com seções de release bundle e validação final.
- V1_7_RELEASE_CHECKLIST.md: status Go/No-Go atualizado para GO_WITH_WARNINGS.
- RELEASE_HISTORY.md: adicionada entrada v1.7.0-local-ai-appliance como current.
- LOCAL_PRODUCTION_RUNBOOK.md: adicionada seção de release bundle.

### Notes
- Consulte `docs/V1_7_RELEASE_NOTES.md` para a lista completa de features consolidadas.
- PSP/PIX real permanecem fora do escopo (documentado como future).
- Cloud gerenciada permanece fora do escopo (appliance offline-first).
- Nenhum .tar.gz versionado no git (apenas manifests e checksums).

## [v1.6.7-final-qa] - 2026-05-12

### Added
- Client Ready Report consolidado com artifacts JSON/MD e documento versionavel.
- Checklist formal de promocao para v1.7.0-local-ai-appliance com 13 categorias.
- Geracao de status automatico do checklist v1.7.0 com Go/No-Go.
- Validacao de release checklist com script dedicado.
- Auditoria geral da linha v1.6.x documentada em V1_6_AUDIT_SUMMARY.md.
- Testes de seguranca, status e integridade para client-ready report e v1.7 checklist.

### Changed
- VERSION atualizada de v1.6.6-repo-cleanup para v1.6.7-final-qa.
- RELEASE_HISTORY.md: adicionada entrada v1.6.7-final-qa e v1.6.6-repo-cleanup.
- Makefile: novos targets client-ready-report, validate-client-ready-report, validate-v1.7-checklist, v1.7-checklist-status.
- README.md: secoes para Client Ready Report e v1.7 Release Checklist.
- CAPABILITY_MATRIX.md: PSP/PIX documentado como future.

### Notes
- PSP/PIX real permanecem fora do escopo.
- Rate limit readiness apresenta warning conhecido (exit code 127).
- Release manifests v1.6.5 e v1.6.6 com git_commit da versao anterior (inconsistencia documentada).
- Linha v1.6.x concluida. Proximo release: v1.7.0-local-ai-appliance.

## [v1.6.6-repo-cleanup] - 2026-05-12

### Added
- Consolidacao do layout do repositorio com arquivos operacionais movidos para a raiz.
- Padronizacao das bibliotecas shell compartilhadas em `scripts/lib/`.
- Validacoes automatizadas para imports, paths de scripts, Makefile e layout do repositorio.
- Script seguro para limpeza de branches locais com suporte a `--dry-run` e protecoes para branches estaveis.
- Historico consolidado de releases em `docs/RELEASE_HISTORY.md` com geracao e validacao dedicadas.
- Suite de testes e auditorias locais para fechar a release de repo cleanup com seguranca.

### Notes
- Release preparada para bundle e validacao local completa sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG, `.tar.gz` ou artefatos brutos.

## [v1.6.5-sales-ops] - 2026-05-12

### Added
- CRM local simples para leads com fluxo comercial basico e dados demo locais.
- Proposta comercial preenchivel por cliente com template e validacoes de seguranca.
- Gerador de orcamento local com cobertura administrativa e controles de exposicao.
- Templates de contrato/SOW com geracao local e protecao contra inclusao de secrets.
- Checklist de implantacao paga e relatorio operacional associado.
- Relatorio mensal para cliente com API administrativa, template e validacoes dedicadas.
- Modo white-label basico com configuracao local, branding publico e UI associada.
- Scripts de validacao dedicados para CRM, propostas, orcamentos, contratos, implantacao paga, relatorio mensal e white-label.
- Suite de testes dedicada para fluxos comerciais, contratos, relatórios e seguranca da release.

### Notes
- PSP/PIX real permanecem fora do escopo desta release.
- Release preparada para bundle sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG, `.tar.gz` ou artefatos comerciais gerados.

## [v1.6.4-customer-demo-pack] - 2026-05-11

### Added
- Demo pack comercial com 5 cenarios (clinica, juridico, suporte, educacao, provedor-api), planos e dados ficticios.
- Roteiro de apresentacao para cliente com scripts de 15/30/60 minutos e talk tracks prontos.
- Proposta tecnica Markdown/PDF geravel com `scripts/generate-proposal-pdf.sh`.
- Reset demo seguro com dry-run padrao, --yes obrigatorio e metadata demo=true.
- Dados ficticios realistas em `demo-pack/fake-data/` com validacao dedicada.
- Meeting Ready Check (`scripts/meeting-ready-check-local.sh`) com status MEETING_READY, READY_WITH_WARNINGS, NOT_READY.
- Pagina local /capabilities com recursos, status (GA/Beta/Future) e limitacoes explicitas (PSP, PIX, Tools/FC).
- Endpoint JSON `GET /public/capabilities` com versao, features, limitations, local_appliance_mode, sem secrets.
- Landing page atualizada com link para /capabilities.
- Scripts de validacao: validate-commercial-demo-pack, validate-client-presentation-docs, validate-fake-demo-data, validate-meeting-ready-check, validate-capabilities-page, validate-proposals-local, validate-reset-commercial-demo-pack.
- Testes dedicados para demo pack, apresentacao, propostas, meeting-ready, capabilities page e seguranca.

### Notes
- PSP real nao incluido — faturamento e manual.
- PIX real nao incluido — sem QR Code ou cobranca automatica.
- Tools/Function Calling parcial — depende do backend local.
- Dados demo marcados como ficticios/demo via metadata.
- Release preparada para bundle sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG ou artefatos brutos.

## [v1.6.3-readiness-cleanup] - 2026-05-11

### Added
- Correção de warnings do Production Readiness report com diagnóstico automatizado.
- Modelo de chat utilizável no `/v1/models` probe para validação de readiness.
- Probe chat/SSE robusto com capability opcional e fallback seguro.
- TTS readiness auth corrigido com validação de autenticação explícita.
- Rate limit probe seguro com cleanup e verificação de segurança.
- CORS local/appliance explícito com defaults seguros e probe de readiness.
- Production Readiness final READY com score de validação e security report PASS.
- Testes dedicados para readiness cleanup v1.6.3 e production readiness ready score.

### Notes
- Release preparada para bundle e validação local completa sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG ou artefatos brutos.

## [v1.6.2-installer-polish] - 2026-05-11

### Added
- Instalador local `install-local-appliance.sh` e wizard `configure-local-wizard.sh` para preparar appliances de cliente final com mensagens operacionais amigáveis.
- Checklist pré-demo/pré-cliente, documentação de instalação para cliente final e catálogo de erros operacionais sanitizados.
- Backup automático antes de upgrade, integração de rollback com backup de upgrade e validação completa pós-instalação.
- Scripts de validação local para instalador, wizard, checklist, documentação, erros operacionais, backup/upgrade e pós-instalação.
- Cobertura de testes dedicada para segurança, relatórios e fluxos operacionais da release `installer-polish`.

### Notes
- Release preparada para bundle e validação local completa sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG ou artefatos brutos.

## [v1.6.1-product-hardening] - 2026-05-10

### Added
- Makefile consolidado como entrypoint operacional para rotinas locais de produto e validação.
- System Control Center com cobertura de API, UI e sanitização de saídas administrativas.
- Hardening de migrations com validações de heads, safety checks de upgrade e documentação de operação.
- `LOCAL_APPLIANCE_MODE` com guards de release e validações específicas de segurança local.
- Isolamento multi-tenant reforçado para embeddings, responses, TTS, billing portal e export/delete.
- Proteções contra abuso com autenticação, limites, validação de payloads e isolamento por tenant.
- Matriz comercial de planos e gates de features refletidos em API, portal e pricing.
- Capability matrix e documentação de integrações com exemplos locais sem secrets.

### Notes
- Release preparada para validação local completa, incluindo relatórios de segurança, readiness e bundle sem artefatos proibidos versionados.

## [v1.5.6-runtime-hardening] - 2026-05-09

### Added
- Runtime health e admin deep health com sanitização de informações sensíveis.
- Governança de TTS com quotas, billing local, client portal e dashboard administrativo.
- Benchmark real por modelo com exposição segura via Admin API e documentação operacional.
- Fluxo local de upgrade/rollback com smoke test pós-upgrade e validações de segurança.
- Dashboard e APIs de readiness/security com cobertura de testes e validações locais.

### Notes
- `/v1/embeddings` e `/v1/responses` permanecem fora desta release enquanto não estiverem prontos.

## [v1.6.0-beta.1] - 2026-05-09

### Added
- OpenAI-compatible `/v1/responses` endpoint as a simplified compatibility layer.
- Refactored chat completions pipeline to support multiple entry points.
- Support for `instructions` and `input` (string or array) in `/v1/responses`.
- Simplified `/v1/responses` output contract with `created_at`, `status`, `output`, `output_text`, `usage`, and metadata passthrough.
- Compatibility headers for model routing and fallback: `X-Requested-Model`, `X-Resolved-Model`, `X-Backend-Name`, `X-Fallback-Used`.
- Explicit `501` responses for unsupported `tools`, `tool_choice`, and `stream` in `/v1/responses`.
- Automated tests and examples for the new endpoint.
- Validation script `scripts/validate-responses-api-local.sh`.
- OpenAI-compatible `/v1/embeddings` endpoint.
- Deterministic mock embeddings backend for local testing and integration.
- Embeddings quota management and usage tracking (requests and tokens).
- New embedding fields in `BillingPlan`, `QuotaCounter`, and `UsageRecord`.
- Example scripts for embeddings in CURL, Python, and Node.js.
- Validation script `scripts/validate-embeddings-local.sh`.
- Comprehensive test suite for embeddings.
- New documentation: `docs/OPENAI_COMPATIBILITY.md`.

## [v1.5.5-security-artifacts-clean] - 2026-05-09

### Added
- artifact secret diagnosis
- source redaction for generated artifacts
- safe cleanup/redaction for ignored artifacts
- stronger release artifacts validation
- improved security-report scoring for redacted ignored artifacts
- guarantee summaries/releases do not carry test tokens

## [v1.5.4-security-cleanup] - 2026-05-08

### Added
- security report cleanup workflow
- release artifacts security validation
- permissions validation/fix scripts
- `.pem`/`.key` policy
- `.gitignore` hardening
- safe fixture classification in check-secrets/security-report
- final security cleanup validator

## [v1.5.2-local-ops] - 2026-05-08

### Added
- production readiness report
- security report local
- retention policy local
- tenant export seguro
- tenant delete seguro
- model benchmark
- release bundle seguro
- first-run local

## [v1.5.1-local-production] - 2026-05-08

### Fixed
- fixed release metadata version source
- aligned release manifest, summary.json and summary.md
- added validate-release-metadata.sh
- added regression test for release metadata consistency

## [v1.4.4-local-demo] - 2026-05-08

### Added
- Modo demo local completo rodando em `http://localhost:18080`.
- Cliente demo pré-configurado para fluxos locais de produto.
- API key demo segura gerada em `.local/`, sem expor a chave completa no repositório.
- Documentos RAG demo para testes rápidos de ingestão e consulta.
- Portal demo para experiência do cliente local.
- Dashboard demo para administração local.
- Exemplos de uso em curl, Python e Node.js.
- Script `demo-full-local.sh` para executar a jornada demo completa.
- Landing page local melhorada para onboarding do demo.
- Documentação de demo em `docs/LOCAL_DEMO_GUIDE.md`, `docs/LOCAL_DEMO_FAQ.md` e materiais relacionados.
- Escopo local preservado sem PSP real ou PIX real.

### Fixed
- Robustez no script de demonstração ao lidar com portas de controle de plano.

## [v1.4.3-local-hardening] - 2026-05-07

### Added
- Logging padronizado dos validadores para melhor rastreabilidade.
- Arquivos summary.md e summary.json melhorados com detalhes da validação.
- Release manifest automático em cada execução de release.
- Runbook local detalhado em docs/LOCAL_PRODUCTION_RUNBOOK.md.
- Check de secrets automático para prevenir vazamento de credenciais.
- Limpeza segura de dados RAG locais com script dedicado.

### Changed
- Processo de DR e restore revalidado para ambiente local.
- Scripts de validação agora suportam modo localhost como principal.
- Reforço da segurança no manuseio de dados locais.
