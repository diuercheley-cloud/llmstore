SHELL := /bin/bash

.PHONY: install up down validate validate-local-production production-readiness backup logs check-secrets install-git-hooks clean-compose-local first-run-local first-run-demo

first-run-local:
	./scripts/first-run-local.sh

first-run-demo:
	./scripts/first-run-local.sh --with-demo

install:
	./scripts/install.sh

check-secrets:
	./scripts/check-secrets.sh --all

security-report:
	./scripts/security-report-local.sh

fix-permissions:
	./scripts/fix-local-permissions.sh --yes

validate-permissions:
	./scripts/validate-local-permissions.sh

install-git-hooks:
	./scripts/check-secrets.sh --install-hook

up:
	./scripts/up.sh

down:
	./scripts/down.sh

validate:
	./scripts/validate-e2e.sh

validate-local-production:
	./scripts/validate-local-production-full.sh

production-readiness:
	./scripts/production-readiness-local.sh

demo-local:
	./scripts/demo-full-local.sh --no-build

demo-local-reset:
	./scripts/demo-full-local.sh --reset-first

validate-demo-local:
	./scripts/validate-demo-local.sh

backup:
	./scripts/backup.sh

clean-compose-local:
	./scripts/clean-compose-local.sh

clean-rag-local-dry-run:
	./scripts/clean-rag-local-data.sh --dry-run

clean-rag-local:
	./scripts/clean-rag-local-data.sh

retention-dry-run:
	./scripts/retention-local.sh --dry-run --section all

validate-retention:
	./scripts/validate-retention-local.sh

validate-export-client:
	./scripts/validate-export-client-local.sh

validate-delete-client:
	./scripts/validate-delete-client-local.sh

release-bundle:
	./scripts/create-release-bundle.sh --version $(shell cat VERSION) --include-docs --include-examples --include-demo

validate-release-bundle:
	./scripts/validate-release-bundle.sh

benchmark-model:
	./scripts/benchmark-model-local.sh --model "gemma" --quick

logs:
	@if [[ -n "$$SERVICE" ]]; then \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f $$SERVICE; \
	else \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f control-plane control-plane-worker data-plane-gemma; \
	fi
