SHELL := /bin/bash
export PATH := $(CURDIR)/venv/bin:$(CURDIR)/.venv/bin:$(PATH)

# Default target
.DEFAULT_GOAL := help

validate-release-readiness: ## Validate that all mandatory files and hygiene standards for release are met
	@python3 scripts/validate_release_readiness.py

# --- Standardized Commands ---

# Backend (Python)
backend-lint: ## Run backend linting
	@.venv/bin/ruff check .

backend-test: ## Run backend tests
	@.venv/bin/pytest tests/unit tests/integration -m "not slow"

backend-typecheck: ## Run backend type checking
	@.venv/bin/mypy .

generate-sbom: ## Generate CycloneDX SBOM for the Control Plane
	@python3 scripts/generate_sbom.py

generate-route-surface: ## Generate API route surface manifest
	@PYTHONPATH=.:control_plane uv run python3 scripts/generate_route_surface_manifest.py

validate-route-surface: ## Validate API route surface governance
	@$(MAKE) generate-route-surface
	@python3 scripts/validate_route_surface.py

generate-docs: ## Generate all automated documentation
	@$(MAKE) generate-route-surface
	@PYTHONPATH=.:control_plane uv run python3 scripts/generate_docs.py

validate-docs: ## Validate that generated docs are up to date
	@$(MAKE) generate-docs
	@python3 scripts/validate_generated_docs.py
	@git diff --exit-code docs/generated || (echo "Error: Generated docs are out of sync. Commit the changes." && exit 1)

validate-deprecated-surface: ## Validate all deprecated surfaces have owners, replacements, and removal deadlines
	@python3 scripts/validate_deprecated_surface.py

validate-mock-surface: ## Detect mocks/placeholders in supported/core endpoints
	@python3 scripts/detect_supported_surface_mocks.py

validate-all-surfaces: validate-route-surface validate-deprecated-surface validate-mock-surface ## Validate all surface governance

validate-surface-governance: ## Validate route surface + deprecated surface governance (CI gate)
	@$(MAKE) validate-route-surface
	@$(MAKE) validate-deprecated-surface

test-backup-components: ## Run fast backup/restore unit tests (SQLite, idempotency, redaction, no DR)
	@PYTHONPATH=.:control_plane BACKUP_RESTORE_ENABLED=true .venv/bin/pytest \
		tests/backup/test_backup_restore_sqlite.py \
		tests/backup/test_idempotency.py \
		-q --timeout=120 \
		--junitxml=artifacts/reports/backup-components.xml

test-backup-dr: ## Run full DR scenario tests (backup + restore + rollback, SQLite + Postgres)
	@PYTHONPATH=.:control_plane BACKUP_RESTORE_ENABLED=true .venv/bin/pytest tests/backup_dr/ tests/backup/test_backup_restore_postgres.py -q --timeout=300 -m "backup_dr"

generate-lockfile: ## Regenerate reproducible lockfile
	@uv lock

# Frontend (Node)
frontend-lint: ## Run frontend linting
	@npm run lint --workspaces --if-present

frontend-test: ## Run frontend tests
	@npm run test --workspaces --if-present

frontend-build: ## Run frontend builds
	@npm run build --workspaces --if-present

frontend-typecheck: ## Run frontend type checking
	@npm run typecheck --workspaces --if-present

# SDK
sdk-build: ## Build SDKs
	@npm run build --workspace=sdk/node
	@cd sdk/python && python -m build

sdk-test: ## Test SDKs
	@npm run test --workspace=sdk/node
	@pytest sdk/python/tests

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

# (moved to makefiles/quality.mk)

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

# (moved to makefiles/operations.mk)

help: ## Show this help message
	@echo "LLM Inference Stack - Operator Commands"
	@echo "Usage: make <target> [BACKUP_DIR=/path/to/backup]"
	@echo ""
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

validate-llm-harness: ## Validate only the modular LLM harness
	@bash scripts/validators/validate-llm-harness.sh

integration-local-llm-harness: ## Run integration tests against a real local LLM (requires env vars)
	@echo "Running local LLM integration tests..."
	@bash scripts/validators/validate-local-llm-harness-env.sh
	@PYTHONPATH=. .venv/bin/python3 -m pytest -m "integration and local_llm" tests/integration/llm_harness/integration/test_local_openai_compatible.py

docker-build-llm-harness: ## Build the LLM Harness standalone Docker image
	@echo "Building LLM Harness image..."
	@docker build -t llm-harness:latest -f docker/llm-harness/Dockerfile .

docker-run-llm-harness-help: ## Run LLM Harness help inside container
	@docker run --rm llm-harness:latest --help

docker-run-llm-harness-health: ## Run LLM Harness health check inside container
	@docker run --rm llm-harness:latest health --local-only

typecheck-llm-harness: ## Run mypy type checking on the LLM harness
	@echo "Running mypy on LLM harness..."
	@.venv/bin/mypy --config-file scripts/llm_harness/pyproject.toml scripts/llm_harness

release-gate-llm-harness: ## Run the isolated release gate for the modular LLM harness
	@$(MAKE) validate-llm-harness
	@PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli --help >/dev/null
	@PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli code --help >/dev/null
	@PYTHONPATH=. .venv/bin/python3 -m scripts.llm_harness.cli health --local-only >/dev/null
	@./scripts/dev/agent-test.sh --help >/dev/null
	@PYTHONPATH=. .venv/bin/python3 scripts/llm_harness/release_gate.py
	@echo "LLM harness release gate completed successfully."

operational-readiness: ## Run the Operational Readiness Pack validation
	@bash scripts/dev/operational-readiness-pack.sh

release-gate: agentic-ga-hardening ## Run the release gate validator (Requires TAG=vX.Y.Z)
	@bash scripts/release/release-gate.sh $(TAG)

verify-release-artifacts: ## Verify artifact governance and generate checksums (Requires TAG=vX.Y.Z)
	@bash scripts/validators/verify-release-artifacts.sh $(TAG)

chaos-list: ## List all available chaos experiments
	@bash scripts/chaos-list.sh

chaos-run-safe: ## Run a safe chaos experiment (Requires ID=exp-id)
	@bash scripts/dev/chaos-run.sh $(ID) --safe

chaos-report: ## Generate chaos experiment report (Requires RUN_ID=run-id)
	@bash scripts/chaos-report.sh $(RUN_ID)

compliance-evidence: ## Collect and package compliance evidence (SOC 2 / ISO 27001)
	@mkdir -p artifacts/compliance/latest
	@bash scripts/dev/collect-compliance-evidence.sh
	@bash scripts/dev/generate-compliance-pack.sh

compliance-check: ## Run compliance readiness lint and audit
	@bash scripts/validators/compliance-check.sh

compliance-release-gate: ## Validate compliance criteria for release (Requires TAG=vX.Y.Z)
	@bash scripts/release/compliance-release-gate.sh $(TAG)

platform-freeze-check: ## Verify architectural freeze rules
	@chmod +x scripts/validators/platform-freeze-check.sh scripts/validators/platform-freeze-check.py
	@bash scripts/validators/platform-freeze-check.sh

check-feature-flags-integrity: ## Validate feature flags integrity
	@chmod +x scripts/validators/check-feature-flags-integrity.sh scripts/validators/check-feature-flags-integrity.py
	@bash scripts/validators/check-feature-flags-integrity.sh

check-supported-surface: ## Reconcile and audit supported surface capabilities
	@chmod +x scripts/validators/check-supported-surface.sh scripts/validators/check_supported_surface.py
	@bash scripts/validators/check-supported-surface.sh

check-freeze-governance: ## Run platform freeze and governance checks
	@chmod +x scripts/validators/check-freeze-governance.sh
	@bash scripts/validators/check-freeze-governance.sh

# (moved to makefiles/agent.mk and makefiles/operations.mk)

agentic-up: ## Start stack with agentic profile (includes agent-worker)
	./scripts/deploy/up.sh --profile agentic

agentic-readiness: ## Run Agentic Runtime Readiness Checks
	@chmod +x scripts/dev/agentic-readiness.sh
	@./scripts/dev/agentic-readiness.sh

agentic-production-on-readiness: ## Validate Agentic Production-ON readiness (runtime live, not safe-default)
	@chmod +x scripts/validators/validate-agentic-production-on.sh
	@AGENTIC_PRODUCTION_ON_VALIDATION=true ./scripts/validators/validate-agentic-production-on.sh
# (moved to makefiles/operations.mk)

validate-control-center: ## Validate System Control Center (Backend + UI)
	./scripts/validators/validate-system-control-center-local.sh

validate-operational-controls: ## Validate operational controls governance flows
	chmod +x ./scripts/validators/validate-operational-controls.sh
	./scripts/validators/validate-operational-controls.sh

validate-tenant-encryption: ## Validate tenant encryption controls (Phase 36)
	chmod +x scripts/validators/validate-tenant-encryption.sh
	./scripts/validators/validate-tenant-encryption.sh

validate-sovereign-airgap-governance: ## Validate sovereign airgap governance controls (Phase 37)
	chmod +x scripts/validators/validate-sovereign-airgap-governance.sh
	./scripts/validators/validate-sovereign-airgap-governance.sh

validate-model-supply-chain: ## Validate secure model supply chain controls (Phase 38)
	chmod +x scripts/validators/validate-model-supply-chain.sh
	./scripts/validators/validate-model-supply-chain.sh

validate-model-integrity-monitor: ## Validate runtime model integrity monitor (Phase 39)
	chmod +x scripts/validators/validate-model-integrity-monitor.sh
	./scripts/validators/validate-model-integrity-monitor.sh

validate-cryptographic-receipts: ## Validate cryptographic inference receipts (Phase 41)
	chmod +x scripts/validators/validate-cryptographic-receipts.sh
	./scripts/validators/validate-cryptographic-receipts.sh

validate-rag-vault: ## Validate regulated RAG vault controls (Phase 48)
	chmod +x scripts/validators/validate-rag-vault.sh
	./scripts/validators/validate-rag-vault.sh

validate-retrieval-proofs: ## Validate retrieval proofs + context lineage (Phase 49)
	chmod +x scripts/validators/validate-retrieval-proofs.sh
	./scripts/validators/validate-retrieval-proofs.sh

validate-architecture-boundaries: ## Validate architecture boundaries for the stabilization cycle
	python3 ./scripts/validators/validate_architecture_boundaries.py

validate-runtime-contracts: ## Validate core runtime contract documentation
	python3 ./scripts/validators/validate_runtime_contracts.py

validate-domain-contracts: ## Validate lightweight domain contracts for modularization
	python3 ./scripts/validators/validate_domain_contracts.py

validate-invariants: ## Validate lightweight advisory invariants
	python3 ./scripts/validators/validate_invariants.py

validate-adrs: ## Validate Architectural Decision Records
	python3 ./scripts/validators/validate_adrs.py

validate-platform-architecture: ## Run unified platform architecture validation suite
	python3 ./scripts/validators/validate_platform_architecture.py

validate-phase-82-platform-sustainability: ## Validate Phase 82 platform sustainability, governance core and dry-run recovery
	# python3 ./scripts/validators/validate_phase_82_platform_sustainability.py
	python3 ./scripts/validators/validate_platform_boundaries.py
	.venv/bin/python -m pytest \
		tests/architecture/test_platform_boundaries.py \
		tests/architecture/test_domain_dependency_graph.py \
		tests/integration/governance/test_policy_dsl.py \
		tests/integration/governance/test_phase_82_policy_engine.py \
		tests/integration/governance/test_policy_conflicts.py \
		tests/integration/governance/test_data_governance.py \
		tests/integration/governance/test_human_governance_workflows.py \
		tests/integration/governance/test_phase_82_governance_core.py \
		tests/integration/operations/test_deterministic_events.py \
		tests/integration/operations/test_sovereign_observability.py \
		tests/integration/operations/test_disaster_recovery.py \
		tests/integration/operations/test_phase_82_operations_core.py \
		tests/test_router_presence.py \
		-q --tb=short

validate-claims: ## Validate documentation and scripts for prohibited claims
	python3 ./scripts/validators/validate_claims.py

validate-governance-documentation-foundation: ## Validate Governance Documentation Foundation before Phase 79
	python3 ./scripts/validators/validate_governance_documentation_foundation.py
	.venv/bin/python -m pytest tests/integration/docs/test_governance_documentation_foundation.py -q --tb=short

validate-release-engineering: ## Validate release engineering and operational stability baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/validators/validate_release_engineering.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/integration/releases/ -q --tb=short

generate-release-baseline: ## Generate deterministic platform release baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/release/generate_release_baseline.py

validate-framework-warnings: ## Validate framework warnings and deprecations
	PYTHONPATH=control_plane .venv/bin/python scripts/validators/validate_framework_warnings.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/integration/quality/test_framework_warnings.py -q --tb=short

# (moved to makefiles/quality.mk)

validate-dependency-graph: ## Validate architectural dependency graph
	PYTHONPATH=control_plane .venv/bin/python scripts/validators/validate_dependency_graph.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/architecture/test_dependency_graph_hardening.py -q --tb=short

# (moved to makefiles/quality.mk)

validate-internal-security-review: ## Validate internal security review
	PYTHONPATH=control_plane .venv/bin/python scripts/validators/validate_internal_security_review.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/integration/security/test_internal_security_review.py -q --tb=short

validate-naming-consistency: ## Validate naming and API consistency
	PYTHONPATH=control_plane .venv/bin/python scripts/validators/validate_naming_consistency.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/architecture/test_naming_consistency.py -q --tb=short

validate-v1-readiness: ## Validate v1 readiness criteria
	PYTHONPATH=control_plane .venv/bin/python scripts/validators/validate_v1_readiness.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/integration/releases/test_v1_readiness.py -q --tb=short

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
	validate-route-surface \
	validate-docs \
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
	validate-v1-readiness \
	validate-mock-surface

validate-architecture-smoke hygiene-check: ## Run smoke validation (static checks + short tests, no slow integration)
	@echo "Running smoke validation (fast path, no integration tests)"
	@set -e; for target in $(SMOKE_VALIDATION_TARGETS); do \
		echo "==> $$target"; \
		$(MAKE) --no-print-directory $$target; \
	done
	@echo "--- Phase validator scripts (static checks, no slow pytest) ---"
	# python3 ./scripts/validators/validate_phase_69_failure_forecasting.py --smoke # Broken: docs/VALIDATORS_STATUS.md
	# python3 ./scripts/validators/validate_phase_70_correlation_engine.py # Broken: docs/VALIDATORS_STATUS.md
	python3 ./scripts/validators/validate_phase_71_remediation_planning.py --smoke
	python3 ./scripts/validators/validate_phase_72_remediation_execution.py --smoke
	python3 ./scripts/validators/validate_phase_73_adapter_sandbox.py --smoke
	python3 ./scripts/validators/validate_phase_74_adapter_registry.py --smoke
	python3 ./scripts/validators/validate_phase_75_adapter_promotion.py --smoke
	# ./.venv/bin/python scripts/validators/validate_phase_76_attestation_framework.py # Broken: docs/VALIDATORS_STATUS.md
	# ./.venv/bin/python scripts/validators/validate_phase_77_federation_sync.py # Broken: docs/VALIDATORS_STATUS.md
	# python3 ./scripts/validators/validate_phase_78_compatibility_contracts.py # Broken: docs/VALIDATORS_STATUS.md
	# python3 ./scripts/validators/validate_phase_79_plugin_runtime.py # Broken: docs/VALIDATORS_STATUS.md
	# python3 ./scripts/validators/validate_phase_80_plugin_supply_chain.py # Broken: docs/VALIDATORS_STATUS.md
	# python3 ./scripts/validators/validate_phase_81_reproducible_builds.py # Broken: docs/VALIDATORS_STATUS.md
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

# (moved to makefiles/quality.mk)

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
	@$(MAKE) validate-docs
	python3 ./scripts/docs/generate_docs_site.py --check
	python3 ./scripts/docs/check_links.py
	python3 ./scripts/validators/validate_platform_documentation.py
	python3 ./scripts/validators/check-doc-consistency.py
	python3 -m pytest tests/integration/docs/test_platform_documentation.py -q --tb=short

docs-build: ## Build centralized MkDocs portal
	@$(MAKE) generate-docs
	python3 ./scripts/docs/generate_docs_site.py
	mkdocs build --strict

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

security-scan: ## Run automated security scanning (Bandit & Semgrep)
	@python3 scripts/validators/validate_security_scan.py

# Compatibility alias for older automation that expects a single Makefile
# governance checker target instead of the documentation/runtime split.
validate-makefile-governance: ## Validate Makefile governance structure, docs and tests
	python3 ./scripts/validators/validate_makefile_governance.py
	.venv/bin/python -m pytest tests/integration/build/test_makefile_governance.py -q --tb=short

validate-phase-66-readiness: ## Validate readiness gate before Phase 66 implementation
	# python3 ./scripts/validators/validate_phase_66_readiness.py

validate-phase-69-failure-forecasting: ## Validate Phase 69 Predictive Failure Signals + Deterministic Forecasting
	# python3 ./scripts/validators/validate_phase_69_failure_forecasting.py # Broken: docs/VALIDATORS_STATUS.md
	# Targeted test list — do NOT run tests/integration/operations/ broadly to avoid
	# excessive execution in the validate-architecture aggregate.
	# .venv/bin/python -m pytest ... -q --tb=short

validate-phase-70-correlation-engine: ## Validate Phase 70 Deterministic Operations Correlation Engine
	# python3 ./scripts/validators/validate_phase_70_correlation_engine.py # Broken: docs/VALIDATORS_STATUS.md
	# .venv/bin/python -m pytest ... -q --tb=short

validate-phase-71-remediation-planning: ## Validate Phase 71 Deterministic Remediation Planning
	python3 ./scripts/validators/validate_phase_71_remediation_planning.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_remediation_planning_models.py \
		tests/integration/operations/test_deterministic_remediation_planner.py \
		tests/integration/operations/test_remediation_blast_radius.py \
		tests/integration/operations/test_remediation_approval_requirements.py \
		tests/integration/operations/test_remediation_receipts.py \
		tests/integration/operations/test_remediation_audit_events.py \
		tests/integration/operations/test_remediation_planning_api.py \
		tests/integration/operations/test_remediation_planning_dashboard.py \
		tests/integration/operations/test_phase_71_validation.py \
		-q --tb=short

validate-phase-72-remediation-execution: ## Validate Phase 72 Approval-Gated Remediation Execution
	python3 ./scripts/validators/validate_phase_72_remediation_execution.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_remediation_execution_models.py \
		tests/integration/operations/test_remediation_execution_gate.py \
		tests/integration/operations/test_remediation_simulation_adapter.py \
		tests/integration/operations/test_approval_gated_remediation_executor.py \
		tests/integration/operations/test_remediation_execution_rollback.py \
		tests/integration/operations/test_remediation_execution_receipts.py \
		tests/integration/operations/test_remediation_execution_audit_events.py \
		tests/integration/operations/test_remediation_execution_api.py \
		tests/integration/operations/test_remediation_execution_dashboard.py \
		tests/integration/operations/test_phase_72_validation.py \
		-q --tb=short

validate-phase-73-adapter-sandbox: ## Validate Phase 73 Controlled Adapter Sandbox
	python3 ./scripts/validators/validate_phase_73_adapter_sandbox.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_adapter_sandbox_models.py \
		tests/integration/operations/test_adapter_contracts.py \
		tests/integration/operations/test_adapter_manifest_validator.py \
		tests/integration/operations/test_adapter_sandbox_context.py \
		tests/integration/operations/test_adapter_simulation_runner.py \
		tests/integration/operations/test_adapter_policy_guard.py \
		tests/integration/operations/test_adapter_sandbox_receipts.py \
		tests/integration/operations/test_adapter_sandbox_audit_events.py \
		tests/integration/operations/test_adapter_sandbox_api.py \
		tests/integration/operations/test_adapter_sandbox_dashboard.py \
		tests/integration/operations/test_phase_73_validation.py \
		-q --tb=short

validate-phase-74-adapter-registry: ## Validate Phase 74 Signed Adapter Registry
	python3 ./scripts/validators/validate_phase_74_adapter_registry.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_adapter_registry_models.py \
		tests/integration/operations/test_adapter_registry_hash_utils.py \
		tests/integration/operations/test_signed_adapter_registry_service.py \
		tests/integration/operations/test_adapter_registry_policy_engine.py \
		tests/integration/operations/test_adapter_registry_allowlist_blocklist.py \
		tests/integration/operations/test_adapter_registry_receipts.py \
		tests/integration/operations/test_adapter_registry_audit_events.py \
		tests/integration/operations/test_adapter_registry_api.py \
		tests/integration/operations/test_adapter_registry_dashboard.py \
		tests/integration/operations/test_phase_74_validation.py \
		-q --tb=short

validate-phase-75-adapter-promotion: ## Validate Phase 75 Adapter Promotion Workflow
	python3 ./scripts/validators/validate_phase_75_adapter_promotion.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_adapter_promotion_models.py \
		tests/integration/operations/test_adapter_promotion_hash_utils.py \
		tests/integration/operations/test_adapter_promotion_gates.py \
		tests/integration/operations/test_adapter_promotion_workflow_service.py \
		tests/integration/operations/test_adapter_promotion_staging_simulation.py \
		tests/integration/operations/test_adapter_promotion_receipts.py \
		tests/integration/operations/test_adapter_promotion_audit_events.py \
		tests/integration/operations/test_adapter_promotion_api.py \
		tests/integration/operations/test_adapter_promotion_dashboard.py \
		tests/integration/operations/test_phase_75_validation.py \
		-q --tb=short

validate-phase-78-compatibility-contracts: ## Validate Phase 78 Compatibility Contracts & Version Negotiation
	# python3 ./scripts/validators/validate_phase_78_compatibility_contracts.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_compatibility_models.py \
		tests/integration/operations/test_compatibility_hash_utils.py \
		tests/integration/operations/test_semantic_versioning.py \
		tests/integration/operations/test_compatibility_matrix.py \
		tests/integration/operations/test_version_negotiation.py \
		tests/integration/operations/test_capability_negotiation.py \
		tests/integration/operations/test_deprecation_lifecycle.py \
		tests/integration/operations/test_compatibility_verification.py \
		tests/integration/operations/test_compatibility_receipts.py \
		tests/integration/operations/test_compatibility_audit_events.py \
		tests/integration/operations/test_compatibility_api.py \
		tests/integration/operations/test_compatibility_dashboard.py \
		tests/integration/operations/test_phase_78_validation.py \
		-q --tb=short

validate-phase-79-plugin-runtime: ## Validate Phase 79 Formal Plugin ABI & Extension Runtime
	# python3 ./scripts/validators/validate_phase_79_plugin_runtime.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_plugin_runtime_models.py \
		tests/integration/operations/test_plugin_runtime_hash_utils.py \
		tests/integration/operations/test_plugin_abi_contracts.py \
		tests/integration/operations/test_plugin_capability_boundaries.py \
		tests/integration/operations/test_plugin_runtime_compatibility_enforcer.py \
		tests/integration/operations/test_plugin_extension_loader.py \
		tests/integration/operations/test_plugin_isolation_policy.py \
		tests/integration/operations/test_plugin_lifecycle.py \
		tests/integration/operations/test_plugin_replay_verifier.py \
		tests/integration/operations/test_plugin_federation_compatibility.py \
		tests/integration/operations/test_plugin_runtime_receipts.py \
		tests/integration/operations/test_plugin_runtime_audit_events.py \
		tests/integration/operations/test_plugin_runtime_api.py \
		tests/integration/operations/test_plugin_runtime_dashboard.py \
		tests/integration/operations/test_phase_79_validation.py \
		-q --tb=short

validate-phase-80-plugin-supply-chain: ## Validate Phase 80 Plugin Supply-Chain Provenance & SBOM Placeholder Framework
	# python3 ./scripts/validators/validate_phase_80_plugin_supply_chain.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_plugin_supply_chain_models.py \
		tests/integration/operations/test_plugin_supply_chain_hash_utils.py \
		tests/integration/operations/test_plugin_supply_chain_services.py \
		tests/integration/operations/test_plugin_supply_chain_api.py \
		tests/integration/operations/test_plugin_supply_chain_dashboard.py \
		tests/integration/operations/test_phase_80_validation.py \
		-q --tb=short

validate-phase-81-reproducible-builds: ## Validate Phase 81 Reproducible Build & Artifact Verification Framework
	# python3 ./scripts/validators/validate_phase_81_reproducible_builds.py
	.venv/bin/python -m pytest \
		tests/integration/operations/test_reproducible_build_models.py \
		tests/integration/operations/test_reproducible_build_hash_utils.py \
		tests/integration/operations/test_reproducible_build_service.py \
		tests/integration/operations/test_artifact_verification.py \
		tests/integration/operations/test_source_artifact_lineage.py \
		tests/integration/operations/test_build_environment_policy.py \
		tests/integration/operations/test_artifact_replay_verifier.py \
		tests/integration/operations/test_reproducible_build_provenance_integration.py \
		tests/integration/operations/test_reproducible_build_receipts.py \
		tests/integration/operations/test_reproducible_build_audit_events.py \
		tests/integration/operations/test_reproducible_build_api.py \
		tests/integration/operations/test_reproducible_build_dashboard.py \
		tests/integration/operations/test_phase_81_validation.py \
		-q --tb=short

validate-phase-76-attestation-framework: ## Validate Sovereign Execution Attestation Framework (Phase 76)
	# ./.venv/bin/python scripts/validators/validate_phase_76_attestation_framework.py
	./.venv/bin/python -m pytest \
		tests/integration/operations/test_attestation_framework_models.py \
		tests/integration/operations/test_attestation_hash_utils.py \
		tests/integration/operations/test_attestation_service.py \
		tests/integration/operations/test_attestation_federation_bundle.py \
		tests/integration/operations/test_attestation_trust_policy_engine.py \
		tests/integration/operations/test_attestation_replay_verifier.py \
		tests/integration/operations/test_attestation_receipts.py \
		tests/integration/operations/test_attestation_audit_events.py \
		tests/integration/operations/test_attestation_api.py \
		tests/integration/operations/test_attestation_dashboard.py \
		tests/integration/operations/test_phase_76_validation.py \
		-q --tb=short

validate-phase-77-federation-sync: ## Validate Sovereign Federation Synchronization Protocol (Phase 77)
	# ./.venv/bin/python scripts/validators/validate_phase_77_federation_sync.py
	./.venv/bin/python -m pytest \
		tests/integration/operations/test_federation_sync_models.py \
		tests/integration/operations/test_federation_hash_utils.py \
		tests/integration/operations/test_federation_environment_registry.py \
		tests/integration/operations/test_federation_synchronization_protocol.py \
		tests/integration/operations/test_federation_trust_negotiation.py \
		tests/integration/operations/test_federation_conflict_resolution.py \
		tests/integration/operations/test_federation_replay_verifier.py \
		tests/integration/operations/test_federation_receipts.py \
		tests/integration/operations/test_federation_audit_events.py \
		tests/integration/operations/test_federation_api.py \
		tests/integration/operations/test_federation_dashboard.py \
		tests/integration/operations/test_phase_77_validation.py \
		-q --tb=short
validate-execution-proofs: ## Validate verifiable AI execution proofs + Merkle audit timelines (Phase 60)
	chmod +x scripts/validators/validate-execution-proofs.sh
	./scripts/validators/validate-execution-proofs.sh

validate-inference-reproducibility: ## Validate deterministic inference audit + replay controls (Phase 40)
	chmod +x scripts/validators/validate-inference-reproducibility.sh
	./scripts/validators/validate-inference-reproducibility.sh

validate-post-install: ## Run post-installation validation
	./scripts/validators/validate-post-install-local.sh --with-demo

repo-hygiene: ## Run repository hygiene check
	@bash scripts/repo_hygiene_check.sh

validate-quick: repo-hygiene ## Quick production validation
	VALIDATION_MODE=quick ./scripts/validators/validate-local-production-full.sh

validate-full: ## Full production validation
	VALIDATION_MODE=full ./scripts/validators/validate-local-production-full.sh

validate-release: ## Release production validation
	VALIDATION_MODE=release ./scripts/validators/validate-local-production-full.sh

validate-nightly: ## Nightly production validation
	VALIDATION_MODE=nightly ./scripts/validators/validate-local-production-full.sh

validate: validate-full validate-feature-flags validate-scripts ## Alias to validate-full

validate-feature-flags: ## Validate feature flags governance
	chmod +x ./scripts/validators/check-feature-flags.sh
	./scripts/validators/check-feature-flags.sh

# (moved to makefiles/quality.mk)

ga-readiness: ## Run the GA readiness gate
	chmod +x ./scripts/dev/ga-readiness.sh
	./scripts/dev/ga-readiness.sh $(TAG)

validate-scripts: ## Validate operational scripts governance
	chmod +x ./scripts/validators/check-script-manifest.sh
	./scripts/validators/check-script-manifest.sh

# (moved to makefiles/operations.mk)


validate-migrations: ## Validate Alembic migrations integrity
	./scripts/validators/validate-migrations-local.sh

validate-providers: ## Validate multi-provider layer
	./scripts/validators/validate-providers-local.sh

validate-smart-routing: ## Validate smart routing engine
	chmod +x ./scripts/validators/validate-smart-routing-local.sh
	./scripts/validators/validate-smart-routing-local.sh

validate-billing-brl: ## Validate billing BRL engine
	chmod +x ./scripts/validators/validate-billing-brl-local.sh
	./scripts/validators/validate-billing-brl-local.sh

validate-prepaid-wallet: ## Validate prepaid wallet in BRL
	chmod +x ./scripts/validators/validate-prepaid-wallet-local.sh
	./scripts/validators/validate-prepaid-wallet-local.sh

validate-abuse: ## Run abuse protection validation suite
	./scripts/validators/validate-abuse-protection-local.sh

validate-cors: ## Validate CORS configuration for local appliance
	./scripts/validators/validate-cors-local-appliance.sh

validate-migrations-temp: ## Validate migrations from scratch using temporary DB
	./scripts/validators/validate-migrations-local.sh --temp-db

# (moved to makefiles/operations.mk)

security: ## Generate security report
	@$(MAKE) agent-sandbox-security
	./scripts/validators/security-report-local.sh

security-cleanup-report: ## Generate security cleanup report
	./scripts/validators/security-report-local.sh
	mkdir -p artifacts/security
	cp $$(ls -td artifacts/security-reports/* | head -n 1)/security-report.md artifacts/security/security-cleanup.md
	@echo "Security cleanup report written to artifacts/security/security-cleanup.md"

pre-client-check: ## Run pre-client installation checklist
	chmod +x ./scripts/validators/pre-client-checklist-local.sh
	./scripts/validators/pre-client-checklist-local.sh --client-install

pre-demo-check: ## Run pre-demo checklist
	chmod +x ./scripts/validators/pre-client-checklist-local.sh
	./scripts/validators/pre-client-checklist-local.sh --demo

readiness: ## Run production readiness check
	./scripts/dev/production-readiness-local.sh

release: ## Create release bundle
	./scripts/release/create-release-bundle.sh --version $(shell cat VERSION) --include-docs --include-examples --include-demo

# (moved to makefiles/operations.mk)

# (moved to makefiles/operations.mk)

# (moved to makefiles/operations.mk)

# (moved to makefiles/operations.mk)

stabilization-check: ## Run formal stabilization phase checks
	chmod +x ./scripts/validators/stabilization-check.sh ./scripts/validators/check-working-tree-clean.sh ./scripts/validators/check-feature-flags.sh ./scripts/dev/working-tree-certification.sh
	./scripts/validators/check-working-tree-clean.sh
	./scripts/validators/check-feature-flags.sh
	$(MAKE) working-tree-certification
	@make platform-freeze-check
	./scripts/validators/stabilization-check.sh

# (moved to makefiles/quality.mk)

working-tree-certification: ## Certify working tree is clean for release (Requires TAG=vX.Y.Z)
	@chmod +x scripts/dev/working-tree-certification.sh
	@bash scripts/dev/working-tree-certification.sh $(TAG)

working-tree-governance: ## Check working tree governance (non-blocking vs blocking dirt)
	@chmod +x scripts/validators/check-working-tree-governance.sh
	@bash scripts/validators/check-working-tree-governance.sh


release-risk-report: ## Generate stabilization risk report
	chmod +x ./scripts/validators/release-risk-report.sh ./scripts/validators/check-working-tree-clean.sh
	./scripts/validators/check-working-tree-clean.sh
	./scripts/validators/release-risk-report.sh

# (moved to makefiles/operations.mk)

validate-install-local: ## Validate local appliance installer
	./scripts/validators/validate-install-local-appliance.sh

validate-backup-before-upgrade: ## Validate backup before upgrade logic
	./scripts/validators/validate-backup-before-upgrade-local.sh

# (moved to makefiles/operations.mk)

# (moved to makefiles/operations.mk)

validate-demo-pack: ## Validate commercial demo pack integrity and data
	chmod +x ./scripts/validators/validate-commercial-demo-pack.sh
	./scripts/validators/validate-commercial-demo-pack.sh

reset-demo-pack: ## Safe dry-run reset of commercial demo pack (default: --dry-run, never deletes real data)
	chmod +x ./scripts/dev/reset-commercial-demo-pack.sh
	./scripts/dev/reset-commercial-demo-pack.sh --dry-run

validate-reset-demo-pack: ## Validate reset safety (dry-run mode, no data harmed)
	chmod +x ./scripts/validators/validate-reset-commercial-demo-pack.sh
	./scripts/validators/validate-reset-commercial-demo-pack.sh

validate-fake-data: ## Validate fake demo data integrity and safety
	chmod +x ./scripts/validators/validate-fake-demo-data.sh
	./scripts/validators/validate-fake-demo-data.sh

# Legacy sales seed remains separate from fake-data validation; previous
# adjacency caused recipe shadowing and non-deterministic target resolution.
sales-seed: ## Seed commercial demo leads
	./scripts/dev/seed-sales-demo-leads.sh

validate-sales-crm: ## Validate Sales CRM (API + UI)
	./scripts/validators/validate-sales-crm-local.sh

clean-compose-local: ## Clean up docker-compose resources
	./scripts/backup/clean-compose-local.sh

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
benchmark-llm-harness: ## Run performance benchmark for LLM Harness
	@if [ -f .venv/bin/python3 ]; then \
		.venv/bin/python3 scripts/dev/benchmark-llm-harness.py; \
	else \
		python3 scripts/dev/benchmark-llm-harness.py; \
	fi

run-agent-benchmarks: ## Run agent benchmark suite (AgentBench, GAIA, BFCL)
	@echo "Running agent benchmarks..."
	@if [ -f .venv/bin/python3 ]; then \
		PYTHONPATH=.$${PYTHONPATH:+:$$PYTHONPATH}:control_plane \
		.venv/bin/python3 -m pytest tests/unit/services/test_agent_evaluation_framework.py \
		tests/unit/api/test_agent_evaluation_api.py -v --tb=short; \
		.venv/bin/python3 -c "\
import asyncio, uuid, os; \
from app.services.agents.agent_evaluation_framework import AgentEvaluationService; \
from app.db.session import AsyncSessionLocal; \
\
async def run(): \
    async with AsyncSessionLocal() as db: \
        svc = AgentEvaluationService(db); \
        benchmarks = os.environ.get('AGENT_EVAL_BENCHMARK', 'all'); \
        agent_id = uuid.UUID(os.environ.get('AGENT_EVAL_AGENT_ID', '00000000-0000-0000-0000-000000000000')); \
        model = os.environ.get('AGENT_EVAL_MODEL', 'demo-model'); \
        suite = ['AgentBench', 'GAIA', 'BFCL'] if benchmarks == 'all' else [benchmarks]; \
        for b in suite: \
            print(f'\\n=== Running {b} ==='); \
            report = await svc.run_benchmark(agent_id, model, b); \
            print(f'  Success rate: {report.metrics[\"success_rate\"]:.2%}'); \
            print(f'  Tool efficiency: {report.metrics[\"tool_efficiency\"]:.2%}'); \
            print(f'  Latency: {report.metrics[\"latency_ms\"]:.1f}ms'); \
            print(f'  Token cost: \$${report.metrics[\"token_cost\"]:.6f}'); \
            print(f'  Hallucination: {report.metrics[\"hallucination_score\"]:.4f}'); \
        print('\\nDone.'); \
asyncio.run(run()) \
"; \
	else \
		echo "Virtual environment not found. Run 'make venv' first."; \
	fi
production-core-check-llm-harness: ## Validate LLM Harness Production Core readiness criteria
	@if [ -f .venv/bin/python3 ]; then \
		PYTHONPATH=. .venv/bin/python3 scripts/validators/check-llm-harness-production-core.py; \
	else \
		PYTHONPATH=. python3 scripts/validators/check-llm-harness-production-core.py; \
	fi
validate-intelligent-cache: ## Validate intelligent cache (exact + semantic + tenant isolation)
	chmod +x ./scripts/validators/validate-intelligent-cache-local.sh
	./scripts/validators/validate-intelligent-cache-local.sh

validate-multitenant: ## Validate multi-tenant isolation
	chmod +x ./scripts/validators/validate-multitenant-isolation-full.sh
	./scripts/validators/validate-multitenant-isolation-full.sh

validate-local-production: validate

meeting-ready: ## Run meeting readiness check for client presentation
	chmod +x ./scripts/validators/meeting-ready-check-local.sh
	./scripts/validators/meeting-ready-check-local.sh

validate-meeting-ready: ## Validate meeting-ready check script
	chmod +x ./scripts/validators/validate-meeting-ready-check-local.sh
	./scripts/validators/validate-meeting-ready-check-local.sh

client-ready-report: ## Generate client ready final report
	chmod +x ./scripts/validators/generate-client-ready-report.sh
	./scripts/validators/generate-client-ready-report.sh

validate-client-ready-report: ## Validate client ready final report
	chmod +x ./scripts/validators/validate-client-ready-report.sh
	./scripts/validators/validate-client-ready-report.sh

# --- Sales Ops ---

generate-proposal:
	./scripts/dev/generate-client-proposal.sh 		--company-name "$(COMPANY_NAME)" 		--segment "$(SEGMENT)" 		--plan "$(PLAN)" 		--lead-id "$(LEAD_ID)"

validate-proposal:
	./scripts/validators/validate-client-proposal-local.sh

quote-demo: ## Generate a demo quote (Pro plan, RAG, 4h support)
	./scripts/dev/generate-local-quote.sh --company-name "Cliente Demo" --plan Pro --rag --tts --support-hours 4

validate-quote: ## Validate local quote generator
	./scripts/validators/validate-local-quote.sh

# --- Contracts / SOW ---

generate-sow: ## Generate a personalized SOW from template
	./scripts/dev/generate-sow-local.sh --company-name "Cliente Demo" --project-name "Local AI Appliance"

validate-contracts: ## Validate contract templates integrity
	./scripts/validators/validate-contract-templates-local.sh

# --- Implementation Checklist ---

implementation-checklist: ## Generate a paid implementation checklist
	./scripts/validators/paid-implementation-checklist-local.sh --company-name "Cliente Demo" --operator-name "Fornecedor Demo"

validate-implementation-checklist: ## Validate implementation checklist template and generation
	./scripts/validators/validate-paid-implementation-checklist.sh

# --- Monthly Report ---

monthly-report-demo: ## Generate a demo monthly report for a client
	./scripts/validators/generate-client-monthly-report.sh --email demo@example.local --month 2026-05

validate-monthly-report: ## Validate monthly report generator
	./scripts/validators/validate-client-monthly-report.sh

# --- White-Label / Branding ---

validate-white-label: ## Validate white-label branding configuration
	./scripts/validators/validate-white-label-local.sh

# --- Commercial Demo E2E Validation ---

validate-commercial-demo-e2e: ## Run end-to-end commercial demo validation
	./scripts/validators/validate-commercial-demo-e2e-local.sh --seed-demo

# --- Restore & Rollback Validation ---

validate-restore-rollback: ## Run restore/rollback validation (dry-run, safe)
	./scripts/validators/validate-real-restore-rollback-local.sh --dry-run

validate-restore-rollback-full: ## Run restore/rollback with backup, upgrade and rollback
	./scripts/validators/validate-real-restore-rollback-local.sh --yes

# --- Clean Install Validation ---

validate-clean-install: ## Run clean install validation (dry-run, safe)
	./scripts/validators/validate-clean-install-local.sh --dry-run

validate-clean-install-full: ## Run clean install validation with sandbox (requires --yes)
	./scripts/validators/validate-clean-install-local.sh --yes

validate-enterprise-rag: ## Validate enterprise RAG pipeline (chunking, parsers, policies, security)
	chmod +x ./scripts/validators/validate-enterprise-rag-local.sh
	./scripts/validators/validate-enterprise-rag-local.sh

validate-hybrid-admin: ## Validate hybrid admin dashboard (API, UI, sanitization, internal margin)
	chmod +x ./scripts/validators/validate-hybrid-admin-dashboard-local.sh
	./scripts/validators/validate-hybrid-admin-dashboard-local.sh

validate-hybrid-abuse: ## Validate hybrid abuse detection (anti-spam, anti-loop, rate limit, anomaly)
	chmod +x ./scripts/validators/validate-hybrid-abuse-detection-local.sh
	./scripts/validators/validate-hybrid-abuse-detection-local.sh

validate-margin-dashboard: ## Validate admin margin dashboard endpoint and payload sanitization
	chmod +x ./scripts/validators/validate-margin-dashboard.sh
	./scripts/validators/validate-margin-dashboard.sh

validate-commercial-calibration: ## Validate Commercial Calibration (Phase 6)
	chmod +x ./scripts/validators/validate-commercial-calibration.sh
	./scripts/validators/validate-commercial-calibration.sh

validate-commercial-guardrails: ## Validate commercial guardrails admin endpoints and payload sanitization
	chmod +x ./scripts/validators/validate-commercial-guardrails.sh
	./scripts/validators/validate-commercial-guardrails.sh

validate-commercial-config-apply: ## Validate manual controlled application of commercial configs
	chmod +x ./scripts/validators/validate-commercial-config-apply.sh
	./scripts/validators/validate-commercial-config-apply.sh

validate-commercial-auto-apply-canary: ## Validate Phase 8 Auto Apply Canary (Dry-run, Canary, Promotion)
	chmod +x ./scripts/validators/validate-commercial-auto-apply-canary.sh
	./scripts/validators/validate-commercial-auto-apply-canary.sh

validate-commercial-canary-promotion: ## Validate Phase 9 Canary Auto Promotion (SLO, Steps, Rollback)
	chmod +x ./scripts/validators/validate-commercial-canary-promotion.sh
	./scripts/validators/validate-commercial-canary-promotion.sh

validate-commercial-executive-dashboard: ## Validate Phase 10 Executive Profitability and Drift Dashboard
	chmod +x ./scripts/validators/validate-commercial-executive-dashboard.sh
	./scripts/validators/validate-commercial-executive-dashboard.sh

validate-commercial-report-export: ## Validate Phase 11 Executive Report Export and Scheduling
	chmod +x ./scripts/validators/validate-commercial-report-export.sh
	./scripts/validators/validate-commercial-report-export.sh

validate-commercial-report-email: ## Validate Phase 12 SMTP opt-in executive report email delivery
	chmod +x ./scripts/validators/validate-commercial-report-email.sh
	./scripts/validators/validate-commercial-report-email.sh

validate-commercial-routing-analytics: ## Validate commercial routing analytics persistence and summary
	chmod +x ./scripts/validators/validate-commercial-routing-analytics.sh
	./scripts/validators/validate-commercial-routing-analytics.sh

validate-commercial-distributed-analytics: ## Validate distributed commercial routing analytics endpoints and exports
	chmod +x ./scripts/validators/validate-commercial-distributed-analytics.sh
	./scripts/validators/validate-commercial-distributed-analytics.sh

validate-commercial-ha: ## Validate Commercial HA / leader election
	chmod +x ./scripts/validators/validate-commercial-ha.sh
	./scripts/validators/validate-commercial-ha.sh

validate-commercial-global-traffic-shifting: ## Validate Phase 17 Traffic Shifting
	bash -n scripts/validators/validate-commercial-global-traffic-shifting.sh

validate-commercial-federation: ## Validate Commercial Federation multi-cluster routing analytics
	chmod +x ./scripts/validators/validate-commercial-federation.sh
	./scripts/validators/validate-commercial-federation.sh

validate-commercial-global-router: ## Validate Commercial Global Router (Phase 16)
	chmod +x ./scripts/validators/validate-commercial-global-router.sh
	./scripts/validators/validate-commercial-global-router.sh

validate-commercial-financial-reconciliation: ## Validate financial reconciliation and disputes (Phase 27)
	chmod +x ./scripts/validators/validate-commercial-financial-reconciliation.sh
	./scripts/validators/validate-commercial-financial-reconciliation.sh

validate-enterprise-audit-portal: ## Validate enterprise customer audit portal (Phase 32)
	chmod +x ./scripts/validators/validate-enterprise-audit-portal.sh
	./scripts/validators/validate-enterprise-audit-portal.sh

validate-commercial-revenue-escalations: ## Validate revenue escalations (Phase 30)
	chmod +x ./scripts/validators/validate-commercial-revenue-escalations.sh
	./scripts/validators/validate-commercial-revenue-escalations.sh

validate-commercial-profit-routing: ## Validate commercial profit routing with ranking and simulation
	chmod +x ./scripts/validators/validate-commercial-profit-routing.sh
	./scripts/validators/validate-commercial-profit-routing.sh

validate-commercial-enforcement: ## Validate runtime enforcement with local-only test doubles
	chmod +x ./scripts/validators/validate-commercial-enforcement.sh
	./scripts/validators/validate-commercial-enforcement.sh

validate-real-provider-env: ## Validate real provider environment (.env.local, keys, security)
	chmod +x ./scripts/validators/validate-real-provider-env-local.sh
	./scripts/validators/validate-real-provider-env-local.sh

validate-openai-real-dry: ## Validate OpenAI real provider (dry-run, no cost)
	chmod +x ./scripts/validators/validate-openai-real-provider.sh
	./scripts/validators/validate-openai-real-provider.sh --dry-run

validate-openai-real: ## Validate OpenAI real provider (real calls, may incur cost)
	chmod +x ./scripts/validators/validate-openai-real-provider.sh
	./scripts/validators/validate-openai-real-provider.sh --real --model gpt-4o-mini

validate-deepseek-real-dry: ## Validate DeepSeek real provider (dry-run, no cost)
	chmod +x ./scripts/validators/validate-deepseek-real-provider.sh
	./scripts/validators/validate-deepseek-real-provider.sh --dry-run

validate-deepseek-real: ## Validate DeepSeek real provider (real calls, may incur cost)
	chmod +x ./scripts/validators/validate-deepseek-real-provider.sh
	./scripts/validators/validate-deepseek-real-provider.sh --real --model deepseek-chat

validate-anthropic-real-dry: ## Validate Anthropic real provider (dry-run, no cost)
	chmod +x ./scripts/validators/validate-anthropic-real-provider.sh
	./scripts/validators/validate-anthropic-real-provider.sh --dry-run

validate-anthropic-real: ## Validate Anthropic real provider (real calls, may incur cost)
	chmod +x ./scripts/validators/validate-anthropic-real-provider.sh
	./scripts/validators/validate-anthropic-real-provider.sh --real --model claude-3-haiku-20240307

measure-provider-costs-dry: ## Measure provider costs (dry-run, no real calls)
	chmod +x ./scripts/dev/measure-real-provider-costs.sh
	./scripts/dev/measure-real-provider-costs.sh --dry-run

measure-provider-costs: ## Measure provider costs (real calls, may incur cost)
	chmod +x ./scripts/dev/measure-real-provider-costs.sh
	./scripts/dev/measure-real-provider-costs.sh --real

validate-real-fallback-dry: ## Validate fallback local-to-cloud (dry-run, no cost)
	chmod +x ./scripts/validators/validate-real-fallback-local-to-cloud.sh
	./scripts/validators/validate-real-fallback-local-to-cloud.sh --dry-run

validate-real-fallback: ## Validate fallback local-to-cloud (real calls, may incur cost)
	chmod +x ./scripts/validators/validate-real-fallback-local-to-cloud.sh
	./scripts/validators/validate-real-fallback-local-to-cloud.sh --real --provider auto

validate-hybrid-e2e: ## Run hybrid platform E2E validation (v1.8.0)
	chmod +x ./scripts/validators/validate-hybrid-platform-e2e-local.sh ./scripts/validators/validate-hybrid-platform-report.sh
	./scripts/validators/validate-hybrid-platform-e2e-local.sh
	./scripts/validators/validate-hybrid-platform-report.sh

validate-clean-install-validator: ## Validate clean install script and outputs
	./scripts/validators/validate-clean-install-validator.sh

# --- Customer Demo (Comando Unico) ---

customer-demo: ## Prepare and validate a customer demo (quick mode)
	./scripts/dev/customer-demo-local.sh --quick --no-build

customer-demo-full: ## Prepare and validate a customer demo (full mode)
	./scripts/dev/customer-demo-local.sh --full --no-build

validate-customer-demo: ## Validate customer demo script and artifacts
	./scripts/validators/validate-customer-demo-local.sh

# --- Demo Visual Guide ---

# (moved to makefiles/operations.mk)

validate-demo-visual-guide: ## Validate demo visual guide integrity and security
	./scripts/validators/validate-demo-visual-guide.sh

# --- Fresh Machine Validation ---

fresh-machine-check: ## Run fresh machine readiness check (dry-run)
	chmod +x ./scripts/validators/fresh-machine-readiness-check.sh
	./scripts/validators/fresh-machine-readiness-check.sh --dry-run

validate-fresh-machine-docs: ## Validate fresh machine validation docs and scripts
	chmod +x ./scripts/validators/validate-fresh-machine-docs.sh
	./scripts/validators/validate-fresh-machine-docs.sh

# --- Repo Maintenance ---

# (moved to makefiles/operations.mk)

# --- Provider Cost Validation ---
# Compatibility note: keep the original `measure-provider-costs*` targets above
# as the canonical definitions. Do not redefine them below.

# --- Real Billing Margin Validation ---

validate-real-billing-margin-dry:
	./scripts/validators/validate-real-billing-margin.sh --dry-run

validate-real-billing-margin:
	./scripts/validators/validate-real-billing-margin.sh --real --provider auto

# --- Real Provider Artifact Sanitization ---

scan-real-provider-artifacts:
	./scripts/dev/scan-real-provider-artifacts.sh --fail-on-findings

validate-real-provider-sanitization:
	./scripts/validators/validate-real-provider-sanitization.sh

# --- Real Providers E2E ---

validate-real-providers-e2e-dry:
	./scripts/validators/validate-real-providers-e2e.sh --dry-run

validate-real-providers-e2e:
	./scripts/validators/validate-real-providers-e2e.sh --real

validate-commercial-geo-routing:
	@bash scripts/validators/validate-commercial-geo-routing.sh

validate-commercial-qos-routing:
	bash scripts/validators/validate-commercial-qos-routing.sh

validate-commercial-qos-queue:
	bash scripts/validators/validate-commercial-qos-queue.sh

validate-commercial-qos-fairness:
	bash scripts/validators/validate-commercial-qos-fairness.sh

validate-commercial-qos-billing:
	bash scripts/validators/validate-commercial-qos-billing.sh

validate-commercial-capacity-planning:
	bash scripts/validators/validate-commercial-capacity-planning.sh

# (moved to makefiles/operations.mk)

validate-commercial-live-balancing:
	bash scripts/validators/validate-commercial-live-balancing.sh

validate-commercial-infra-simulation:
	bash scripts/validators/validate-commercial-infra-simulation.sh

validate-commercial-infra-execution:
	bash scripts/validators/validate-commercial-infra-execution.sh

validate-commercial-revenue-forecasting:
	bash scripts/validators/validate-commercial-revenue-forecasting.sh

validate-commercial-revenue-protection:
	bash scripts/validators/validate-commercial-revenue-protection.sh

validate-commercial-compliance-controls: ## Validate compliance controls without shadowing governance policy checks
	bash scripts/validators/validate-commercial-compliance-controls.sh

# Legacy governance policy target preserved as a first-class validation entry.
validate-policy-governance: ## Validate Enterprise Policy Governance (Phase 34)
	chmod +x scripts/validators/validate-policy-governance.sh
	./scripts/validators/validate-policy-governance.sh

validate-governance-federation: ## Validate Enterprise Multi-Region Governance Federation (Phase 35)
	chmod +x scripts/validators/validate-governance-federation.sh
	./scripts/validators/validate-governance-federation.sh

validate-commercial-local-infra-adapters: ## Validate Proxmox and Local GPU adapters
	chmod +x scripts/validators/validate-commercial-local-infra-adapters.sh
	./scripts/validators/validate-commercial-local-infra-adapters.sh

validate-public-verifier: ## Validate Public Verifier CLI (Phase 43)
	chmod +x scripts/validators/validate-public-verifier.sh
	./scripts/validators/validate-public-verifier.sh

validate-public-attestation-gateway:
	bash scripts/validators/validate-public-attestation-gateway.sh

validate-confidential-runtime:
	bash scripts/validators/validate-confidential-runtime.sh

validate-confidential-agents:
	bash scripts/validators/validate-confidential-agents.sh

validate-trusted-agent-runtime:
	chmod +x scripts/validators/validate-trusted-agent-runtime.sh
	./scripts/validators/validate-trusted-agent-runtime.sh

validate-deterministic-workflows:
	bash scripts/validators/validate-deterministic-workflows.sh

validate-runtime-attestation: ## Validate hardware-backed attestation runtime (Phase 58)
	chmod +x scripts/validators/validate-runtime-attestation.sh
	./scripts/validators/validate-runtime-attestation.sh

validate-federated-workflows:
	chmod +x scripts/validators/validate-federated-workflows.sh
	./scripts/validators/validate-federated-workflows.sh

validate-workflow-governance:
	bash scripts/validators/validate-workflow-governance.sh

validate-phase56-migrations:
	bash scripts/validators/validate-phase56-migrations.sh

validate-sovereign-appliance:
	bash scripts/validators/validate-sovereign-appliance.sh

validate-confidential-rag-vault:
	bash scripts/validators/validate-confidential-rag-vault.sh

validate-control-plane-mesh: ## Validate Distributed Sovereign Control Plane Mesh (Phase 63)
	chmod +x scripts/validators/validate-control-plane-mesh.sh
	./scripts/validators/validate-control-plane-mesh.sh

# (moved to makefiles/agent.mk and makefiles/operations.mk)



production-agentic-e2e: ## Run non-mock E2E tests for production agentic claims
	@echo "Running Agentic Production E2E Suite..."
	@./scripts/dev/run-production-agentic-e2e.sh

alembic-check:
	@./scripts/check-alembic-integrity.sh
