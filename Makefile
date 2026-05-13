SHELL := /bin/bash

# Default target
.DEFAULT_GOAL := help

.PHONY: help first-run up down restart status health validate validate-control-center demo security readiness release backup restore upgrade rollback benchmark smoke clean-safe logs check-secrets fix-permissions install install-git-hooks clean-compose-local reset-demo-pack validate-reset-demo-pack validate-fake-data meeting-ready validate-meeting-ready client-ready-report validate-client-ready-report validate-v1.7-checklist v1.7-checklist-status demo-screenshot-plan validate-demo-visual-guide customer-demo customer-demo-full validate-customer-demo fresh-machine-check validate-fresh-machine-docs validate-providers validate-smart-routing validate-billing-brl validate-prepaid-wallet validate-enterprise-rag validate-hybrid-admin validate-hybrid-abuse validate-hybrid-e2e

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
