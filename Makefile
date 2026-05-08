SHELL := /bin/bash

.PHONY: install up down validate validate-local-production backup logs check-secrets install-git-hooks clean-compose-local

install:
	./scripts/install.sh

check-secrets:
	./scripts/check-secrets.sh --all

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

logs:
	@if [[ -n "$$SERVICE" ]]; then \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f $$SERVICE; \
	else \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f control-plane control-plane-worker data-plane-gemma; \
	fi
