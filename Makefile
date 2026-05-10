SHELL := /bin/bash

# Default target
.DEFAULT_GOAL := help

.PHONY: help first-run up down restart status health validate validate-control-center demo security readiness release backup restore upgrade rollback benchmark smoke clean-safe logs check-secrets fix-permissions install install-git-hooks clean-compose-local

help: ## Show this help message
	@echo "LLM Inference Stack - Operator Commands"
	@echo "Usage: make <target> [BACKUP_DIR=/path/to/backup]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

first-run: ## First run setup with demo data
	./scripts/first-run-local.sh --with-demo

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

validate: ## Full production validation
	./scripts/validate-local-production-full.sh

validate-migrations: ## Validate Alembic migrations integrity
	./scripts/validate-migrations-local.sh

validate-abuse: ## Run abuse protection validation suite
	./scripts/validate-abuse-protection-local.sh

validate-migrations-temp: ## Validate migrations from scratch using temporary DB
	./scripts/validate-migrations-local.sh --temp-db

demo: ## Run full demo (no build)
	./scripts/demo-full-local.sh --no-build

security: ## Generate security report
	./scripts/security-report-local.sh

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

install: ## Install system dependencies
	./scripts/install.sh

install-git-hooks: ## Install pre-commit git hooks
	./scripts/check-secrets.sh --install-hook

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
validate-multitenant: ## Validate multi-tenant isolation
	chmod +x ./scripts/validate-multitenant-isolation-full.sh
	./scripts/validate-multitenant-isolation-full.sh

validate-local-production: validate
