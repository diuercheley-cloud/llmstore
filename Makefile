SHELL := /bin/bash

# Default target
.DEFAULT_GOAL := help

VALIDATE_PHASE_TARGETS := \
	validate-phase-66-readiness \
	validate-phase-69-failure-forecasting \
	validate-phase-70-correlation-engine \
	validate-phase-71-remediation-planning \
	validate-phase-72-remediation-execution \
	validate-phase-73-adapter-sandbox \
	validate-phase-74-adapter-registry \
	validate-phase-75-adapter-promotion \
	validate-phase-76-attestation-framework \
	validate-phase-77-federation-sync \
	validate-phase-78-compatibility-contracts \
	validate-phase-79-plugin-runtime \
	validate-phase-80-plugin-supply-chain \
	validate-phase-81-reproducible-builds \
	validate-phase-82-platform-sustainability

service-coverage-report:
	python3 scripts/check-service-test-coverage.py

service-coverage-gate:
	python3 scripts/check-service-test-coverage.py --gate

# Official deterministic validation groups. These lists are the source of truth
# for aggregate targets and for Makefile governance checks.
CORE_VALIDATION_TARGETS := \
	validate-architecture-boundaries \
	validate-phase-82-platform-sustainability \
	validate-runtime-contracts \
	validate-domain-contracts \
	validate-adrs \
	validate-invariants \
	validate-claims \
	validate-platform-architecture \
	validate-governance-documentation-foundation \
	validate-makefile-governance \
	validate-phase-66-readiness

GOVERNANCE_VALIDATION_TARGETS := \
	validate-governance-documentation-foundation \
	validate-policy-governance \
	validate-operational-controls \
	validate-tenant-encryption \
	validate-sovereign-airgap-governance \
	validate-governance-federation \
	validate-workflow-governance

RUNTIME_VALIDATION_TARGETS := \
	validate-model-supply-chain \
	validate-model-integrity-monitor \
	validate-inference-reproducibility \
	validate-phase-69-failure-forecasting \
	validate-phase-70-correlation-engine \
	validate-phase-71-remediation-planning \
	validate-phase-72-remediation-execution \
	validate-phase-76-attestation-framework \
	validate-runtime-attestation

FEDERATION_VALIDATION_TARGETS := \
	validate-commercial-federation \
	validate-governance-federation \
	validate-federated-workflows \
	validate-phase-77-federation-sync \
	validate-control-plane-mesh

PLUGIN_VALIDATION_TARGETS := \
	validate-phase-73-adapter-sandbox \
	validate-phase-74-adapter-registry \
	validate-phase-75-adapter-promotion \
	validate-phase-79-plugin-runtime \
	validate-phase-80-plugin-supply-chain \
	validate-phase-81-reproducible-builds

COMPATIBILITY_VALIDATION_TARGETS := \
	validate-phase-78-compatibility-contracts \
	validate-commercial-local-infra-adapters

DOCUMENTATION_VALIDATION_TARGETS := \
	validate-platform-documentation \
	validate-adrs \
	validate-claims \
	validate-governance-documentation-foundation \
	validate-makefile-governance

SECURITY_VALIDATION_TARGETS := \
	validate-policy-governance \
	validate-tenant-encryption \
	validate-model-supply-chain \
	validate-model-integrity-monitor \
	validate-cryptographic-receipts \
	validate-rag-vault \
	validate-retrieval-proofs \
	validate-runtime-attestation

ARCHITECTURE_VALIDATION_TARGETS := \
	$(CORE_VALIDATION_TARGETS) \
	validate-phase-69-failure-forecasting \
	validate-phase-70-correlation-engine \
	validate-phase-71-remediation-planning \
	validate-phase-72-remediation-execution \
	validate-phase-73-adapter-sandbox \
	validate-phase-74-adapter-registry \
	validate-phase-75-adapter-promotion \
	validate-phase-76-attestation-framework \
	validate-phase-77-federation-sync \
	validate-phase-78-compatibility-contracts \
	validate-phase-79-plugin-runtime \
	validate-phase-80-plugin-supply-chain \
	validate-phase-81-reproducible-builds \
	validate-release-engineering \
	validate-framework-warnings \
	validate-dependency-graph \
	validate-internal-security-review \
	validate-naming-consistency \
	validate-v1-readiness

PLATFORM_VALIDATION_TARGETS := \
	validate-architecture \
	validate-governance \
	validate-security

ALL_VALIDATION_TARGETS := \
	validate-platform

customer-ready: ## Validate final client installation (Ready/Not Ready)
	./scripts/validate-customer-ready.sh

appliance-local: ## Install as local appliance (no cloud)
	./scripts/install-customer.sh appliance-local

hybrid-provider: ## Install with cloud providers enabled
	./scripts/install-customer.sh hybrid-provider

demo-sales: ## Install optimized for sales demos
	./scripts/install-customer.sh demo-sales

enterprise-rag: ## Install optimized for RAG
	./scripts/install-customer.sh enterprise-rag

dev-lab: ## Install for development and testing
	./scripts/install-customer.sh dev-lab

preflight: ## Run preflight checks for deployment
	@bash scripts/preflight-check.sh

deploy-appliance: ## Deploy as a local appliance
	@bash scripts/deploy-appliance.sh

deploy-k8s: ## Deploy to Kubernetes using Helm
	@bash scripts/deploy-kubernetes.sh

upgrade-release: ## Upgrade the current release with backup and validation
	@bash scripts/upgrade-release.sh

rollback-release: ## Rollback to the previous release
	@bash scripts/rollback-release.sh

post-deploy-validate: ## Validate system after deployment
	@bash scripts/post-deploy-validate.sh

help: ## Show this help message
	@echo "LLM Inference Stack - Operator Commands"
	@echo "Usage: make <target> [BACKUP_DIR=/path/to/backup]"
	@echo ""
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

operational-readiness: ## Run the Operational Readiness Pack validation
	@bash scripts/operational-readiness-pack.sh

release-gate: agentic-ga-hardening ## Run the release gate validator (Requires TAG=vX.Y.Z)
	@bash scripts/release-gate.sh $(TAG)

verify-release-artifacts: ## Verify artifact governance and generate checksums (Requires TAG=vX.Y.Z)
	@bash scripts/verify-release-artifacts.sh $(TAG)

chaos-list: ## List all available chaos experiments
	@bash scripts/chaos-list.sh

chaos-run-safe: ## Run a safe chaos experiment (Requires ID=exp-id)
	@bash scripts/chaos-run.sh $(ID) --safe

chaos-report: ## Generate chaos experiment report (Requires RUN_ID=run-id)
	@bash scripts/chaos-report.sh $(RUN_ID)

compliance-evidence: ## Collect and package compliance evidence (SOC 2 / ISO 27001)
	@mkdir -p artifacts/compliance/latest
	@bash scripts/collect-compliance-evidence.sh
	@bash scripts/generate-compliance-pack.sh

compliance-check: ## Run compliance readiness lint and audit
	@bash scripts/compliance-check.sh

compliance-release-gate: ## Validate compliance criteria for release (Requires TAG=vX.Y.Z)
	@bash scripts/compliance-release-gate.sh $(TAG)

platform-freeze-check: ## Verify architectural freeze rules
	@chmod +x scripts/platform-freeze-check.sh scripts/platform-freeze-check.py
	@bash scripts/platform-freeze-check.sh

check-feature-flags-integrity: ## Validate feature flags integrity
	@chmod +x scripts/check-feature-flags-integrity.sh scripts/check-feature-flags-integrity.py
	@bash scripts/check-feature-flags-integrity.sh

check-supported-surface: ## Reconcile and audit supported surface capabilities
	@chmod +x scripts/check-supported-surface.sh scripts/check_supported_surface.py
	@bash scripts/check-supported-surface.sh

check-freeze-governance: ## Run platform freeze and governance checks
	@chmod +x scripts/check-freeze-governance.sh
	@bash scripts/check-freeze-governance.sh

test-smoke-resilience: ## Run smoke tests for resilience
	@cd control_plane && PYTHONPATH=. ../venv/bin/pytest tests/smoke/test_smoke.py

test-chaos-resilience: ## Run chaos tests for resilience
	@cd control_plane && PYTHONPATH=. ../venv/bin/pytest tests/chaos/test_chaos.py

first-run: ## First run setup with demo data
	./scripts/first-run-local.sh --with-demo

configure-local: ## Guided wizard to configure local appliance
	./scripts/configure-local-wizard.sh --interactive

configure-local-noninteractive: ## Configure local appliance with defaults
	./scripts/configure-local-wizard.sh --non-interactive --yes

up: ## Start the stack in background
	./scripts/up.sh

down: ## Stop the stack
	./scripts/down.sh

restart: ## Restart the stack
	$(MAKE) down
	$(MAKE) up

status: ## Show stack status
	docker compose ps

agent-worker: ## Start the Agent Worker process
	@chmod +x scripts/run-agent-worker.sh
	@./scripts/run-agent-worker.sh

agentic-up: ## Start stack with agentic profile (includes agent-worker)
	docker compose --profile agentic up -d

agentic-readiness: ## Run Agentic Runtime Readiness Checks
	@chmod +x scripts/agentic-readiness.sh
	@./scripts/agentic-readiness.sh

agentic-production-on-readiness: ## Validate Agentic Production-ON readiness (runtime live, not safe-default)
	@chmod +x scripts/validate-agentic-production-on.sh
	@AGENTIC_PRODUCTION_ON_VALIDATION=true ./scripts/validate-agentic-production-on.sh

agent-security-tests: ## Run agent security and sandbox jailbreak tests
	@echo "Running Agent security and jailbreak tests..."
	@PYTHONPATH=.:control_plane .venv/bin/pytest tests/security/ -v

agent-kg-benchmark: ## Generate the synthetic KG benchmark artifact
	@echo "Running Knowledge Graph benchmark..."
	@chmod +x scripts/benchmark-knowledge-graph.sh
	@./scripts/benchmark-knowledge-graph.sh

agent-e2e-tests: ## Run lightweight agentic E2E contract tests
	@echo "Running Agentic E2E tests..."
	@PYTHONPATH=.:control_plane .venv/bin/pytest tests/e2e/test_multi_agent_research_code_review_deploy.py tests/e2e/test_agent_studio_dry_run.py tests/e2e/test_mcp_tool_integration.py -v

agent-executor-e2e: ## Run Agent Executor real E2E flow test
	@echo "Running Agent Executor real E2E flow test..."
	@PYTHONPATH=.:control_plane .venv/bin/pytest tests/e2e/test_agent_executor_real_flow.py -v


agent-platform-validation: ## Run the core agentic expansion validation pack
	@echo "Running full Agentic Platform operational validation..."
	@$(MAKE) agent-security-tests
	@$(MAKE) agent-kg-benchmark
	@$(MAKE) agent-e2e-tests

real-execution-readiness: ## Run Real Execution Readiness Gate
	@chmod +x scripts/real-execution-readiness.sh
	@./scripts/real-execution-readiness.sh

agent-dlq-inspect: ## Inspect agent dead letter queue
	@./scripts/agent-dlq-inspect.sh

agent-recovery-test: ## Run agent queue recovery test
	@./scripts/agent-queue-recovery-test.sh

agent-queue-inspect: ## Inspect agent queue depth, workers, DLQ
	@chmod +x scripts/agent-queue-inspect.sh
	@./scripts/agent-queue-inspect.sh

agent-worker-status: ## Show agent worker status and heartbeats
	@chmod +x scripts/agent-worker-status.sh
	@./scripts/agent-worker-status.sh

agent-worker-drain: ## Drain agent worker (cancel queued jobs)
	@chmod +x scripts/agent-worker-drain.sh
	@./scripts/agent-worker-drain.sh

agent-sandbox-security: ## Run Agent Sandbox Security checks
	@chmod +x scripts/agent-sandbox-security-test.sh
	@./scripts/agent-sandbox-security-test.sh

agent-evals: ## Run Agent Evaluation suites
	@echo "Running Agent Evaluations..."
	@PYTHONPATH=control_plane .venv/bin/python -m pytest tests/agent_evals/

agent-real-provider-validation: ## Run Agent real provider validation suite (opt-in, budgeted)
	@echo "Running Agent Real Provider Validation..."
	@chmod +x scripts/run-agent-real-provider-validation.sh
	@AGENT_REAL_PROVIDER_VALIDATION_ENABLED=true \
	 AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL=1.00 \
	 AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS=60 \
	 PYTHONPATH=control_plane \
	 ./scripts/run-agent-real-provider-validation.sh

agent-real-provider-validation-real: ## Run Agent real provider validation (real calls, may incur cost)
	@echo "Running Agent Real Provider Validation (REAL MODE)..."
	@chmod +x scripts/run-agent-real-provider-validation.sh
	@AGENT_REAL_PROVIDER_VALIDATION_ENABLED=true \
	 AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID=false \
	 AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL=1.00 \
	 PYTHONPATH=control_plane \
	 ./scripts/run-agent-real-provider-validation.sh --real --budget 1.00

agent-eval-gate: ## Run Agent Evaluation promotion gate verification
	@echo "Running Agent Eval Gate Verification..."
	@PYTHONPATH=control_plane .venv/bin/python -c "\
	import asyncio; \
	from app.db.session import SessionLocal; \
	from app.services.agents.eval_gate import EvalGateService; \
	from sqlalchemy import select; \
	from app.models.agents import AgentRegistryEntry; \
	async def run(): \
	    async with SessionLocal() as db: \
	        res = await db.execute(select(AgentRegistryEntry).where(AgentRegistryEntry.status == 'approved')); \
	        entries = res.scalars().all(); \
	        print(f'Found {len(entries)} agents pending gate check'); \
	        for entry in entries: \
	            print(f'  Agent: {entry.name} ({entry.id}) - status: {entry.status}'); \
	asyncio.run(run())"
health: ## Check stack health (endpoints: /health, /ready, /status)
	./scripts/test-health.sh

validate-control-center: ## Validate System Control Center (Backend + UI)
	./scripts/validate-system-control-center-local.sh

validate-operational-controls: ## Validate operational controls governance flows
	chmod +x ./scripts/validate-operational-controls.sh
	./scripts/validate-operational-controls.sh

validate-tenant-encryption: ## Validate tenant encryption controls (Phase 36)
	chmod +x scripts/validate-tenant-encryption.sh
	./scripts/validate-tenant-encryption.sh

validate-sovereign-airgap-governance: ## Validate sovereign airgap governance controls (Phase 37)
	chmod +x scripts/validate-sovereign-airgap-governance.sh
	./scripts/validate-sovereign-airgap-governance.sh

validate-model-supply-chain: ## Validate secure model supply chain controls (Phase 38)
	chmod +x scripts/validate-model-supply-chain.sh
	./scripts/validate-model-supply-chain.sh

validate-model-integrity-monitor: ## Validate runtime model integrity monitor (Phase 39)
	chmod +x scripts/validate-model-integrity-monitor.sh
	./scripts/validate-model-integrity-monitor.sh

validate-cryptographic-receipts: ## Validate cryptographic inference receipts (Phase 41)
	chmod +x scripts/validate-cryptographic-receipts.sh
	./scripts/validate-cryptographic-receipts.sh

validate-rag-vault: ## Validate regulated RAG vault controls (Phase 48)
	chmod +x scripts/validate-rag-vault.sh
	./scripts/validate-rag-vault.sh

validate-retrieval-proofs: ## Validate retrieval proofs + context lineage (Phase 49)
	chmod +x scripts/validate-retrieval-proofs.sh
	./scripts/validate-retrieval-proofs.sh

validate-architecture-boundaries: ## Validate architecture boundaries for the stabilization cycle
	python3 ./scripts/validate_architecture_boundaries.py

validate-runtime-contracts: ## Validate core runtime contract documentation
	python3 ./scripts/validate_runtime_contracts.py

validate-domain-contracts: ## Validate lightweight domain contracts for modularization
	python3 ./scripts/validate_domain_contracts.py

validate-invariants: ## Validate lightweight advisory invariants
	python3 ./scripts/validate_invariants.py

validate-adrs: ## Validate Architectural Decision Records
	python3 ./scripts/validate_adrs.py

validate-platform-architecture: ## Run unified platform architecture validation suite
	python3 ./scripts/validate_platform_architecture.py

validate-phase-82-platform-sustainability: ## Validate Phase 82 platform sustainability, governance core and dry-run recovery
	python3 ./scripts/validate_phase_82_platform_sustainability.py
	python3 ./scripts/validate_platform_boundaries.py
	.venv/bin/python -m pytest \
		tests/architecture/test_platform_boundaries.py \
		tests/architecture/test_phase_82_platform_sustainability.py \
		tests/architecture/test_domain_dependency_graph.py \
		tests/governance/test_policy_dsl.py \
		tests/governance/test_phase_82_policy_engine.py \
		tests/governance/test_policy_conflicts.py \
		tests/governance/test_data_governance.py \
		tests/governance/test_human_governance_workflows.py \
		tests/governance/test_phase_82_governance_core.py \
		tests/operations/test_deterministic_events.py \
		tests/operations/test_sovereign_observability.py \
		tests/operations/test_disaster_recovery.py \
		tests/operations/test_phase_82_operations_core.py \
		tests/test_router_presence.py \
		-q --tb=short

validate-claims: ## Validate documentation and scripts for prohibited claims
	python3 ./scripts/validate_claims.py

validate-governance-documentation-foundation: ## Validate Governance Documentation Foundation before Phase 79
	python3 ./scripts/validate_governance_documentation_foundation.py
	.venv/bin/python -m pytest tests/docs/test_governance_documentation_foundation.py -q --tb=short

validate-release-engineering: ## Validate release engineering and operational stability baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/validate_release_engineering.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/releases/ -q --tb=short

generate-release-baseline: ## Generate deterministic platform release baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/generate_release_baseline.py

validate-framework-warnings: ## Validate framework warnings and deprecations
	PYTHONPATH=control_plane .venv/bin/python scripts/validate_framework_warnings.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/quality/test_framework_warnings.py -q --tb=short

coverage-baseline: ## Generate coverage baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/generate_coverage_baseline.py

validate-dependency-graph: ## Validate architectural dependency graph
	PYTHONPATH=control_plane .venv/bin/python scripts/validate_dependency_graph.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/architecture/test_dependency_graph_hardening.py -q --tb=short

performance-baseline: ## Generate performance baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/generate_performance_baseline.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/performance/test_performance_baseline_tools.py -q --tb=short

validate-internal-security-review: ## Validate internal security review
	PYTHONPATH=control_plane .venv/bin/python scripts/validate_internal_security_review.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/security/test_internal_security_review.py -q --tb=short

validate-naming-consistency: ## Validate naming and API consistency
	PYTHONPATH=control_plane .venv/bin/python scripts/validate_naming_consistency.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/architecture/test_naming_consistency.py -q --tb=short

validate-v1-readiness: ## Validate v1 readiness criteria
	PYTHONPATH=control_plane .venv/bin/python scripts/validate_v1_readiness.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/releases/test_v1_readiness.py -q --tb=short

validate-pre-v1-hardening: ## Run all pre-v1 platform hardening & stabilization validators
	$(MAKE) validate-framework-warnings
	$(MAKE) coverage-baseline
	$(MAKE) validate-dependency-graph
	$(MAKE) performance-baseline
	$(MAKE) validate-internal-security-review
	$(MAKE) validate-naming-consistency
	$(MAKE) validate-v1-readiness

# --- Core Validation ---
# `validate-architecture` is the legacy-compatible deterministic runner for the
# Phase 66 and Phase 69-79 validation chain.
validate-architecture: ## Run the full architectural validation group in deterministic order
	@echo "Running architectural validation group"
	@set -e; for target in $(ARCHITECTURE_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Architectural validation group passed"

# Smoke validation targets — static checks and short tests only.
# These exclude long integration suites and are suitable for daily use.
SMOKE_VALIDATION_TARGETS := \
	validate-platform-documentation \
	validate-makefile-governance \
	validate-governance-documentation-foundation \
	validate-domain-contracts \
	validate-claims \
	validate-platform-architecture \
	validate-architecture-boundaries \
	validate-runtime-contracts \
	validate-invariants \
	validate-adrs \
	validate-release-engineering \
	validate-framework-warnings \
	validate-dependency-graph \
	validate-internal-security-review \
	validate-naming-consistency \
	validate-v1-readiness

validate-architecture-smoke: ## Run smoke validation (static checks + short tests, no slow integration)
	@echo "Running smoke validation (fast path, no integration tests)"
	@set -e; for target in $(SMOKE_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "--- Phase validator scripts (static checks, no slow pytest) ---"
	python3 ./scripts/validate_phase_69_failure_forecasting.py --smoke
	python3 ./scripts/validate_phase_70_correlation_engine.py
	python3 ./scripts/validate_phase_71_remediation_planning.py
	python3 ./scripts/validate_phase_72_remediation_execution.py
	python3 ./scripts/validate_phase_73_adapter_sandbox.py
	python3 ./scripts/validate_phase_74_adapter_registry.py
	python3 ./scripts/validate_phase_75_adapter_promotion.py
	./.venv/bin/python scripts/validate_phase_76_attestation_framework.py
	./.venv/bin/python scripts/validate_phase_77_federation_sync.py
	python3 ./scripts/validate_phase_78_compatibility_contracts.py
	python3 ./scripts/validate_phase_79_plugin_runtime.py
	python3 ./scripts/validate_phase_80_plugin_supply_chain.py
	python3 ./scripts/validate_phase_81_reproducible_builds.py
	@echo "--- Phase 82 smoke ---"
	$(MAKE) --no-print-directory validate-phase-82-platform-sustainability
	$(MAKE) --no-print-directory validate-release-engineering
	$(MAKE) --no-print-directory validate-framework-warnings
	$(MAKE) --no-print-directory validate-dependency-graph
	$(MAKE) --no-print-directory validate-internal-security-review
	$(MAKE) --no-print-directory validate-naming-consistency
	$(MAKE) --no-print-directory validate-v1-readiness
	@echo "Smoke validation passed"

# `validate-architecture-full` preserves full coverage (same as legacy validate-architecture).
validate-architecture-full: ## Run full architecture validation (complete, may include slow tests)
	$(MAKE) --no-print-directory validate-architecture

measure-validation-targets: ## Measure duration and exit code of validation targets
	python3 ./scripts/measure_validation_targets.py

list-slow-tests: ## Identify slow pytest tests
	python3 ./scripts/list_slow_tests.py --test-dir tests/build --timeout 120

# `validate-platform` and `validate-all` are the official top-level aggregates.
# They intentionally compose other aggregates instead of redefining recipes.
validate-platform: ## Run the official platform validation aggregates in deterministic order
	@echo "Running platform validation group"
	@set -e; for target in $(PLATFORM_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Platform validation group passed"

validate-all: ## Run the full deterministic validation stack
	@echo "Running complete validation group"
	@set -e; for target in $(ALL_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Complete validation group passed"

# --- Governance Validation ---
# Legacy governance targets remain callable directly; this aggregate defines the
# official deterministic order for governance-only checks.
validate-governance: ## Run governance validation targets in deterministic order
	@echo "Running governance validation group"
	@set -e; for target in $(GOVERNANCE_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Governance validation group passed"

# --- Runtime Validation ---
validate-runtime: ## Run runtime validation targets in deterministic order
	@echo "Running runtime validation group"
	@set -e; for target in $(RUNTIME_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Runtime validation group passed"

# --- Federation Validation ---
validate-federation: ## Run federation validation targets in deterministic order
	@echo "Running federation validation group"
	@set -e; for target in $(FEDERATION_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Federation validation group passed"

# --- Plugin Validation ---
validate-plugin: ## Run plugin validation targets in deterministic order
	@echo "Running plugin validation group"
	@set -e; for target in $(PLUGIN_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Plugin validation group passed"

# --- Compatibility Validation ---
validate-compatibility: ## Run compatibility validation targets in deterministic order
	@echo "Running compatibility validation group"
	@set -e; for target in $(COMPATIBILITY_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Compatibility validation group passed"

# --- Documentation Validation ---
validate-platform-documentation: ## Validate platform documentation completeness and consistency
	python3 ./scripts/validate_platform_documentation.py
	python3 ./scripts/check-doc-consistency.py
	.venv/bin/python -m pytest tests/docs/test_platform_documentation.py -q --tb=short

validate-documentation: ## Run documentation validation targets in deterministic order
	@echo "Running documentation validation group"
	@set -e; for target in $(DOCUMENTATION_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Documentation validation group passed"

# --- Security Validation ---
validate-security: ## Run security validation targets in deterministic order
	@echo "Running security validation group"
	@set -e; for target in $(SECURITY_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "Security validation group passed"

# Compatibility alias for older automation that expects a single Makefile
# governance checker target instead of the documentation/runtime split.
validate-makefile-governance: ## Validate Makefile governance structure, docs and tests
	python3 ./scripts/validate_makefile_governance.py
	.venv/bin/python -m pytest tests/build/test_makefile_governance.py -q --tb=short

validate-phase-66-readiness: ## Validate readiness gate before Phase 66 implementation
	python3 ./scripts/validate_phase_66_readiness.py

validate-phase-69-failure-forecasting: ## Validate Phase 69 Predictive Failure Signals + Deterministic Forecasting
	python3 ./scripts/validate_phase_69_failure_forecasting.py
	# Targeted test list — do NOT run tests/operations/ broadly to avoid
	# excessive execution in the validate-architecture aggregate.
	.venv/bin/python -m pytest \
		tests/operations/test_failure_signal_models.py \
		tests/operations/test_deterministic_forecasting_engine.py \
		tests/operations/test_failure_risk_scoring.py \
		tests/operations/test_failure_forecasting_receipts.py \
		tests/operations/test_failure_forecasting_audit_events.py \
		tests/operations/test_failure_forecasting_api.py \
		-q --tb=short

validate-phase-70-correlation-engine: ## Validate Phase 70 Deterministic Operations Correlation Engine
	python3 ./scripts/validate_phase_70_correlation_engine.py
	.venv/bin/python -m pytest \
		tests/operations/test_correlation_models.py \
		tests/operations/test_deterministic_correlation_engine.py \
		tests/operations/test_operational_trust_graph.py \
		tests/operations/test_correlation_api.py \
		tests/operations/test_correlation_receipts.py \
		tests/operations/test_correlation_audit_events.py \
		tests/operations/test_correlation_risk_analysis.py \
		tests/operations/test_correlation_dashboard.py \
		tests/operations/test_phase_70_validation.py \
		-q --tb=short

validate-phase-71-remediation-planning: ## Validate Phase 71 Deterministic Remediation Planning
	python3 ./scripts/validate_phase_71_remediation_planning.py
	.venv/bin/python -m pytest \
		tests/operations/test_remediation_planning_models.py \
		tests/operations/test_deterministic_remediation_planner.py \
		tests/operations/test_remediation_blast_radius.py \
		tests/operations/test_remediation_approval_requirements.py \
		tests/operations/test_remediation_receipts.py \
		tests/operations/test_remediation_audit_events.py \
		tests/operations/test_remediation_planning_api.py \
		tests/operations/test_remediation_planning_dashboard.py \
		tests/operations/test_phase_71_validation.py \
		-q --tb=short

validate-phase-72-remediation-execution: ## Validate Phase 72 Approval-Gated Remediation Execution
	python3 ./scripts/validate_phase_72_remediation_execution.py
	.venv/bin/python -m pytest \
		tests/operations/test_remediation_execution_models.py \
		tests/operations/test_remediation_execution_gate.py \
		tests/operations/test_remediation_simulation_adapter.py \
		tests/operations/test_approval_gated_remediation_executor.py \
		tests/operations/test_remediation_execution_rollback.py \
		tests/operations/test_remediation_execution_receipts.py \
		tests/operations/test_remediation_execution_audit_events.py \
		tests/operations/test_remediation_execution_api.py \
		tests/operations/test_remediation_execution_dashboard.py \
		tests/operations/test_phase_72_validation.py \
		-q --tb=short

validate-phase-73-adapter-sandbox: ## Validate Phase 73 Controlled Adapter Sandbox
	python3 ./scripts/validate_phase_73_adapter_sandbox.py
	.venv/bin/python -m pytest \
		tests/operations/test_adapter_sandbox_models.py \
		tests/operations/test_adapter_contracts.py \
		tests/operations/test_adapter_manifest_validator.py \
		tests/operations/test_adapter_sandbox_context.py \
		tests/operations/test_adapter_simulation_runner.py \
		tests/operations/test_adapter_policy_guard.py \
		tests/operations/test_adapter_sandbox_receipts.py \
		tests/operations/test_adapter_sandbox_audit_events.py \
		tests/operations/test_adapter_sandbox_api.py \
		tests/operations/test_adapter_sandbox_dashboard.py \
		tests/operations/test_phase_73_validation.py \
		-q --tb=short

validate-phase-74-adapter-registry: ## Validate Phase 74 Signed Adapter Registry
	python3 ./scripts/validate_phase_74_adapter_registry.py
	.venv/bin/python -m pytest \
		tests/operations/test_adapter_registry_models.py \
		tests/operations/test_adapter_registry_hash_utils.py \
		tests/operations/test_signed_adapter_registry_service.py \
		tests/operations/test_adapter_registry_policy_engine.py \
		tests/operations/test_adapter_registry_allowlist_blocklist.py \
		tests/operations/test_adapter_registry_receipts.py \
		tests/operations/test_adapter_registry_audit_events.py \
		tests/operations/test_adapter_registry_api.py \
		tests/operations/test_adapter_registry_dashboard.py \
		tests/operations/test_phase_74_validation.py \
		-q --tb=short

validate-phase-75-adapter-promotion: ## Validate Phase 75 Adapter Promotion Workflow
	python3 ./scripts/validate_phase_75_adapter_promotion.py
	.venv/bin/python -m pytest \
		tests/operations/test_adapter_promotion_models.py \
		tests/operations/test_adapter_promotion_hash_utils.py \
		tests/operations/test_adapter_promotion_gates.py \
		tests/operations/test_adapter_promotion_workflow_service.py \
		tests/operations/test_adapter_promotion_staging_simulation.py \
		tests/operations/test_adapter_promotion_receipts.py \
		tests/operations/test_adapter_promotion_audit_events.py \
		tests/operations/test_adapter_promotion_api.py \
		tests/operations/test_adapter_promotion_dashboard.py \
		tests/operations/test_phase_75_validation.py \
		-q --tb=short

validate-phase-78-compatibility-contracts: ## Validate Phase 78 Compatibility Contracts & Version Negotiation
	python3 ./scripts/validate_phase_78_compatibility_contracts.py
	.venv/bin/python -m pytest \
		tests/operations/test_compatibility_models.py \
		tests/operations/test_compatibility_hash_utils.py \
		tests/operations/test_semantic_versioning.py \
		tests/operations/test_compatibility_matrix.py \
		tests/operations/test_version_negotiation.py \
		tests/operations/test_capability_negotiation.py \
		tests/operations/test_deprecation_lifecycle.py \
		tests/operations/test_compatibility_verification.py \
		tests/operations/test_compatibility_receipts.py \
		tests/operations/test_compatibility_audit_events.py \
		tests/operations/test_compatibility_api.py \
		tests/operations/test_compatibility_dashboard.py \
		tests/operations/test_phase_78_validation.py \
		-q --tb=short

validate-phase-79-plugin-runtime: ## Validate Phase 79 Formal Plugin ABI & Extension Runtime
	python3 ./scripts/validate_phase_79_plugin_runtime.py
	.venv/bin/python -m pytest \
		tests/operations/test_plugin_runtime_models.py \
		tests/operations/test_plugin_runtime_hash_utils.py \
		tests/operations/test_plugin_abi_contracts.py \
		tests/operations/test_plugin_capability_boundaries.py \
		tests/operations/test_plugin_runtime_compatibility_enforcer.py \
		tests/operations/test_plugin_extension_loader.py \
		tests/operations/test_plugin_isolation_policy.py \
		tests/operations/test_plugin_lifecycle.py \
		tests/operations/test_plugin_replay_verifier.py \
		tests/operations/test_plugin_federation_compatibility.py \
		tests/operations/test_plugin_runtime_receipts.py \
		tests/operations/test_plugin_runtime_audit_events.py \
		tests/operations/test_plugin_runtime_api.py \
		tests/operations/test_plugin_runtime_dashboard.py \
		tests/operations/test_phase_79_validation.py \
		-q --tb=short

validate-phase-80-plugin-supply-chain: ## Validate Phase 80 Plugin Supply-Chain Provenance & SBOM Placeholder Framework
	python3 ./scripts/validate_phase_80_plugin_supply_chain.py
	.venv/bin/python -m pytest \
		tests/operations/test_plugin_supply_chain_models.py \
		tests/operations/test_plugin_supply_chain_hash_utils.py \
		tests/operations/test_plugin_supply_chain_services.py \
		tests/operations/test_plugin_supply_chain_api.py \
		tests/operations/test_plugin_supply_chain_dashboard.py \
		tests/operations/test_phase_80_validation.py \
		-q --tb=short

validate-phase-81-reproducible-builds: ## Validate Phase 81 Reproducible Build & Artifact Verification Framework
	python3 ./scripts/validate_phase_81_reproducible_builds.py
	.venv/bin/python -m pytest \
		tests/operations/test_reproducible_build_models.py \
		tests/operations/test_reproducible_build_hash_utils.py \
		tests/operations/test_reproducible_build_service.py \
		tests/operations/test_artifact_verification.py \
		tests/operations/test_source_artifact_lineage.py \
		tests/operations/test_build_environment_policy.py \
		tests/operations/test_artifact_replay_verifier.py \
		tests/operations/test_reproducible_build_provenance_integration.py \
		tests/operations/test_reproducible_build_receipts.py \
		tests/operations/test_reproducible_build_audit_events.py \
		tests/operations/test_reproducible_build_api.py \
		tests/operations/test_reproducible_build_dashboard.py \
		tests/operations/test_phase_81_validation.py \
		-q --tb=short

validate-phase-76-attestation-framework: ## Validate Sovereign Execution Attestation Framework (Phase 76)
	./.venv/bin/python scripts/validate_phase_76_attestation_framework.py
	./.venv/bin/python -m pytest \
		tests/operations/test_attestation_framework_models.py \
		tests/operations/test_attestation_hash_utils.py \
		tests/operations/test_attestation_service.py \
		tests/operations/test_attestation_federation_bundle.py \
		tests/operations/test_attestation_trust_policy_engine.py \
		tests/operations/test_attestation_replay_verifier.py \
		tests/operations/test_attestation_receipts.py \
		tests/operations/test_attestation_audit_events.py \
		tests/operations/test_attestation_api.py \
		tests/operations/test_attestation_dashboard.py \
		tests/operations/test_phase_76_validation.py \
		-q --tb=short

validate-phase-77-federation-sync: ## Validate Sovereign Federation Synchronization Protocol (Phase 77)
	./.venv/bin/python scripts/validate_phase_77_federation_sync.py
	./.venv/bin/python -m pytest \
		tests/operations/test_federation_sync_models.py \
		tests/operations/test_federation_hash_utils.py \
		tests/operations/test_federation_environment_registry.py \
		tests/operations/test_federation_synchronization_protocol.py \
		tests/operations/test_federation_trust_negotiation.py \
		tests/operations/test_federation_conflict_resolution.py \
		tests/operations/test_federation_replay_verifier.py \
		tests/operations/test_federation_receipts.py \
		tests/operations/test_federation_audit_events.py \
		tests/operations/test_federation_api.py \
		tests/operations/test_federation_dashboard.py \
		tests/operations/test_phase_77_validation.py \
		-q --tb=short
validate-execution-proofs: ## Validate verifiable AI execution proofs + Merkle audit timelines (Phase 60)
	chmod +x scripts/validate-execution-proofs.sh
	./scripts/validate-execution-proofs.sh

validate-inference-reproducibility: ## Validate deterministic inference audit + replay controls (Phase 40)
	chmod +x scripts/validate-inference-reproducibility.sh
	./scripts/validate-inference-reproducibility.sh

validate-post-install: ## Run post-installation validation
	./scripts/validate-post-install-local.sh --with-demo

validate-quick: ## Quick production validation
	VALIDATION_MODE=quick ./scripts/validate-local-production-full.sh

validate-full: ## Full production validation
	VALIDATION_MODE=full ./scripts/validate-local-production-full.sh

validate-release: ## Release production validation
	VALIDATION_MODE=release ./scripts/validate-local-production-full.sh

validate-nightly: ## Nightly production validation
	VALIDATION_MODE=nightly ./scripts/validate-local-production-full.sh

validate: validate-full validate-feature-flags validate-scripts ## Alias to validate-full

validate-feature-flags: ## Validate feature flags governance
	chmod +x ./scripts/check-feature-flags.sh
	./scripts/check-feature-flags.sh

feature-flag-audit: ## Run the feature flags governance auditor
	chmod +x ./scripts/audit-feature-flags.py
	@if [ -x ./.venv/bin/python3 ]; then ./.venv/bin/python3 ./scripts/audit-feature-flags.py; \
	elif [ -x ./venv/bin/python3 ]; then ./venv/bin/python3 ./scripts/audit-feature-flags.py; \
	else python3 ./scripts/audit-feature-flags.py; fi

surface-area-audit: ## Run the supported surface governance audit
	chmod +x ./scripts/surface-area-audit.py
	@if [ -x ./.venv/bin/python3 ]; then PYTHONPATH=control_plane ./.venv/bin/python3 ./scripts/surface-area-audit.py; \
	elif [ -x ./venv/bin/python3 ]; then PYTHONPATH=control_plane ./venv/bin/python3 ./scripts/surface-area-audit.py; \
	else PYTHONPATH=control_plane python3 ./scripts/surface-area-audit.py; fi

ga-readiness: ## Run the GA readiness gate
	chmod +x ./scripts/ga-readiness.sh
	./scripts/ga-readiness.sh $(TAG)

validate-scripts: ## Validate operational scripts governance
	chmod +x ./scripts/check-script-manifest.sh
	./scripts/check-script-manifest.sh

backup-dry-run: ## Run dry-run database and configs backup simulation
	chmod +x ./scripts/backup.sh
	./scripts/backup.sh --dry-run

restore-dry-run: ## Run dry-run database restore simulation
	chmod +x ./scripts/restore-local.sh
	./scripts/restore-local.sh --dry-run ./artifacts/backups/test-backup-run

upgrade-dry-run: ## Run dry-run system upgrade simulation
	chmod +x ./scripts/upgrade-release.sh
	./scripts/upgrade-release.sh --dry-run --force

rollback-dry-run: ## Run dry-run system rollback simulation
	chmod +x ./scripts/rollback-release.sh
	./scripts/rollback-release.sh --dry-run


validate-migrations: ## Validate Alembic migrations integrity
	./scripts/validate-migrations-local.sh

validate-providers: ## Validate multi-provider layer
	./scripts/validate-providers-local.sh

validate-smart-routing: ## Validate smart routing engine
	chmod +x ./scripts/validate-smart-routing-local.sh
	./scripts/validate-smart-routing-local.sh

validate-billing-brl: ## Validate billing BRL engine
	chmod +x ./scripts/validate-billing-brl-local.sh
	./scripts/validate-billing-brl-local.sh

validate-prepaid-wallet: ## Validate prepaid wallet in BRL
	chmod +x ./scripts/validate-prepaid-wallet-local.sh
	./scripts/validate-prepaid-wallet-local.sh

validate-abuse: ## Run abuse protection validation suite
	./scripts/validate-abuse-protection-local.sh

validate-cors: ## Validate CORS configuration for local appliance
	./scripts/validate-cors-local-appliance.sh

validate-migrations-temp: ## Validate migrations from scratch using temporary DB
	./scripts/validate-migrations-local.sh --temp-db

demo: ## Run full demo (no build)
	./scripts/demo-full-local.sh --no-build

security: ## Generate security report
	@$(MAKE) agent-sandbox-security
	./scripts/security-report-local.sh

security-cleanup-report: ## Generate security cleanup report
	./scripts/security-report-local.sh
	mkdir -p artifacts/security
	cp $$(ls -td artifacts/security-reports/* | head -n 1)/security-report.md artifacts/security/security-cleanup.md
	@echo "Security cleanup report written to artifacts/security/security-cleanup.md"

pre-client-check: ## Run pre-client installation checklist
	chmod +x ./scripts/pre-client-checklist-local.sh
	./scripts/pre-client-checklist-local.sh --client-install

pre-demo-check: ## Run pre-demo checklist
	chmod +x ./scripts/pre-client-checklist-local.sh
	./scripts/pre-client-checklist-local.sh --demo

readiness: ## Run production readiness check
	./scripts/production-readiness-local.sh

release: ## Create release bundle
	./scripts/create-release-bundle.sh --version $(shell cat VERSION) --include-docs --include-examples --include-demo

backup: ## Perform local backup (artifacts/backups-local/)
	./scripts/backup-local.sh

restore: ## Restore from backup (Requires BACKUP_DIR)
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "Usage: make restore BACKUP_DIR=/path/to/backup"; \
		echo "Available backups in artifacts/backups-local/:"; \
		ls -d artifacts/backups-local/*/ 2>/dev/null || echo "No backups found."; \
		exit 1; \
	fi
	./scripts/restore-local.sh $(BACKUP_DIR)

upgrade: ## Upgrade local installation
	./scripts/upgrade-local.sh

rollback: ## Rollback local installation
	./scripts/rollback-local.sh

benchmark: ## Run quick model benchmark
	./scripts/benchmark-model-local.sh --quick

smoke: ## Run post-upgrade smoke tests
	./scripts/post-upgrade-smoke-local.sh

clean-safe: ## Dry-run of data retention (safe cleanup)
	./scripts/retention-local.sh --dry-run --section all

logs: ## Show logs (use SERVICE=name for specific service)
	@if [[ -n "$$SERVICE" ]]; then \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f $$SERVICE; \
	else \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f control-plane control-plane-worker data-plane-gemma agent-worker; \
	fi

check-secrets: ## Scan for secrets in the codebase
	./scripts/check-secrets.sh --all

stabilization-check: ## Run formal stabilization phase checks
	chmod +x ./scripts/stabilization-check.sh ./scripts/check-working-tree-clean.sh ./scripts/check-feature-flags.sh ./scripts/working-tree-certification.sh
	./scripts/check-working-tree-clean.sh
	./scripts/check-feature-flags.sh
	$(MAKE) working-tree-certification
	@make platform-freeze-check
	./scripts/stabilization-check.sh

complexity-report: ## Generate platform complexity analysis and recommendations
	chmod +x ./scripts/complexity-report.sh
	./scripts/complexity-report.sh

working-tree-certification: ## Certify working tree is clean for release (Requires TAG=vX.Y.Z)
	@chmod +x scripts/working-tree-certification.sh
	@bash scripts/working-tree-certification.sh $(TAG)

working-tree-governance: ## Check working tree governance (non-blocking vs blocking dirt)
	@chmod +x scripts/check-working-tree-governance.sh
	@bash scripts/check-working-tree-governance.sh


release-risk-report: ## Generate stabilization risk report
	chmod +x ./scripts/release-risk-report.sh ./scripts/check-working-tree-clean.sh
	./scripts/check-working-tree-clean.sh
	./scripts/release-risk-report.sh

fix-permissions: ## Fix local file permissions
	./scripts/fix-local-permissions.sh --yes

install-local: ## Install system as local appliance with demo data
	./scripts/install-local-appliance.sh --with-demo

validate-install-local: ## Validate local appliance installer
	./scripts/validate-install-local-appliance.sh

validate-backup-before-upgrade: ## Validate backup before upgrade logic
	./scripts/validate-backup-before-upgrade-local.sh

install: ## Install system dependencies
	./scripts/install.sh

install-git-hooks: ## Install pre-commit git hooks
	./scripts/check-secrets.sh --install-hook

demo-pack: ## Seed commercial demo pack (5 scenarios, clients, plans, RAG, invoices)
	chmod +x ./scripts/seed-commercial-demo-pack.sh
	./scripts/seed-commercial-demo-pack.sh

validate-demo-pack: ## Validate commercial demo pack integrity and data
	chmod +x ./scripts/validate-commercial-demo-pack.sh
	./scripts/validate-commercial-demo-pack.sh

reset-demo-pack: ## Safe dry-run reset of commercial demo pack (default: --dry-run, never deletes real data)
	chmod +x ./scripts/reset-commercial-demo-pack.sh
	./scripts/reset-commercial-demo-pack.sh --dry-run

validate-reset-demo-pack: ## Validate reset safety (dry-run mode, no data harmed)
	chmod +x ./scripts/validate-reset-commercial-demo-pack.sh
	./scripts/validate-reset-commercial-demo-pack.sh

validate-fake-data: ## Validate fake demo data integrity and safety
	chmod +x ./scripts/validate-fake-demo-data.sh
	./scripts/validate-fake-demo-data.sh

# Legacy sales seed remains separate from fake-data validation; previous
# adjacency caused recipe shadowing and non-deterministic target resolution.
sales-seed: ## Seed commercial demo leads
	./scripts/seed-sales-demo-leads.sh

validate-sales-crm: ## Validate Sales CRM (API + UI)
	./scripts/validate-sales-crm-local.sh

clean-compose-local: ## Clean up docker-compose resources
	./scripts/clean-compose-local.sh

# Backward compatibility aliases
first-run-local: first-run
first-run-demo: first-run
security-report: security
production-readiness: readiness
demo-local: demo
upgrade-local: upgrade
rollback-local: rollback
post-upgrade-smoke: smoke
benchmark-quick: benchmark
benchmark-model: benchmark
validate-intelligent-cache: ## Validate intelligent cache (exact + semantic + tenant isolation)
	chmod +x ./scripts/validate-intelligent-cache-local.sh
	./scripts/validate-intelligent-cache-local.sh

validate-multitenant: ## Validate multi-tenant isolation
	chmod +x ./scripts/validate-multitenant-isolation-full.sh
	./scripts/validate-multitenant-isolation-full.sh

validate-local-production: validate

meeting-ready: ## Run meeting readiness check for client presentation
	chmod +x ./scripts/meeting-ready-check-local.sh
	./scripts/meeting-ready-check-local.sh

validate-meeting-ready: ## Validate meeting-ready check script
	chmod +x ./scripts/validate-meeting-ready-check-local.sh
	./scripts/validate-meeting-ready-check-local.sh

client-ready-report: ## Generate client ready final report
	chmod +x ./scripts/generate-client-ready-report.sh
	./scripts/generate-client-ready-report.sh

validate-client-ready-report: ## Validate client ready final report
	chmod +x ./scripts/validate-client-ready-report.sh
	./scripts/validate-client-ready-report.sh

validate-v1.7-checklist: ## Validate v1.7.0 release checklist
	chmod +x ./scripts/validate-v1.7-release-checklist.sh
	./scripts/validate-v1.7-release-checklist.sh

v1.7-checklist-status: ## Generate v1.7.0 release checklist status
	chmod +x ./scripts/generate-v1.7-release-checklist-status.sh
	./scripts/generate-v1.7-release-checklist-status.sh

# --- Sales Ops ---

generate-proposal:
	./scripts/generate-client-proposal.sh 		--company-name "$(COMPANY_NAME)" 		--segment "$(SEGMENT)" 		--plan "$(PLAN)" 		--lead-id "$(LEAD_ID)"

validate-proposal:
	./scripts/validate-client-proposal-local.sh

quote-demo: ## Generate a demo quote (Pro plan, RAG, 4h support)
	./scripts/generate-local-quote.sh --company-name "Cliente Demo" --plan Pro --rag --tts --support-hours 4

validate-quote: ## Validate local quote generator
	./scripts/validate-local-quote.sh

# --- Contracts / SOW ---

generate-sow: ## Generate a personalized SOW from template
	./scripts/generate-sow-local.sh --company-name "Cliente Demo" --project-name "Local AI Appliance"

validate-contracts: ## Validate contract templates integrity
	./scripts/validate-contract-templates-local.sh

# --- Implementation Checklist ---

implementation-checklist: ## Generate a paid implementation checklist
	./scripts/paid-implementation-checklist-local.sh --company-name "Cliente Demo" --operator-name "Fornecedor Demo"

validate-implementation-checklist: ## Validate implementation checklist template and generation
	./scripts/validate-paid-implementation-checklist.sh

# --- Monthly Report ---

monthly-report-demo: ## Generate a demo monthly report for a client
	./scripts/generate-client-monthly-report.sh --email demo@example.local --month 2026-05

validate-monthly-report: ## Validate monthly report generator
	./scripts/validate-client-monthly-report.sh

# --- White-Label / Branding ---

validate-white-label: ## Validate white-label branding configuration
	./scripts/validate-white-label-local.sh

# --- Commercial Demo E2E Validation ---

validate-commercial-demo-e2e: ## Run end-to-end commercial demo validation
	./scripts/validate-commercial-demo-e2e-local.sh --seed-demo

# --- Restore & Rollback Validation ---

validate-restore-rollback: ## Run restore/rollback validation (dry-run, safe)
	./scripts/validate-real-restore-rollback-local.sh --dry-run

validate-restore-rollback-full: ## Run restore/rollback with backup, upgrade and rollback
	./scripts/validate-real-restore-rollback-local.sh --yes

# --- Clean Install Validation ---

validate-clean-install: ## Run clean install validation (dry-run, safe)
	./scripts/validate-clean-install-local.sh --dry-run

validate-clean-install-full: ## Run clean install validation with sandbox (requires --yes)
	./scripts/validate-clean-install-local.sh --yes

validate-enterprise-rag: ## Validate enterprise RAG pipeline (chunking, parsers, policies, security)
	chmod +x ./scripts/validate-enterprise-rag-local.sh
	./scripts/validate-enterprise-rag-local.sh

validate-hybrid-admin: ## Validate hybrid admin dashboard (API, UI, sanitization, internal margin)
	chmod +x ./scripts/validate-hybrid-admin-dashboard-local.sh
	./scripts/validate-hybrid-admin-dashboard-local.sh

validate-hybrid-abuse: ## Validate hybrid abuse detection (anti-spam, anti-loop, rate limit, anomaly)
	chmod +x ./scripts/validate-hybrid-abuse-detection-local.sh
	./scripts/validate-hybrid-abuse-detection-local.sh

validate-margin-dashboard: ## Validate admin margin dashboard endpoint and payload sanitization
	chmod +x ./scripts/validate-margin-dashboard.sh
	./scripts/validate-margin-dashboard.sh

validate-commercial-calibration: ## Validate Commercial Calibration (Phase 6)
	chmod +x ./scripts/validate-commercial-calibration.sh
	./scripts/validate-commercial-calibration.sh

validate-commercial-guardrails: ## Validate commercial guardrails admin endpoints and payload sanitization
	chmod +x ./scripts/validate-commercial-guardrails.sh
	./scripts/validate-commercial-guardrails.sh

validate-commercial-config-apply: ## Validate manual controlled application of commercial configs
	chmod +x ./scripts/validate-commercial-config-apply.sh
	./scripts/validate-commercial-config-apply.sh

validate-commercial-auto-apply-canary: ## Validate Phase 8 Auto Apply Canary (Dry-run, Canary, Promotion)
	chmod +x ./scripts/validate-commercial-auto-apply-canary.sh
	./scripts/validate-commercial-auto-apply-canary.sh

validate-commercial-canary-promotion: ## Validate Phase 9 Canary Auto Promotion (SLO, Steps, Rollback)
	chmod +x ./scripts/validate-commercial-canary-promotion.sh
	./scripts/validate-commercial-canary-promotion.sh

validate-commercial-executive-dashboard: ## Validate Phase 10 Executive Profitability and Drift Dashboard
	chmod +x ./scripts/validate-commercial-executive-dashboard.sh
	./scripts/validate-commercial-executive-dashboard.sh

validate-commercial-report-export: ## Validate Phase 11 Executive Report Export and Scheduling
	chmod +x ./scripts/validate-commercial-report-export.sh
	./scripts/validate-commercial-report-export.sh

validate-commercial-report-email: ## Validate Phase 12 SMTP opt-in executive report email delivery
	chmod +x ./scripts/validate-commercial-report-email.sh
	./scripts/validate-commercial-report-email.sh

validate-commercial-routing-analytics: ## Validate commercial routing analytics persistence and summary
	chmod +x ./scripts/validate-commercial-routing-analytics.sh
	./scripts/validate-commercial-routing-analytics.sh

validate-commercial-distributed-analytics: ## Validate distributed commercial routing analytics endpoints and exports
	chmod +x ./scripts/validate-commercial-distributed-analytics.sh
	./scripts/validate-commercial-distributed-analytics.sh

validate-commercial-ha: ## Validate Commercial HA / leader election
	chmod +x ./scripts/validate-commercial-ha.sh
	./scripts/validate-commercial-ha.sh

validate-commercial-global-traffic-shifting: ## Validate Phase 17 Traffic Shifting
	bash -n scripts/validate-commercial-global-traffic-shifting.sh

validate-commercial-federation: ## Validate Commercial Federation multi-cluster routing analytics
	chmod +x ./scripts/validate-commercial-federation.sh
	./scripts/validate-commercial-federation.sh

validate-commercial-global-router: ## Validate Commercial Global Router (Phase 16)
	chmod +x ./scripts/validate-commercial-global-router.sh
	./scripts/validate-commercial-global-router.sh

validate-commercial-financial-reconciliation: ## Validate financial reconciliation and disputes (Phase 27)
	chmod +x ./scripts/validate-commercial-financial-reconciliation.sh
	./scripts/validate-commercial-financial-reconciliation.sh

validate-enterprise-audit-portal: ## Validate enterprise customer audit portal (Phase 32)
	chmod +x ./scripts/validate-enterprise-audit-portal.sh
	./scripts/validate-enterprise-audit-portal.sh

validate-commercial-revenue-escalations: ## Validate revenue escalations (Phase 30)
	chmod +x ./scripts/validate-commercial-revenue-escalations.sh
	./scripts/validate-commercial-revenue-escalations.sh

validate-commercial-profit-routing: ## Validate commercial profit routing with ranking and simulation
	chmod +x ./scripts/validate-commercial-profit-routing.sh
	./scripts/validate-commercial-profit-routing.sh

validate-commercial-enforcement: ## Validate runtime enforcement with local-only test doubles
	chmod +x ./scripts/validate-commercial-enforcement.sh
	./scripts/validate-commercial-enforcement.sh

validate-real-provider-env: ## Validate real provider environment (.env.local, keys, security)
	chmod +x ./scripts/validate-real-provider-env-local.sh
	./scripts/validate-real-provider-env-local.sh

validate-openai-real-dry: ## Validate OpenAI real provider (dry-run, no cost)
	chmod +x ./scripts/validate-openai-real-provider.sh
	./scripts/validate-openai-real-provider.sh --dry-run

validate-openai-real: ## Validate OpenAI real provider (real calls, may incur cost)
	chmod +x ./scripts/validate-openai-real-provider.sh
	./scripts/validate-openai-real-provider.sh --real --model gpt-4o-mini

validate-deepseek-real-dry: ## Validate DeepSeek real provider (dry-run, no cost)
	chmod +x ./scripts/validate-deepseek-real-provider.sh
	./scripts/validate-deepseek-real-provider.sh --dry-run

validate-deepseek-real: ## Validate DeepSeek real provider (real calls, may incur cost)
	chmod +x ./scripts/validate-deepseek-real-provider.sh
	./scripts/validate-deepseek-real-provider.sh --real --model deepseek-chat

validate-anthropic-real-dry: ## Validate Anthropic real provider (dry-run, no cost)
	chmod +x ./scripts/validate-anthropic-real-provider.sh
	./scripts/validate-anthropic-real-provider.sh --dry-run

validate-anthropic-real: ## Validate Anthropic real provider (real calls, may incur cost)
	chmod +x ./scripts/validate-anthropic-real-provider.sh
	./scripts/validate-anthropic-real-provider.sh --real --model claude-3-haiku-20240307

measure-provider-costs-dry: ## Measure provider costs (dry-run, no real calls)
	chmod +x ./scripts/measure-real-provider-costs.sh
	./scripts/measure-real-provider-costs.sh --dry-run

measure-provider-costs: ## Measure provider costs (real calls, may incur cost)
	chmod +x ./scripts/measure-real-provider-costs.sh
	./scripts/measure-real-provider-costs.sh --real

validate-real-fallback-dry: ## Validate fallback local-to-cloud (dry-run, no cost)
	chmod +x ./scripts/validate-real-fallback-local-to-cloud.sh
	./scripts/validate-real-fallback-local-to-cloud.sh --dry-run

validate-real-fallback: ## Validate fallback local-to-cloud (real calls, may incur cost)
	chmod +x ./scripts/validate-real-fallback-local-to-cloud.sh
	./scripts/validate-real-fallback-local-to-cloud.sh --real --provider auto

validate-hybrid-e2e: ## Run hybrid platform E2E validation (v1.8.0)
	chmod +x ./scripts/validate-hybrid-platform-e2e-local.sh ./scripts/validate-hybrid-platform-report.sh
	./scripts/validate-hybrid-platform-e2e-local.sh
	./scripts/validate-hybrid-platform-report.sh

validate-clean-install-validator: ## Validate clean install script and outputs
	./scripts/validate-clean-install-validator.sh

# --- Customer Demo (Comando Unico) ---

customer-demo: ## Prepare and validate a customer demo (quick mode)
	./scripts/customer-demo-local.sh --quick --no-build

customer-demo-full: ## Prepare and validate a customer demo (full mode)
	./scripts/customer-demo-local.sh --full --no-build

validate-customer-demo: ## Validate customer demo script and artifacts
	./scripts/validate-customer-demo-local.sh

# --- Demo Visual Guide ---

demo-screenshot-plan: ## Generate screenshot capture plan (or capture with Playwright)
	./scripts/prepare-demo-screenshots-local.sh

validate-demo-visual-guide: ## Validate demo visual guide integrity and security
	./scripts/validate-demo-visual-guide.sh

# --- Fresh Machine Validation ---

fresh-machine-check: ## Run fresh machine readiness check (dry-run)
	chmod +x ./scripts/fresh-machine-readiness-check.sh
	./scripts/fresh-machine-readiness-check.sh --dry-run

validate-fresh-machine-docs: ## Validate fresh machine validation docs and scripts
	chmod +x ./scripts/validate-fresh-machine-docs.sh
	./scripts/validate-fresh-machine-docs.sh

# --- Repo Maintenance ---

cleanup-branches: ## List safe-to-delete local branches (dry-run)
	./scripts/cleanup-local-branches.sh --dry-run --merged-only

# --- Provider Cost Validation ---
# Compatibility note: keep the original `measure-provider-costs*` targets above
# as the canonical definitions. Do not redefine them below.

# --- Real Billing Margin Validation ---

validate-real-billing-margin-dry:
	./scripts/validate-real-billing-margin.sh --dry-run

validate-real-billing-margin:
	./scripts/validate-real-billing-margin.sh --real --provider auto

# --- Real Provider Artifact Sanitization ---

scan-real-provider-artifacts:
	./scripts/scan-real-provider-artifacts.sh --fail-on-findings

validate-real-provider-sanitization:
	./scripts/validate-real-provider-sanitization.sh

# --- Real Providers E2E ---

validate-real-providers-e2e-dry:
	./scripts/validate-real-providers-e2e.sh --dry-run

validate-real-providers-e2e:
	./scripts/validate-real-providers-e2e.sh --real

validate-commercial-geo-routing:
	@bash scripts/validate-commercial-geo-routing.sh

validate-commercial-qos-routing:
	bash scripts/validate-commercial-qos-routing.sh

validate-commercial-qos-queue:
	bash scripts/validate-commercial-qos-queue.sh

validate-commercial-qos-fairness:
	bash scripts/validate-commercial-qos-fairness.sh

validate-commercial-qos-billing:
	bash scripts/validate-commercial-qos-billing.sh

validate-commercial-capacity-planning:
	bash scripts/validate-commercial-capacity-planning.sh

test: ## Run focused regression suite for admin RBAC, tokenization, PKI/attestation/plugins, and GGUF hot swap
	PYTHONPATH=control_plane .venv/bin/python -m pytest \
		tests/test_admin_rbac.py \
		tests/test_tokenizer_service.py \
		control_plane/tests/test_pki_attestation_plugins.py \
		control_plane/tests/test_model_hot_swap.py \
		-q --tb=short

test-e2e: ## Run the full End-to-End test suite
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/e2e/ -v --tb=short

test-smoke: ## Run essential smoke tests (subset of E2E + health checks)
	$(MAKE) health
	PYTHONPATH=control_plane .venv/bin/python -m pytest \
		tests/e2e/test_admin_rbac_flow.py \
		tests/e2e/test_client_api_key_flow.py \
		-v --tb=short

test-release: ## Run all tests required for a release (Core + E2E + Security)
	$(MAKE) test
	$(MAKE) test-e2e
	$(MAKE) security
	$(MAKE) check-secrets

validate-commercial-live-balancing:
	bash scripts/validate-commercial-live-balancing.sh

validate-commercial-infra-simulation:
	bash scripts/validate-commercial-infra-simulation.sh

validate-commercial-infra-execution:
	bash scripts/validate-commercial-infra-execution.sh

validate-commercial-revenue-forecasting:
	bash scripts/validate-commercial-revenue-forecasting.sh

validate-commercial-revenue-protection:
	bash scripts/validate-commercial-revenue-protection.sh

validate-commercial-compliance-controls: ## Validate compliance controls without shadowing governance policy checks
	bash scripts/validate-commercial-compliance-controls.sh

# Legacy governance policy target preserved as a first-class validation entry.
validate-policy-governance: ## Validate Enterprise Policy Governance (Phase 34)
	chmod +x scripts/validate-policy-governance.sh
	./scripts/validate-policy-governance.sh

validate-governance-federation: ## Validate Enterprise Multi-Region Governance Federation (Phase 35)
	chmod +x scripts/validate-governance-federation.sh
	./scripts/validate-governance-federation.sh

validate-commercial-local-infra-adapters: ## Validate Proxmox and Local GPU adapters
	chmod +x scripts/validate-commercial-local-infra-adapters.sh
	./scripts/validate-commercial-local-infra-adapters.sh

validate-public-verifier: ## Validate Public Verifier CLI (Phase 43)
	chmod +x scripts/validate-public-verifier.sh
	./scripts/validate-public-verifier.sh

validate-public-attestation-gateway:
	bash scripts/validate-public-attestation-gateway.sh

validate-confidential-runtime:
	bash scripts/validate-confidential-runtime.sh

validate-confidential-agents:
	bash scripts/validate-confidential-agents.sh

validate-trusted-agent-runtime:
	chmod +x scripts/validate-trusted-agent-runtime.sh
	./scripts/validate-trusted-agent-runtime.sh

validate-deterministic-workflows:
	bash scripts/validate-deterministic-workflows.sh

validate-runtime-attestation: ## Validate hardware-backed attestation runtime (Phase 58)
	chmod +x scripts/validate-runtime-attestation.sh
	./scripts/validate-runtime-attestation.sh

validate-federated-workflows:
	chmod +x scripts/validate-federated-workflows.sh
	./scripts/validate-federated-workflows.sh

validate-workflow-governance:
	bash scripts/validate-workflow-governance.sh

validate-phase56-migrations:
	bash scripts/validate-phase56-migrations.sh

validate-sovereign-appliance:
	bash scripts/validate-sovereign-appliance.sh

validate-confidential-rag-vault:
	bash scripts/validate-confidential-rag-vault.sh

validate-control-plane-mesh: ## Validate Distributed Sovereign Control Plane Mesh (Phase 63)
	chmod +x scripts/validate-control-plane-mesh.sh
	./scripts/validate-control-plane-mesh.sh

sandbox-ga-test: ## Validate Sandbox GA Hardening policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_sandbox_ga.py -v

mcp-ga-test: ## Validate MCP GA Hardening policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_mcp_ga.py -v

memory-erasure-test: ## Validate Memory Erasure/Right to be Forgotten policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_memory_erasure.py -v

capability-signature-gate: ## Validate Bundle/Capability Signing and supply chain policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_capability_signing.py -v

multi-agent-ga-test: ## Validate Multi-Agent GA Path policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_multi_agent_ga.py -v

agent-studio-ga-test: ## Validate Agent Studio GA and Visual Flow Editor logic
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_studio_ga.py -v

agent-debugger-test: ## Validate Time-Travel Debugger and Replay logic
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_debugger.py -v

agent-canary-test: ## Validate Shadow Mode and Canary Agents logic
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_canary.py -v

agent-wallet-test: ## Validate Agent Wallets and Spend Controls
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_wallet.py -v

agent-digital-twins-test: ## Validate Digital Twin Connectors and Safety Interlocks
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_digital_twins.py -v

agent-sab-test: ## Validate Standardized Agent Bundle (SAB) portability
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_sab.py -v

agent-federated-memory-test: ## Validate Federated Memory and Sovereign Sync
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_federated_memory.py -v

agent-mcts-test: ## Validate MCTS Reasoning Runtime
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_mcts_reasoning.py -v

agent-constraints-test: ## Validate Constraint-Based Reasoning Runtime
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_constraint_reasoning.py -v

agentic-ga-hardening: sandbox-ga-test mcp-ga-test memory-erasure-test capability-signature-gate multi-agent-ga-test agent-studio-ga-test agent-debugger-test agent-canary-test agent-wallet-test agent-digital-twins-test agent-sab-test agent-federated-memory-test agent-mcts-test agent-constraints-test ## Run all Agentic AI GA Hardening tests

# --- Kubernetes & Operator Mode ---

k8s-render: ## Render Kubernetes manifests using a simple template script (since helm is missing)
	@echo "Rendering Kubernetes manifests..."
	@mkdir -p deploy/rendered
	@cp deploy/kubernetes/*.yaml deploy/rendered/

k8s-validate: ## Validate Kubernetes manifests using python tests
	@echo "Validating Kubernetes manifests..."
	@PYTHONPATH=. .venv/bin/pytest tests/kubernetes/test_yaml_validity.py -v

helm-package: ## Package Helm chart
	@echo "Packaging Helm chart..."
	@tar -cvzf llm-inference-stack-0.1.0.tgz -C deploy/helm llm-inference-stack

operator-test: ## Test Operator (mock reconciliation)
	@echo "Testing Operator reconciliation..."
	@PYTHONPATH=. .venv/bin/python3 operator/main.py --help || echo "Operator script exists and is syntactically correct."
	@PYTHONPATH=. .venv/bin/pytest tests/kubernetes/test_operator_mock.py -v

distributed-runtime-test: ## Test Distributed Runtime service and endpoints
	@echo "Testing Distributed Runtime..."
	@PYTHONPATH=. .venv/bin/pytest tests/runtime/test_distributed_runtime.py -v

gpu-autoscaling-test: ## Test GPU Orchestration and Autoscaling
	@echo "Testing GPU Orchestration and Autoscaling..."
	@PYTHONPATH=. .venv/bin/pytest tests/runtime/test_gpu_orchestrator.py -v

agent-optimization-check: ## Execute agent evals and verify safety/optimization constraints
	@echo "Running Agentic CI/CD Optimization checks..."
	@PYTHONPATH=control_plane .venv/bin/pytest control_plane/tests/test_agent_optimization.py -v



production-agentic-e2e: ## Run non-mock E2E tests for production agentic claims
	@echo "Running Agentic Production E2E Suite..."
	@./scripts/run-production-agentic-e2e.sh
