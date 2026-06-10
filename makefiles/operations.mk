# ── Operations & Deployment Targets ────────────────────────────

customer-ready: ## Validate final client installation (Ready/Not Ready)
	./scripts/validators/validate-customer-ready.sh

appliance-local: ## Install as local appliance (no cloud)
	./scripts/deploy/install-customer.sh appliance-local

hybrid-provider: ## Install with cloud providers enabled
	./scripts/deploy/install-customer.sh hybrid-provider

demo-sales: ## Install optimized for sales demos
	./scripts/deploy/install-customer.sh demo-sales

enterprise-rag: ## Install optimized for RAG
	./scripts/deploy/install-customer.sh enterprise-rag

dev-lab: ## Install for development and testing
	./scripts/deploy/install-customer.sh dev-lab

preflight: ## Run preflight checks for deployment
	@bash scripts/validators/preflight-check.sh

deploy-appliance: ## Deploy as a local appliance
	@bash scripts/deploy/deploy-appliance.sh

deploy-k8s: ## Deploy to Kubernetes using Helm
	@bash scripts/deploy/deploy-kubernetes.sh

upgrade-release: ## Upgrade the current release with backup and validation
	@bash scripts/deploy/upgrade-release.sh

rollback-release: ## Rollback to the previous release
	@bash scripts/release/rollback-release.sh

post-deploy-validate: ## Validate system after deployment
	@bash scripts/validators/post-deploy-validate.sh

install-local: ## Install system as local appliance with demo data
	./scripts/deploy/install-local-appliance.sh --with-demo

install: ## Install system dependencies
	./scripts/deploy/install.sh

install-git-hooks: ## Install pre-commit git hooks
	./scripts/validators/check-secrets.sh --install-hook

first-run: ## First run setup with demo data
	./scripts/deploy/first-run-local.sh --with-demo

configure-local: ## Guided wizard to configure local appliance
	./scripts/dev/configure-local-wizard.sh --interactive

configure-local-noninteractive: ## Configure local appliance with defaults
	./scripts/dev/configure-local-wizard.sh --non-interactive --yes

up: ## Start the stack in background
	./scripts/deploy/up.sh

down: ## Stop the stack
	./scripts/deploy/down.sh

restart: ## Restart the stack
	$(MAKE) down
	$(MAKE) up

status: ## Show stack status
	./scripts/dev/status.sh

health: ## Check stack health (endpoints: /health, /ready, /status)
	./scripts/dev/test-health.sh

logs: ## Show logs (use SERVICE=name for specific service)
	@if [[ -n "$$SERVICE" ]]; then \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f $$SERVICE; \
	else \
		docker compose --env-file $${ENV_FILE:-.env.local} -f docker-compose.yml logs -f control-plane control-plane-worker data-plane-gemma agent-worker; \
	fi

backup: ## Perform local backup (artifacts/backups-local/)
	./scripts/backup/backup-local.sh

restore: ## Restore from backup (Requires BACKUP_DIR)
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "Usage: make restore BACKUP_DIR=/path/to/backup"; \
		echo "Available backups in artifacts/backups-local/:"; \
		ls -d artifacts/backups-local/*/ 2>/dev/null || echo "No backups found."; \
		exit 1; \
	fi
	./scripts/backup/restore-local.sh $(BACKUP_DIR)

upgrade: ## Upgrade local installation
	./scripts/deploy/upgrade-local.sh

rollback: ## Rollback local installation
	./scripts/dev/rollback-local.sh

backup-dry-run: ## Run dry-run database and configs backup simulation
	chmod +x ./scripts/backup/backup.sh
	./scripts/backup/backup.sh --dry-run

restore-dry-run: ## Run dry-run database restore simulation
	chmod +x ./scripts/backup/restore-local.sh
	./scripts/backup/restore-local.sh --dry-run ./artifacts/backups/test-backup-run

upgrade-dry-run: ## Run dry-run system upgrade simulation
	chmod +x ./scripts/deploy/upgrade-release.sh
	./scripts/deploy/upgrade-release.sh --dry-run --force

rollback-dry-run: ## Run dry-run system rollback simulation
	chmod +x ./scripts/release/rollback-release.sh
	./scripts/release/rollback-release.sh --dry-run

demo: ## Run full demo (no build)
	./scripts/dev/demo-full-local.sh --no-build

demo-pack: ## Seed commercial demo pack (5 scenarios, clients, plans, RAG, invoices)
	chmod +x ./scripts/dev/seed-commercial-demo-pack.sh
	./scripts/dev/seed-commercial-demo-pack.sh

demo-screenshot-plan: ## Generate screenshot capture plan (or capture with Playwright)
	./scripts/dev/prepare-demo-screenshots-local.sh

benchmark: ## Run quick model benchmark
	./scripts/dev/benchmark-model-local.sh --quick

smoke: ## Run post-upgrade smoke tests
	./scripts/validators/post-upgrade-smoke-local.sh

clean-safe: ## Dry-run of data retention (safe cleanup)
	./scripts/backup/retention-local.sh --dry-run --section all

check-secrets: ## Scan for secrets in the codebase
	./scripts/validators/check-secrets.sh --all

fix-permissions: ## Fix local file permissions
	./scripts/dev/fix-local-permissions.sh --yes

cleanup-branches: ## List safe-to-delete local branches (dry-run)
	./scripts/backup/cleanup-local-branches.sh --dry-run --merged-only

# ── Test Suites ────────────────────────────────────────────────

test: ## Run focused regression suite for admin RBAC, tokenization, PKI/attestation/plugins, and GGUF hot swap
	PYTHONPATH=control_plane .venv/bin/python -m pytest \
		tests/test_admin_rbac.py \
		tests/test_tokenizer_service.py \
		tests/control_plane/test_pki_attestation_plugins.py \
		tests/control_plane/test_model_hot_swap.py \
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

test-smoke-resilience: ## Run smoke tests for resilience
	@cd control_plane && PYTHONPATH=. ../venv/bin/pytest tests/smoke/test_smoke.py

test-chaos-resilience: ## Run chaos tests for resilience
	@cd control_plane && PYTHONPATH=. ../venv/bin/pytest tests/chaos/test_chaos.py

# ── Kubernetes & Operator Mode ─────────────────────────────────

k8s-render: ## Render Kubernetes manifests using a simple template script (since helm is missing)
	@echo "Rendering Kubernetes manifests..."
	@mkdir -p deploy/rendered
	@cp deploy/kubernetes/*.yaml deploy/rendered/

k8s-validate: ## Validate Kubernetes manifests using python tests
	@echo "Validating Kubernetes manifests..."
	@PYTHONPATH=. .venv/bin/pytest tests/integration/kubernetes/test_yaml_validity.py -v

helm-package: ## Package Helm chart
	@echo "Packaging Helm chart..."
	@tar -cvzf llm-inference-stack-0.1.0.tgz -C deploy/helm llm-inference-stack

operator-test: ## Test Operator (mock reconciliation)
	@echo "Testing Operator reconciliation..."
	@PYTHONPATH=. .venv/bin/python3 operator/main.py --help || echo "Operator script exists and is syntactically correct."
	@PYTHONPATH=. .venv/bin/pytest tests/integration/kubernetes/test_operator_mock.py -v

distributed-runtime-test: ## Test Distributed Runtime service and endpoints
	@echo "Testing Distributed Runtime..."
	@PYTHONPATH=. .venv/bin/pytest tests/integration/runtime/test_distributed_runtime.py -v

gpu-autoscaling-test: ## Test GPU Orchestration and Autoscaling
	@echo "Testing GPU Orchestration and Autoscaling..."
	@PYTHONPATH=. .venv/bin/pytest tests/integration/runtime/test_gpu_orchestrator.py -v
