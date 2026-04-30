SHELL := /bin/bash

.PHONY: install up down validate backup logs

install:
	./install.sh

up:
	./scripts/up.sh

down:
	./scripts/down.sh

validate:
	./scripts/validate-e2e.sh

backup:
	./scripts/backup.sh

logs:
	@if [[ -n "$$SERVICE" ]]; then \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f $$SERVICE; \
	else \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f control-plane control-plane-worker data-plane-gemma; \
	fi
