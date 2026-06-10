# ── Quality Gates ──────────────────────────────────────────────

service-coverage-report:
	python3 scripts/validators/check-service-test-coverage.py

service-coverage-gate:
	python3 scripts/validators/check-service-test-coverage.py --gate

test-collect: ## Validate collection of all Python tests
	PYTHONPATH=.:control_plane .venv/bin/python -m pytest --collect-only -q tests tests/control_plane

lint-functional: ## Run blocking Python lint checks without style-only noise
	.venv/bin/ruff check control_plane/app --no-cache --select F821,F811,E722

lint-hygiene-report: ## Report non-blocking Python hygiene debt
	.venv/bin/ruff check control_plane/app --no-cache --select F401,F841,I --statistics

ci-local: lint-functional test-collect check-feature-flags-integrity check-supported-surface platform-freeze-check maintenance-budgets service-coverage-gate ## Reproduce blocking CI quality gates locally

maintenance-budgets: ## Prevent architectural surface and complexity growth
	.venv/bin/python scripts/validators/check-maintenance-budgets.py

coverage-baseline: ## Generate coverage baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/dev/generate_coverage_baseline.py

performance-baseline: ## Generate performance baseline
	PYTHONPATH=control_plane .venv/bin/python scripts/dev/generate_performance_baseline.py
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/integration/performance/test_performance_baseline_tools.py -q --tb=short

complexity-report: ## Generate platform complexity analysis and recommendations
	chmod +x ./scripts/validators/complexity-report.sh
	./scripts/validators/complexity-report.sh

feature-flag-audit: ## Run the feature flags governance auditor
	chmod +x ./scripts/validators/audit-feature-flags.py
	@if [ -x ./.venv/bin/python3 ]; then ./.venv/bin/python3 ./scripts/validators/audit-feature-flags.py; \
	elif [ -x ./venv/bin/python3 ]; then ./venv/bin/python3 ./scripts/validators/audit-feature-flags.py; \
	else python3 ./scripts/validators/audit-feature-flags.py; fi

surface-area-audit: ## Run the supported surface governance audit
	chmod +x ./scripts/validators/surface-area-audit.py
	@if [ -x ./.venv/bin/python3 ]; then PYTHONPATH=control_plane ./.venv/bin/python3 ./scripts/validators/surface-area-audit.py; \
	elif [ -x ./venv/bin/python3 ]; then PYTHONPATH=control_plane ./venv/bin/python3 ./scripts/validators/surface-area-audit.py; \
	else PYTHONPATH=control_plane python3 ./scripts/validators/surface-area-audit.py; fi

measure-validation-targets: ## Measure duration and exit code of validation targets
	python3 ./scripts/validators/measure_validation_targets.py

list-slow-tests: ## Identify slow pytest tests
	python3 ./scripts/dev/list_slow_tests.py --test-dir tests/integration/build --timeout 120
