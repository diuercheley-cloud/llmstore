SHELL := /bin/bash

.PHONY: install up down validate validate-local-production backup logs check-secrets install-git-hooks

install:
	./install.sh

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

backup:
	./scripts/backup.sh

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
