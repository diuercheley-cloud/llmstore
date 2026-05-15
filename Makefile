SHELL := /bin/bash

# Default target
.DEFAULT_GOAL := help

.PHONY: help first-run up down restart status health validate validate-control-center demo security readiness release backup restore upgrade rollback benchmark smoke clean-safe logs check-secrets fix-permissions install install-git-hooks clean-compose-local reset-demo-pack validate-reset-demo-pack validate-fake-data meeting-ready validate-meeting-ready client-ready-report validate-client-ready-report validate-v1.7-checklist v1.7-checklist-status demo-screenshot-plan validate-demo-visual-guide customer-demo customer-demo-full validate-customer-demo fresh-machine-check validate-fresh-machine-docs validate-providers validate-smart-routing validate-billing-brl validate-prepaid-wallet validate-enterprise-rag validate-hybrid-admin validate-hybrid-abuse validate-hybrid-e2e validate-margin-dashboard validate-commercial-guardrails validate-real-provider-env validate-openai-real-dry validate-openai-real validate-deepseek-real-dry validate-deepseek-real validate-anthropic-real-dry validate-anthropic-real validate-real-fallback-dry validate-real-fallback measure-provider-costs-dry measure-provider-costs validate-commercial-distributed-analytics validate-commercial-ha validate-commercial-federation validate-commercial-global-router validate-operational-controls validate-tenant-encryption validate-sovereign-airgap-governance validate-model-supply-chain validate-model-integrity-monitor validate-inference-reproducibility validate-cryptographic-receipts validate-rag-vault validate-retrieval-proofs validate-runtime-attestation validate-federated-workflows

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

help: ## Show this help message
	@echo "LLM Inference Stack - Operator Commands"
	@echo "Usage: make <target> [BACKUP_DIR=/path/to/backup]"
	@echo ""
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

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

validate-execution-proofs: ## Validate verifiable AI execution proofs + Merkle audit timelines (Phase 60)
	chmod +x scripts/validate-execution-proofs.sh
	./scripts/validate-execution-proofs.sh

validate-inference-reproducibility: ## Validate deterministic inference audit + replay controls (Phase 40)
	chmod +x scripts/validate-inference-reproducibility.sh
	./scripts/validate-inference-reproducibility.sh

validate-post-install: ## Run post-installation validation
	./scripts/validate-post-install-local.sh --with-demo

validate: ## Full production validation
	./scripts/validate-local-production-full.sh

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
	./scripts/security-report-local.sh

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
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f control-plane control-plane-worker data-plane-gemma; \
	fi

check-secrets: ## Scan for secrets in the codebase
	./scripts/check-secrets.sh --all

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
sales-seed: ## Seed commercial demo leads
	./scripts/seed-sales-demo-leads.sh

validate-sales-crm: ## Validate Sales CRM (API + UI)
	./scripts/validate-sales-crm-local.sh
	chmod +x ./scripts/validate-fake-demo-data.sh
	./scripts/validate-fake-demo-data.sh

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

measure-provider-costs-dry:
	./scripts/measure-real-provider-costs.sh --dry-run

measure-provider-costs:
	./scripts/measure-real-provider-costs.sh --real

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

test:

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

validate-commercial-compliance-controls:
validate-policy-governance: ## Validate Enterprise Policy Governance (Phase 34) 
	chmod +x scripts/validate-policy-governance.sh 
	./scripts/validate-policy-governance.sh
	bash scripts/validate-commercial-compliance-controls.sh
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
